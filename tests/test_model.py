from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from jetson_fw.config.model import BuildConfig, export_schema

BASE = {
    "version": 1,
    "docker": {
        "image": "builder:latest",
        "dockerfile": "/tmp/Dockerfile",
        "build": True,
        "registry": "",
        "privileged_for_flash": True,
        "devices": ["/dev/bus/usb"],
        "volumes": ["/tmp/build:/workspace/build"],
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
        "name": "bootlin-gcc-9.3",
        "url": "https://example.com/toolchain.tar.xz",
        "sha256": "3" * 64,
        "cross_compile_prefix": "aarch64-buildroot-linux-gnu-",
    },
    "workspace": {"root": "/workspace/build", "keep_intermediate": True},
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


def test_valid_model_accepts_defaults(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    config = BuildConfig.model_validate(BASE)
    export_schema(schema_path)
    assert config.workspace.root == Path("/workspace/build")
    assert schema_path.exists()


def test_invalid_flash_config_rejected() -> None:
    invalid = dict(BASE)
    invalid["targets"] = [
        {
            "name": "orin-nx",
            "module": "p3767",
            "flash_config": "jetson-xavier-nx-devkit-emmc",
            "root_device": "internal",
            "enabled": True,
        }
    ]
    with pytest.raises(ValidationError):
        BuildConfig.model_validate(invalid)


def test_invalid_volume_rejected() -> None:
    invalid = dict(BASE)
    invalid["docker"] = dict(BASE["docker"])
    invalid["docker"]["volumes"] = ["broken-volume"]
    with pytest.raises(ValidationError):
        BuildConfig.model_validate(invalid)
