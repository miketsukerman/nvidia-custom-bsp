from __future__ import annotations

from pathlib import Path

from jetson_fw.config.model import BuildConfig
from jetson_fw.docker.runner import DockerRunner
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


def test_build_run_command_includes_mounts_and_devices(tmp_path: Path) -> None:
    config = build_config(tmp_path)
    shell = ShellRunner(get_logger())
    runner = DockerRunner(config, shell)
    command = runner.build_run_command("echo hi", flash=True)
    assert "--rm" in command
    assert f"{config.repo_root}:{runner.repo_mount}" in command
    assert "--privileged" not in command
    assert "/dev/bus/usb:/dev/bus/usb" in " ".join(command)
    assert "--entrypoint" in command
    assert command[command.index("--entrypoint") + 1] == "bash"
