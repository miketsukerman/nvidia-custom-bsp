"""Assemble rootfs and install modules."""

from __future__ import annotations

from .base import Stage, StageContext


class AssembleRootfsStage(Stage):
    name = "assemble_rootfs"
    dependencies = ("build_kernel",)

    def commands(self, context: StageContext) -> list[str]:
        l4t_dir = context.workspace / "Linux_for_Tegra"
        rootfs_dir = l4t_dir / "rootfs"
        kernel_source = context.kernel_source_dir
        out_dir = context.workspace / "out" / "kernel"
        commands = [
            # nvidia-l4t-gputools postinst recreates this link without `ln -f`,
            # so a failed prior run leaves rootfs in a state that breaks retries.
            f"rm -f {rootfs_dir}/usr/local/bin/nvgpuswitch.py",
            f"cd {l4t_dir} && ./apply_binaries.sh",
        ]
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
