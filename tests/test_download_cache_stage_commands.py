from __future__ import annotations

from pathlib import Path

from jetson_fw.config.model import BuildConfig
from jetson_fw.docker.runner import DockerRunner
from jetson_fw.stages.base import StageContext
from jetson_fw.stages.fetch_bsp import FetchBspStage
from jetson_fw.stages.toolchain import ToolchainStage
from jetson_fw.utils.logging import get_logger
from jetson_fw.utils.shell import ShellRunner


def build_config(tmp_path: Path) -> BuildConfig:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
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


def test_fetch_bsp_stage_uses_cache_aware_download_commands(tmp_path: Path) -> None:
    config = build_config(tmp_path)
    logger = get_logger()
    context = StageContext(
        config=config,
        docker=DockerRunner(config, ShellRunner(logger)),
        logger=logger,
    )

    downloads = context.workspace / "downloads"
    l4t_dir = context.workspace / "Linux_for_Tegra"
    bsp_archive = downloads / "jetson_linux.tbz2"
    rootfs_archive = downloads / "sample_rootfs.tbz2"

    assert FetchBspStage().commands(context) == [
        f"mkdir -p {downloads} {l4t_dir}/rootfs",
        f"if [ ! -f {bsp_archive} ]; then wget -O {bsp_archive} {context.config.l4t.bsp_url}; fi",
        f"echo '{context.config.l4t.bsp_sha256}  {bsp_archive}' | sha256sum -c -",
        f"tar -xjf {bsp_archive} -C {context.workspace}",
        f"if [ ! -f {rootfs_archive} ]; then wget -O {rootfs_archive} {context.config.l4t.sample_rootfs_url}; fi",
        f"echo '{context.config.l4t.sample_rootfs_sha256}  {rootfs_archive}' | sha256sum -c -",
        f"tar -xjf {rootfs_archive} -C {l4t_dir}/rootfs",
    ]


def test_toolchain_stage_uses_cache_aware_download_commands(tmp_path: Path) -> None:
    config = build_config(tmp_path)
    logger = get_logger()
    context = StageContext(
        config=config,
        docker=DockerRunner(config, ShellRunner(logger)),
        logger=logger,
    )

    downloads = context.workspace / "downloads"
    archive = downloads / "toolchain.tar.xz"
    toolchain_root = context.workspace / "toolchain"

    assert ToolchainStage().commands(context) == [
        f"mkdir -p {downloads} {toolchain_root}",
        f"if [ ! -f {archive} ]; then wget -O {archive} {context.config.toolchain.url}; fi",
        f"echo '{context.config.toolchain.sha256}  {archive}' | sha256sum -c -",
        f"tar -xf {archive} -C {toolchain_root} --strip-components=1",
    ]
