"""Flash a target board."""

from __future__ import annotations

from .base import Stage, StageContext


class FlashStage(Stage):
    name = "flash"
    dependencies = ("assemble_rootfs",)

    def validate(self, context: StageContext) -> None:
        if context.target is None:
            raise ValueError("flash stage requires a target")

    def commands(self, context: StageContext) -> list[str]:
        assert context.target is not None
        l4t_dir = context.workspace / "Linux_for_Tegra"
        return [
            f"cd {l4t_dir} && ./flash.sh {context.target.flash_config.value} {context.target.root_device.value}"
        ]
