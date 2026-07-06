"""Assemble rootfs and install modules."""

from __future__ import annotations

from .base import Stage, StageContext


class AssembleRootfsStage(Stage):
    name = "assemble_rootfs"
    dependencies = ("build_kernel",)

    def commands(self, context: StageContext) -> list[str]:
        l4t_dir = context.workspace / "Linux_for_Tegra"
        rootfs_dir = l4t_dir / "rootfs"
        kernel_source = l4t_dir / "source" / "public" / "kernel" / "kernel-5.10"
        out_dir = context.workspace / "out" / "kernel"
        context.logger.debug(
            "assemble_rootfs.context "
            f"l4t_dir={l4t_dir} rootfs_dir={rootfs_dir} out_dir={out_dir}"
        )
        context.logger.debug(
            "assemble_rootfs.options "
            f"install_modules={context.config.rootfs.install_modules} "
            f"extra_packages_count={len(context.config.rootfs.extra_packages)} "
            f"overlay_count={len(context.config.rootfs.overlays)}"
        )
        commands = [f"cd {l4t_dir} && ./apply_binaries.sh"]
        if context.config.rootfs.install_modules:
            commands.append(
                f"make -C {kernel_source} O={out_dir} modules_install INSTALL_MOD_PATH={rootfs_dir}"
            )
        if context.config.rootfs.extra_packages:
            packages = " ".join(context.config.rootfs.extra_packages)
            commands.extend(
                [
                    f"cp /usr/bin/qemu-aarch64-static {rootfs_dir}/usr/bin/",
                    f"chroot {rootfs_dir} /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get update",
                    f"chroot {rootfs_dir} /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y {packages}",
                ]
            )
        for overlay in context.config.rootfs.overlays:
            overlay_src = context.repo_path(overlay.src)
            commands.append(
                f"mkdir -p {rootfs_dir}{overlay.dest} && cp -a {overlay_src}/. {rootfs_dir}{overlay.dest}"
            )
        return commands
