from __future__ import annotations

from pathlib import Path

from jetson_fw.config.model import BuildConfig
from jetson_fw.docker.runner import DockerRunner
from jetson_fw.stages.base import StageContext
from jetson_fw.stages.build_kernel import BuildKernelStage
from jetson_fw.utils.logging import get_logger
from jetson_fw.utils.shell import ShellRunner


def build_config(
    tmp_path: Path, extra_dts: list[str] | None = None, fragments: list[str] | None = None
) -> BuildConfig:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(exist_ok=True)
    dockerfile = repo_root / "docker" / "Dockerfile"
    dockerfile.parent.mkdir()
    dockerfile.write_text("FROM ubuntu:20.04\n", encoding="utf-8")
    kernel: dict = {"source_tag": "jetson_35.2.1", "defconfig": "tegra_defconfig"}
    if extra_dts:
        kernel["extra_dts"] = extra_dts
    if fragments:
        kernel["config_fragments"] = fragments
    config = BuildConfig.model_validate(
        {
            "version": 1,
            "docker": {
                "image": "builder:latest",
                "dockerfile": str(dockerfile),
                "build": True,
                "registry": "",
                "privileged_for_flash": False,
                "devices": ["/dev/bus/usb"],
                "volumes": [f"{tmp_path}/build:/workspace/build:rw"],
                "environment": {"JOBS": "8"},
            },
            "l4t": {
                "release": "35.2.1",
                "bsp_url": "https://example.com/bsp.tbz2",
                "bsp_sha256": "1" * 64,
                "sample_rootfs_url": "https://example.com/rootfs.tbz2",
                "sample_rootfs_sha256": "2" * 64,
            },
            "toolchain": {
                "url": "https://example.com/toolchain.tar.xz",
                "sha256": "3" * 64,
            },
            "workspace": {"root": "/workspace/build"},
            "kernel": kernel,
            "rootfs": {"install_modules": True, "extra_packages": [], "overlays": []},
            "targets": [
                {
                    "name": "xavier-nx",
                    "module": "p3668",
                    "flash_config": "jetson-xavier-nx-devkit-emmc",
                    "root_device": "mmcblk0p1",
                    "enabled": True,
                }
            ],
        }
    )
    config.attach_metadata(repo_root / "configs" / "sample.yaml", repo_root / "configs", repo_root)
    return config


def make_context(config: BuildConfig) -> StageContext:
    logger = get_logger()
    return StageContext(
        config=config,
        docker=DockerRunner(config, ShellRunner(logger)),
        logger=logger,
    )


def test_build_kernel_passes_arch_and_cross_compile_to_make(tmp_path: Path) -> None:
    config = build_config(tmp_path)
    context = make_context(config)

    source_dir = "/workspace/build/Linux_for_Tegra/source/public/kernel/kernel-5.10"
    out_dir = "/workspace/build/out/kernel"
    cross_compile = "/workspace/build/toolchain/bin/aarch64-buildroot-linux-gnu-"
    make_vars = f"ARCH=arm64 CROSS_COMPILE={cross_compile}"

    cmds = BuildKernelStage().commands(context)

    assert f"make -C {source_dir} O={out_dir} {make_vars} tegra_defconfig" in cmds
    assert (
        f"make -C {source_dir} O={out_dir} {make_vars} Image dtbs modules -j${{JOBS:-$(nproc)}}"
        in cmds
    )


def test_build_kernel_no_extra_dts_no_fragments(tmp_path: Path) -> None:
    config = build_config(tmp_path)
    context = make_context(config)

    out_dir = "/workspace/build/out/kernel"
    cmds = BuildKernelStage().commands(context)

    assert cmds[0] == f"mkdir -p {out_dir}"
    # No mkdir for dts, no cp commands
    assert not any("arch/arm64/boot/dts" in c for c in cmds)
    # No merge_config
    assert not any("merge_config" in c for c in cmds)
    assert len(cmds) == 3  # mkdir, defconfig make, image make


def test_build_kernel_with_extra_dts(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    dts_host = repo_root / "fixtures" / "dts" / "xavier-carrier.dts"
    dts_host.parent.mkdir(parents=True)
    dts_host.write_text("", encoding="utf-8")
    config = build_config(tmp_path, extra_dts=[str(dts_host)])
    context = make_context(config)

    source_dir = "/workspace/build/Linux_for_Tegra/source/public/kernel/kernel-5.10"
    expected_container_dts = "/workspace/repo/fixtures/dts/xavier-carrier.dts"
    cmds = BuildKernelStage().commands(context)

    assert f"mkdir -p {source_dir}/arch/arm64/boot/dts" in cmds
    assert any(f"cp {expected_container_dts}" in c for c in cmds)


def test_build_kernel_with_config_fragment(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    frag_host = repo_root / "fixtures" / "configs" / "enable-can.config"
    frag_host.parent.mkdir(parents=True)
    frag_host.write_text("", encoding="utf-8")
    config = build_config(tmp_path, fragments=[str(frag_host)])
    context = make_context(config)

    expected_container_frag = "/workspace/repo/fixtures/configs/enable-can.config"
    cmds = BuildKernelStage().commands(context)

    assert any("merge_config.sh" in c and expected_container_frag in c for c in cmds)
    # merge_config comes after defconfig make
    defconfig_idx = next(i for i, c in enumerate(cmds) if "tegra_defconfig" in c)
    merge_idx = next(i for i, c in enumerate(cmds) if "merge_config.sh" in c)
    assert merge_idx > defconfig_idx
