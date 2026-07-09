from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from jetson_fw.config.model import BuildConfig, export_schema

BASE: dict[str, Any] = {
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
    "bsp": {"overlays": []},
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


def test_model_accepts_non_default_l4t_release_and_derives_kernel_tag() -> None:
    custom = dict(BASE)
    custom["l4t"] = dict(BASE["l4t"])
    custom["l4t"]["release"] = "35.6.4"
    custom["kernel"] = {"defconfig": "tegra_defconfig"}

    config = BuildConfig.model_validate(custom)
    assert config.l4t.release == "35.6.4"
    assert config.kernel.source_tag == "jetson_35.6.4"


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


def test_custom_flash_config_allowed_for_module() -> None:
    custom = dict(BASE)
    custom["targets"] = [
        {
            "name": "air-020",
            "module": "p3767",
            "flash_config": "air-020-production",
            "root_device": "internal",
            "enabled": True,
        }
    ]
    config = BuildConfig.model_validate(custom)
    assert config.targets[0].flash_config == "air-020-production"


def test_effective_target_overrides_merge_with_shared_values() -> None:
    merged = dict(BASE)
    merged["kernel"] = {
        "source_tag": "jetson_35.2.1",
        "defconfig": "tegra_defconfig",
        "extra_dts": ["/tmp/shared.dts"],
    }
    merged["rootfs"] = {
        "install_modules": True,
        "extra_packages": ["curl"],
        "overlays": [{"src": "/tmp/shared-rootfs", "dest": "/etc"}],
    }
    merged["bsp"] = {"overlays": [{"src": "/tmp/shared-bsp", "dest": "/bootloader/shared"}]}
    merged["targets"] = [
        {
            "name": "air-021",
            "module": "p3767",
            "flash_config": "air-021-production",
            "root_device": "internal",
            "enabled": True,
            "kernel": {"extra_dts": ["/tmp/target.dts"], "defconfig": "defconfig_air021"},
            "rootfs": {
                "install_modules": False,
                "extra_packages": ["vim"],
                "overlays": [{"src": "/tmp/target-rootfs", "dest": "/opt"}],
            },
            "bsp": {"overlays": [{"src": "/tmp/target-bsp", "dest": "/bootloader/target"}]},
        }
    ]
    config = BuildConfig.model_validate(merged)
    target = config.targets[0]

    kernel = config.effective_kernel(target)
    assert kernel.defconfig == "defconfig_air021"
    assert [str(path) for path in kernel.extra_dts] == ["/tmp/shared.dts", "/tmp/target.dts"]

    rootfs = config.effective_rootfs(target)
    assert rootfs.install_modules is False
    assert rootfs.extra_packages == ["curl", "vim"]
    assert [overlay.dest for overlay in rootfs.overlays] == ["/etc", "/opt"]

    bsp = config.effective_bsp(target)
    assert [overlay.dest for overlay in bsp.overlays] == [
        "/bootloader/shared",
        "/bootloader/target",
    ]


def test_invalid_volume_rejected() -> None:
    invalid = dict(BASE)
    invalid["docker"] = dict(BASE["docker"])
    invalid["docker"]["volumes"] = ["broken-volume"]
    with pytest.raises(ValidationError):
        BuildConfig.model_validate(invalid)


def test_invalid_bsp_overlay_destination_rejected() -> None:
    invalid = dict(BASE)
    invalid["bsp"] = {"overlays": [{"src": "/tmp/bootloader.dtb", "dest": "bootloader/dtb"}]}
    with pytest.raises(ValidationError):
        BuildConfig.model_validate(invalid)
