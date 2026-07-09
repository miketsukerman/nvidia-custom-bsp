"""Apply patch files to the synced kernel sources."""

from __future__ import annotations

from .base import Stage, StageContext


class PatchKernelStage(Stage):
    name = "patch_kernel"
    dependencies = ("source_sync",)
    target_scoped = True

    def commands(self, context: StageContext) -> list[str]:
        patches = context.kernel.patches
        source_dir = context.kernel_source_dir
        context.logger.debug(
            f"patch_kernel.context source_dir={source_dir} patch_count={len(patches)}"
        )
        if not patches:
            return [":"]
        return [
            f"git -C {source_dir} apply --whitespace=fix {context.repo_path(patch)}"
            for patch in patches
        ]
