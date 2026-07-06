"""Fetch and extract the cross toolchain."""

from __future__ import annotations

from .base import Stage, StageContext


class ToolchainStage(Stage):
    name = "toolchain"
    dependencies = ("fetch_bsp",)

    def commands(self, context: StageContext) -> list[str]:
        downloads = context.workspace / "downloads"
        archive = downloads / "toolchain.tar.xz"
        toolchain_root = context.workspace / "toolchain"
        context.logger.debug(
            "toolchain.paths "
            f"downloads={downloads} archive={archive} toolchain_root={toolchain_root}"
        )
        context.logger.debug(f"toolchain.cache_check archive_exists={archive.exists()}")
        return [
            f"mkdir -p {downloads} {toolchain_root}",
            f"if [ ! -f {archive} ]; then wget -O {archive} {context.config.toolchain.url}; fi",
            f"echo '{context.config.toolchain.sha256}  {archive}' | sha256sum -c -",
            f"tar -xf {archive} -C {toolchain_root} --strip-components=1",
        ]
