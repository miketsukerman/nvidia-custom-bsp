from __future__ import annotations

from pathlib import Path

from jetson_fw.config.model import BuildConfig
from jetson_fw.docker.runner import DockerRunner
from jetson_fw.stages.assemble_rootfs import AssembleRootfsStage
from jetson_fw.stages.base import StageContext
from jetson_fw.utils.logging import get_logger
from jetson_fw.utils.shell import ShellRunner


def build_config(tmp_path: Path, *, target_rootfs: dict[str, object] | None = None) -> BuildConfig:
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
                    **({"rootfs": target_rootfs} if target_rootfs else {}),
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


def test_assemble_rootfs_installs_modules_from_synced_kernel_tree(tmp_path: Path) -> None:
    config = build_config(tmp_path)
    context = make_context(config)

    l4t_dir = "/workspace/build/Linux_for_Tegra"
    rootfs_dir = f"{l4t_dir}/rootfs"
    kernel_source = "/workspace/build/Linux_for_Tegra/sources/kernel/kernel-5.10"
    out_dir = "/workspace/build/out/kernel"

    assert AssembleRootfsStage().commands(context) == [
        f"rm -f {rootfs_dir}/usr/local/bin/nvgpuswitch.py",
        f"rm -f {rootfs_dir}/dev/random {rootfs_dir}/dev/urandom",
        f"cd {l4t_dir} && ./apply_binaries.sh",
        f"make -C {kernel_source} O={out_dir} modules_install INSTALL_MOD_PATH={rootfs_dir}",
    ]


def test_assemble_rootfs_includes_target_rootfs_overrides(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    target_overlay = repo_root / "fixtures" / "rootfs" / "target"
    target_overlay.mkdir(parents=True)
    (target_overlay / "file.txt").write_text("x", encoding="utf-8")
    config = build_config(
        tmp_path,
        target_rootfs={
            "install_modules": False,
            "extra_packages": ["vim"],
            "overlays": [{"src": str(target_overlay), "dest": "/opt/air020"}],
        },
    )
    context = make_context(config, with_target=True)
    commands = AssembleRootfsStage().commands(context)

    assert not any("modules_install" in command for command in commands)
    assert any("apt-get install -y vim" in command for command in commands)
    assert any("/workspace/repo/fixtures/rootfs/target/." in command for command in commands)
