"""Flash a target board."""

from __future__ import annotations

from .base import Stage, StageContext


class FlashStage(Stage):
    name = "flash"
    dependencies = ("assemble_rootfs",)
    target_scoped = True

    def validate(self, context: StageContext) -> None:
        if context.target is None:
            raise ValueError("flash stage requires a target")

    def commands(self, context: StageContext) -> list[str]:
        assert context.target is not None
        l4t_dir = context.workspace / "Linux_for_Tegra"
        context.logger.debug(
            "flash.context "
            f"target={context.target.name} flash_config={context.target.flash_config} "
            f"root_device={context.target.root_device.value} l4t_dir={l4t_dir}"
        )
        return [
            f"cd {l4t_dir} && ./flash.sh {context.target.flash_config} {context.target.root_device.value}"
        ]
