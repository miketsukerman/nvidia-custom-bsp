from __future__ import annotations

from pathlib import Path

from jetson_fw.config.model import BuildConfig
from jetson_fw.docker.runner import DockerRunner
from jetson_fw.stages.base import StageContext
from jetson_fw.stages.source_sync import PROMETHEUS_DTS_SOURCE, SourceSyncStage
from jetson_fw.utils.logging import get_logger
from jetson_fw.utils.shell import ShellRunner


def build_config(tmp_path: Path, *, target_kernel: dict[str, object] | None = None) -> BuildConfig:
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
                    **({"kernel": target_kernel} if target_kernel else {}),
                }
            ],
        }
    )
    config.attach_metadata(repo_root / "configs" / "sample.yaml", repo_root / "configs", repo_root)
    return config


def test_source_sync_stage_uses_kernel_only_mode(tmp_path: Path) -> None:
    config = build_config(tmp_path)
    logger = get_logger()
    context = StageContext(
        config=config,
        docker=DockerRunner(config, ShellRunner(logger)),
        logger=logger,
    )
    escaped_source = PROMETHEUS_DTS_SOURCE.replace("/", r"\/")

    assert SourceSyncStage().commands(context) == [
        f"sed '/{escaped_source}/d' /workspace/build/Linux_for_Tegra/source_sync.sh > /workspace/build/Linux_for_Tegra/source_sync.filtered.sh",
        "chmod +x /workspace/build/Linux_for_Tegra/source_sync.filtered.sh",
        "/workspace/build/Linux_for_Tegra/source_sync.filtered.sh -k jetson_35.2.1",
        "rm -f /workspace/build/Linux_for_Tegra/source_sync.filtered.sh",
    ]


def test_source_sync_stage_uses_target_kernel_source_tag_override(tmp_path: Path) -> None:
    config = build_config(tmp_path, target_kernel={"source_tag": "jetson_35.2.1-custom"})
    logger = get_logger()
    context = StageContext(
        config=config,
        docker=DockerRunner(config, ShellRunner(logger)),
        logger=logger,
        target=config.targets[0],
    )

    commands = SourceSyncStage().commands(context)
    assert (
        commands[2]
        == "/workspace/build/Linux_for_Tegra/source_sync.filtered.sh -k jetson_35.2.1-custom"
    )
