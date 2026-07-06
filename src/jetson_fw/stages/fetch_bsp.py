"""Fetch and extract BSP artifacts."""

from __future__ import annotations

from .base import Stage, StageContext


class FetchBspStage(Stage):
    name = "fetch_bsp"

    def commands(self, context: StageContext) -> list[str]:
        downloads = context.workspace / "downloads"
        l4t_dir = context.workspace / "Linux_for_Tegra"
        bsp_archive = downloads / "jetson_linux.tbz2"
        rootfs_archive = downloads / "sample_rootfs.tbz2"
        return [
            f"mkdir -p {downloads} {l4t_dir}/rootfs",
            f"if [ ! -f {bsp_archive} ]; then wget -O {bsp_archive} {context.config.l4t.bsp_url}; fi",
            f"echo '{context.config.l4t.bsp_sha256}  {bsp_archive}' | sha256sum -c -",
            f"tar -xjf {bsp_archive} -C {context.workspace}",
            f"if [ ! -f {rootfs_archive} ]; then wget -O {rootfs_archive} {context.config.l4t.sample_rootfs_url}; fi",
            f"echo '{context.config.l4t.sample_rootfs_sha256}  {rootfs_archive}' | sha256sum -c -",
            f"tar -xjf {rootfs_archive} -C {l4t_dir}/rootfs",
        ]
