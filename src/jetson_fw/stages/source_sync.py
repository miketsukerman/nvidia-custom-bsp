"""Sync kernel sources from NVIDIA."""

from __future__ import annotations

from .base import Stage, StageContext


class SourceSyncStage(Stage):
    name = "source_sync"
    dependencies = ("fetch_bsp",)

    def commands(self, context: StageContext) -> list[str]:
        l4t_dir = context.workspace / "Linux_for_Tegra"
        return [f"cd {l4t_dir} && ./source_sync.sh -t {context.config.kernel.source_tag}"]
