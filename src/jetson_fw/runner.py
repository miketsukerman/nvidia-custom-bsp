"""Stage orchestration."""

from __future__ import annotations

from jetson_fw.config.model import BuildConfig, TargetConfig
from jetson_fw.docker.runner import DockerRunner
from jetson_fw.stages.assemble_rootfs import AssembleRootfsStage
from jetson_fw.stages.base import Stage, StageContext
from jetson_fw.stages.build_kernel import BuildKernelStage
from jetson_fw.stages.fetch_bsp import FetchBspStage
from jetson_fw.stages.flash import FlashStage
from jetson_fw.stages.source_sync import SourceSyncStage
from jetson_fw.stages.toolchain import ToolchainStage
from jetson_fw.utils.logging import Logger


class BuildRunner:
    """Run stages in dependency order."""

    def __init__(self, config: BuildConfig, docker: DockerRunner, logger: Logger):
        self.config = config
        self.docker = docker
        self.logger = logger
        self.stages: dict[str, Stage] = {
            "fetch_bsp": FetchBspStage(),
            "toolchain": ToolchainStage(),
            "source_sync": SourceSyncStage(),
            "build_kernel": BuildKernelStage(),
            "assemble_rootfs": AssembleRootfsStage(),
            "flash": FlashStage(),
        }

    def run_build(self, *, stage_name: str | None = None, dry_run: bool = False, force: bool = False) -> None:
        ordered = self._ordered_stage_names(stage_name or "assemble_rootfs")
        context = StageContext(self.config, self.docker, self.logger, dry_run=dry_run, force=force)
        for name in ordered:
            self.logger.info(f"Running stage: {name}")
            self.stages[name].run(context)

    def run_flash(self, target: TargetConfig, *, dry_run: bool = False, force: bool = False) -> None:
        ordered = self._ordered_stage_names("flash")
        context = StageContext(
            self.config,
            self.docker,
            self.logger,
            dry_run=dry_run,
            force=force,
            target=target,
        )
        for name in ordered:
            self.logger.info(f"Running stage: {name}")
            self.stages[name].run(context)

    def run_all(self, *, dry_run: bool = False, force: bool = False) -> None:
        self.run_build(dry_run=dry_run, force=force)
        for target in self.config.enabled_targets():
            self.run_flash(target, dry_run=dry_run, force=force)

    def _ordered_stage_names(self, final_stage: str) -> list[str]:
        if final_stage not in self.stages:
            raise ValueError(f"unknown stage: {final_stage}")
        ordered: list[str] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            for dependency in self.stages[name].dependencies:
                visit(dependency)
            ordered.append(name)

        visit(final_stage)
        return ordered
