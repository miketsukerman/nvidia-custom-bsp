"""Build stage abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from jetson_fw.config.model import BuildConfig, TargetConfig
from jetson_fw.docker.runner import DockerRunner
from jetson_fw.utils.logging import Logger


@dataclass
class StageContext:
    """Shared runtime objects for stages."""

    config: BuildConfig
    docker: DockerRunner
    logger: Logger
    dry_run: bool = False
    force: bool = False
    target: TargetConfig | None = None

    @property
    def workspace(self) -> Path:
        return self.config.workspace.root

    @property
    def state_dir(self) -> Path:
        return self.workspace / ".state"

    def marker_path(self, stage_name: str) -> Path:
        return self.state_dir / f"{stage_name}.done"

    def repo_path(self, host_path: Path) -> Path:
        return self.docker.container_path(host_path)


class Stage(ABC):
    """Base class for an executable stage."""

    name: str
    dependencies: tuple[str, ...] = ()

    def validate(self, context: StageContext) -> None:
        """Validate stage prerequisites."""

    def should_skip(self, context: StageContext) -> bool:
        return not context.force and context.marker_path(self.name).exists()

    @abstractmethod
    def commands(self, context: StageContext) -> list[str]:
        """Return the shell commands executed for this stage."""

    def run(self, context: StageContext) -> None:
        if self.should_skip(context):
            context.logger.info(f"Skipping {self.name}; marker exists.")
            return
        self.validate(context)
        inner = " && ".join(
            [
                f"mkdir -p {context.state_dir}",
                *self.commands(context),
                f"touch {context.marker_path(self.name)}",
            ]
        )
        context.docker.run(inner, flash=self.name == "flash", dry_run=context.dry_run)
