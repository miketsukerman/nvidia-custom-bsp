"""Build kernel image, device trees, and modules."""

from __future__ import annotations

from .base import Stage, StageContext


class BuildKernelStage(Stage):
    name = "build_kernel"
    dependencies = ("toolchain", "source_sync")

    def commands(self, context: StageContext) -> list[str]:
        source_dir = context.kernel_source_dir
        out_dir = context.workspace / "out" / "kernel"
        cross_compile = (
            f"{context.workspace}/toolchain/bin/" f"{context.config.toolchain.cross_compile_prefix}"
        )
        make_vars = f"ARCH=arm64 CROSS_COMPILE={cross_compile}"
        commands = [
            f"mkdir -p {out_dir}",
        ]
        if context.config.kernel.extra_dts:
            commands.append(f"mkdir -p {source_dir}/arch/arm64/boot/dts")
        for dts in context.config.kernel.extra_dts:
            commands.append(f"cp {context.repo_path(dts)} {source_dir}/arch/arm64/boot/dts/")
        commands.append(
            f"cd {source_dir} && make {make_vars} O={out_dir} {context.config.kernel.defconfig}"
        )
        if context.config.kernel.config_fragments:
            fragments = " ".join(
                str(context.repo_path(fragment))
                for fragment in context.config.kernel.config_fragments
            )
            commands.append(
                f"cd {source_dir} && {make_vars} {source_dir}/scripts/kconfig/merge_config.sh -O {out_dir} {out_dir}/.config {fragments}"
            )
        commands.append(
            f"cd {source_dir} && make {make_vars} O={out_dir} Image dtbs modules -j${{JOBS:-$(nproc)}}"
        )
        return commands
