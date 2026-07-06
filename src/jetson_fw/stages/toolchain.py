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
        return [
            f"mkdir -p {downloads} {toolchain_root}",
            f"wget -O {archive} {context.config.toolchain.url}",
            f"echo '{context.config.toolchain.sha256}  {archive}' | sha256sum -c -",
            f"tar -xJf {archive} -C {toolchain_root} --strip-components=1",
        ]
