from __future__ import annotations

from pathlib import Path

from jetson_fw.config.model import BuildConfig
from jetson_fw.docker.runner import DockerRunner
from jetson_fw.stages.base import StageContext
from jetson_fw.stages.customize_bsp import CustomizeBspStage
from jetson_fw.utils.logging import get_logger
from jetson_fw.utils.shell import ShellRunner


def build_config(tmp_path: Path, *, overlays: list[dict[str, str]] | None = None) -> BuildConfig:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(exist_ok=True)
    dockerfile = repo_root / "docker" / "Dockerfile"
    dockerfile.parent.mkdir()
    dockerfile.write_text("FROM ubuntu:20.04\n", encoding="utf-8")
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
            "kernel": {"source_tag": "jetson_35.2.1", "defconfig": "tegra_defconfig"},
            "rootfs": {"install_modules": True, "extra_packages": [], "overlays": []},
            "bsp": {"overlays": overlays or []},
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


def test_customize_bsp_stage_is_noop_without_overlays(tmp_path: Path) -> None:
    config = build_config(tmp_path)

    assert CustomizeBspStage().commands(make_context(config)) == [":"]


def test_customize_bsp_stage_copies_directory_overlays_into_l4t(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    source_dir = repo_root / "fixtures" / "bootloader" / "t186ref" / "BCT"
    source_dir.mkdir(parents=True)
    (source_dir / "tegra194-mb1-bct-device-prod.cfg").write_text("", encoding="utf-8")
    config = build_config(
        tmp_path,
        overlays=[
            {
                "src": str(source_dir),
                "dest": "/bootloader/t186ref/BCT",
            }
        ],
    )

    assert CustomizeBspStage().commands(make_context(config)) == [
        "mkdir -p /workspace/build/Linux_for_Tegra/bootloader/t186ref/BCT && cp -a "
        "/workspace/repo/fixtures/bootloader/t186ref/BCT/. "
        "/workspace/build/Linux_for_Tegra/bootloader/t186ref/BCT"
    ]


def test_customize_bsp_stage_copies_file_overlays_into_l4t(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    source_file = repo_root / "fixtures" / "bootloader" / "kernel_tegra194-p3668.dtb"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("", encoding="utf-8")
    config = build_config(
        tmp_path,
        overlays=[
            {
                "src": str(source_file),
                "dest": "/bootloader/kernel_tegra194-p3668.dtb",
            }
        ],
    )

    assert CustomizeBspStage().commands(make_context(config)) == [
        "mkdir -p /workspace/build/Linux_for_Tegra/bootloader && cp -a "
        "/workspace/repo/fixtures/bootloader/kernel_tegra194-p3668.dtb "
        "/workspace/build/Linux_for_Tegra/bootloader/kernel_tegra194-p3668.dtb"
    ]
