"""Sync kernel sources from NVIDIA."""

from __future__ import annotations

from .base import Stage, StageContext

PROMETHEUS_DTS_SOURCE = "hardware/nvidia/platform/t23x/prometheus/kernel-dts"
ESCAPED_PROMETHEUS_DTS_SOURCE = PROMETHEUS_DTS_SOURCE.replace("/", r"\/")


class SourceSyncStage(Stage):
    name = "source_sync"
    dependencies = ("customize_bsp",)

    def commands(self, context: StageContext) -> list[str]:
        l4t_dir = context.workspace / "Linux_for_Tegra"
        context.logger.debug(
            f"source_sync.context l4t_dir={l4t_dir} source_tag={context.config.kernel.source_tag}"
        )
        context.logger.debug(f"source_sync.filter removed_path={PROMETHEUS_DTS_SOURCE}")
        return [
            f"cd {l4t_dir}",
            "tmp_script=$(mktemp ./source_sync.filtered.XXXXXX.sh)",
            "trap 'rm -f \"$tmp_script\"' EXIT",
            ("sed " f"'/{ESCAPED_PROMETHEUS_DTS_SOURCE}/d' " './source_sync.sh > "$tmp_script"'),
            'chmod +x "$tmp_script"',
            f'"$tmp_script" -k {context.config.kernel.source_tag}',
        ]
