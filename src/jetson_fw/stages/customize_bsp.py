"""Copy custom files into Linux_for_Tegra."""

from __future__ import annotations

from .base import Stage, StageContext


class CustomizeBspStage(Stage):
    name = "customize_bsp"
    dependencies = ("fetch_bsp",)
    target_scoped = True

    def commands(self, context: StageContext) -> list[str]:
        l4t_dir = context.workspace / "Linux_for_Tegra"
        overlays = context.bsp.overlays
        context.logger.debug(
            f"customize_bsp.context l4t_dir={l4t_dir} overlay_count={len(overlays)}"
        )
        commands: list[str] = []
        for overlay in overlays:
            source = context.repo_path(overlay.src)
            destination = l4t_dir / overlay.dest.lstrip("/")
            if overlay.src.is_dir():
                commands.append(f"mkdir -p {destination} && cp -a {source}/. {destination}")
            else:
                commands.append(f"mkdir -p {destination.parent} && cp -a {source} {destination}")
        return commands or [":"]
