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
        if not context.logger.verbose and not context.logger.quiet:
            total = len(patches)
            for index, patch in enumerate(patches, start=1):
                context.logger.info(f"Patching kernel ({index}/{total}): {patch.name}")
        return [
            f"git -C {source_dir} apply --whitespace=fix {context.repo_path(patch)}"
            for patch in patches
        ]
