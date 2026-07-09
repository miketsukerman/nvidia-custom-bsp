"""Tests for the patch_kernel stage commands."""

from __future__ import annotations

from pathlib import Path

from jetson_fw.config.model import BuildConfig
from jetson_fw.docker.runner import DockerRunner
from jetson_fw.stages.base import StageContext
from jetson_fw.stages.patch_kernel import PatchKernelStage
from jetson_fw.utils.logging import get_logger
from jetson_fw.utils.shell import ShellRunner


def build_config(
    tmp_path: Path,
    global_patches: list[str] | None = None,
    target_patches: list[str] | None = None,
) -> BuildConfig:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(exist_ok=True)
    dockerfile = repo_root / "docker" / "Dockerfile"
    dockerfile.parent.mkdir()
    dockerfile.write_text("FROM ubuntu:20.04\n", encoding="utf-8")
    kernel: dict[str, object] = {"source_tag": "jetson_35.2.1", "defconfig": "tegra_defconfig"}
    if global_patches is not None:
        kernel["patches"] = global_patches
    target_kernel: dict[str, object] = {}
    if target_patches is not None:
        target_kernel["patches"] = target_patches
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
                    **({"kernel": target_kernel} if target_kernel else {}),
                }
            ],
        }
    )
    config.attach_metadata(repo_root / "configs" / "sample.yaml", repo_root / "configs", repo_root)
    return config


def make_context(config: BuildConfig, *, with_target: bool = False) -> StageContext:
    logger = get_logger()
    return StageContext(
        config=config,
        docker=DockerRunner(config, ShellRunner(logger)),
        logger=logger,
        target=config.targets[0] if with_target else None,
    )


def test_patch_kernel_no_patches_emits_noop(tmp_path: Path) -> None:
    config = build_config(tmp_path)
    context = make_context(config)
    cmds = PatchKernelStage().commands(context)
    assert cmds == [":"]


def test_patch_kernel_single_patch_emits_git_apply(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    patch_host = repo_root / "patches" / "fix-usb.patch"
    patch_host.parent.mkdir(parents=True)
    patch_host.write_text("--- a/drivers/usb/core/hub.c\n", encoding="utf-8")
    config = build_config(tmp_path, global_patches=[str(patch_host)])
    context = make_context(config)

    source_dir = "/workspace/build/Linux_for_Tegra/sources/kernel/kernel-5.10"
    expected_patch = "/workspace/repo/patches/fix-usb.patch"
    cmds = PatchKernelStage().commands(context)

    assert len(cmds) == 1
    assert cmds[0] == f"git -C {source_dir} apply --whitespace=fix {expected_patch}"


def test_patch_kernel_multiple_patches_emits_one_command_per_patch(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    patches_dir = repo_root / "patches"
    patches_dir.mkdir(parents=True)
    patch1 = patches_dir / "0001-fix-usb.patch"
    patch2 = patches_dir / "0002-fix-net.patch"
    patch1.write_text("--- a/drivers/usb/core/hub.c\n", encoding="utf-8")
    patch2.write_text("--- a/drivers/net/ethernet/intel/igb/igb_main.c\n", encoding="utf-8")

    config = build_config(tmp_path, global_patches=[str(patch1), str(patch2)])
    context = make_context(config)

    cmds = PatchKernelStage().commands(context)
    assert len(cmds) == 2
    assert all("git -C" in cmd and "apply --whitespace=fix" in cmd for cmd in cmds)
    assert any("0001-fix-usb.patch" in cmd for cmd in cmds)
    assert any("0002-fix-net.patch" in cmd for cmd in cmds)


def test_patch_kernel_target_patches_appended_to_global(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    patches_dir = repo_root / "patches"
    patches_dir.mkdir(parents=True)
    global_patch = patches_dir / "global.patch"
    target_patch = patches_dir / "target.patch"
    global_patch.write_text("--- a/drivers/usb/core/hub.c\n", encoding="utf-8")
    target_patch.write_text("--- a/arch/arm64/boot/dts/nvidia/tegra194.dtsi\n", encoding="utf-8")

    config = build_config(
        tmp_path,
        global_patches=[str(global_patch)],
        target_patches=[str(target_patch)],
    )
    context = make_context(config, with_target=True)

    cmds = PatchKernelStage().commands(context)
    assert len(cmds) == 2
    assert any("global.patch" in cmd for cmd in cmds)
    assert any("target.patch" in cmd for cmd in cmds)
    # global patch is applied first
    assert "global.patch" in cmds[0]
    assert "target.patch" in cmds[1]
