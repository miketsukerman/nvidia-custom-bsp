"""Build stage abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from jetson_fw.config.model import BspConfig, BuildConfig, KernelConfig, RootfsConfig, TargetConfig
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
    def kernel_source_dir(self) -> Path:
        return self.workspace / "Linux_for_Tegra" / "sources" / "kernel" / "kernel-5.10"

    @property
    def kernel(self) -> KernelConfig:
        return self.config.effective_kernel(self.target)

    @property
    def rootfs(self) -> RootfsConfig:
        return self.config.effective_rootfs(self.target)

    @property
    def bsp(self) -> BspConfig:
        return self.config.effective_bsp(self.target)

    @property
    def state_dir(self) -> Path:
        return self.workspace / ".state"

    def marker_path(self, stage_name: str, *, target_scoped: bool = False) -> Path:
        if target_scoped and self.target is not None:
            return self.state_dir / f"{stage_name}.{self.target.name}.done"
        return self.state_dir / f"{stage_name}.done"

    def repo_path(self, host_path: Path) -> Path:
        return self.docker.container_path(host_path)


class Stage(ABC):
    """Base class for an executable stage."""

    name: str
    dependencies: tuple[str, ...] = ()
    target_scoped: bool = False

    def validate(self, context: StageContext) -> None:
        """Validate stage prerequisites."""

    def should_skip(self, context: StageContext) -> bool:
        return not context.force and context.marker_path(
            self.name, target_scoped=self.target_scoped
        ).exists()

    @abstractmethod
    def commands(self, context: StageContext) -> list[str]:
        """Return the shell commands executed for this stage."""

    def run(self, context: StageContext) -> None:
        marker = context.marker_path(self.name, target_scoped=self.target_scoped)
        if self.should_skip(context):
            context.logger.info(f"Skipping {self.name}; marker exists.")
            context.logger.debug(
                f"stage.skip name={self.name} marker={marker} force={context.force}"
            )
            return
        context.logger.debug(
            "stage.start "
            f"name={self.name} dry_run={context.dry_run} force={context.force} "
            f"workspace={context.workspace} state_dir={context.state_dir} "
            f"target={context.target.name if context.target else 'none'}"
        )
        self.validate(context)
        commands = [
            f"mkdir -p {context.state_dir}",
            *self.commands(context),
            f"touch {marker}",
        ]
        context.logger.debug(f"stage.commands name={self.name} count={len(commands)}")
        context.docker.run_commands(commands, flash=self.name == "flash", dry_run=context.dry_run)
        context.logger.debug(f"stage.end name={self.name} marker={marker}")
