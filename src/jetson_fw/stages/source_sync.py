"""Sync kernel sources from NVIDIA."""

from __future__ import annotations

from .base import Stage, StageContext

PROMETHEUS_DTS_SOURCE = "hardware/nvidia/platform/t23x/prometheus/kernel-dts"
ESCAPED_PROMETHEUS_DTS_SOURCE = PROMETHEUS_DTS_SOURCE.replace("/", r"\/")


class SourceSyncStage(Stage):
    name = "source_sync"
    dependencies = ("customize_bsp",)
    target_scoped = True

    def commands(self, context: StageContext) -> list[str]:
        l4t_dir = context.workspace / "Linux_for_Tegra"
        filtered_script = l4t_dir / "source_sync.filtered.sh"
        context.logger.debug(
            f"source_sync.context l4t_dir={l4t_dir} source_tag={context.kernel.source_tag}"
        )
        context.logger.debug(f"source_sync.filter removed_path={PROMETHEUS_DTS_SOURCE}")
        return [
            f"sed '/{ESCAPED_PROMETHEUS_DTS_SOURCE}/d' {l4t_dir}/source_sync.sh > {filtered_script}",
            f"chmod +x {filtered_script}",
            f"{filtered_script} -k {context.kernel.source_tag}",
            f"rm -f {filtered_script}",
        ]
