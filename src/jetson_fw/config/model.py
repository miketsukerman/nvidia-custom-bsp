"""Typed build configuration model."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, ValidationInfo, field_validator, model_validator


class ModuleEnum(str, Enum):
    """Supported Jetson modules."""

    XAVIER_NX = "p3668"
    ORIN_NX = "p3767"


class FlashConfigEnum(str, Enum):
    """Supported L4T R35.2.1 flash configurations."""

    XAVIER_NX_DEVKIT_EMMC = "jetson-xavier-nx-devkit-emmc"
    ORIN_NANO_DEVKIT = "jetson-orin-nano-devkit"


class RootDeviceEnum(str, Enum):
    """Supported root device targets."""

    MMCBLK0P1 = "mmcblk0p1"
    INTERNAL = "internal"


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


class L4TConfig(BaseModel):
    """Jetson Linux archive inputs."""

    release: str = Field(default="35.2.1", description="L4T release version")
    bsp_url: HttpUrl = Field(description="URL to Jetson Linux BSP archive")
    bsp_sha256: str = Field(description="SHA256 for bsp_url artifact")
    sample_rootfs_url: HttpUrl = Field(description="URL to sample root filesystem archive")
    sample_rootfs_sha256: str = Field(description="SHA256 for sample_rootfs_url artifact")

    @field_validator("bsp_sha256", "sample_rootfs_sha256")
    @classmethod
    def validate_sha(cls, value: str) -> str:
        if not _is_sha256(value):
            raise ValueError("must be a 64-character SHA256 hex digest")
        return value.lower()


class ToolchainConfig(BaseModel):
    """Cross compilation toolchain metadata."""

    name: str = Field(default="bootlin-gcc-9.3", description="Toolchain name identifier")
    url: HttpUrl = Field(description="Toolchain archive URL")
    sha256: str = Field(description="SHA256 for toolchain archive")
    cross_compile_prefix: str = Field(
        default="aarch64-buildroot-linux-gnu-",
        description="Cross-compiler prefix used for kernel build",
    )

    @field_validator("sha256")
    @classmethod
    def validate_sha(cls, value: str) -> str:
        if not _is_sha256(value):
            raise ValueError("must be a 64-character SHA256 hex digest")
        return value.lower()


class WorkspaceConfig(BaseModel):
    """Local workspace layout options."""

    root: Path = Field(default=Path("./build"), description="Build workspace root path")
    keep_intermediate: bool = Field(default=True, description="Keep intermediate artifacts")


class KernelConfig(BaseModel):
    """Kernel build options."""

    source_tag: str = Field(default="jetson_35.2.1", description="Tag used with source_sync.sh -t")
    defconfig: str = Field(default="tegra_defconfig", description="Kernel defconfig target")
    config_fragments: list[Path] = Field(
        default_factory=list,
        description="Optional kernel config fragment files",
    )
    extra_dts: list[Path] = Field(
        default_factory=list,
        description="Optional custom DTS files to include/build",
    )


class RootfsOverlay(BaseModel):
    """Overlay content copied into rootfs."""

    src: Path = Field(description="Source file/directory path")
    dest: str = Field(description="Absolute destination path within rootfs")

    @field_validator("dest")
    @classmethod
    def validate_dest(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("must be an absolute rootfs path starting with '/'")
        return value


class RootfsConfig(BaseModel):
    """Rootfs customization options."""

    install_modules: bool = Field(default=True, description="Install kernel modules into rootfs")
    extra_packages: list[str] = Field(default_factory=list, description="Optional apt package names")
    overlays: list[RootfsOverlay] = Field(
        default_factory=list,
        description="Files/directories copied into rootfs",
    )


class TargetConfig(BaseModel):
    """Per-target flashing options."""

    name: str = Field(description="Target name used by CLI")
    module: ModuleEnum = Field(description="Jetson module identifier")
    flash_config: FlashConfigEnum = Field(description="flash.sh board config name")
    root_device: RootDeviceEnum = Field(description="flash.sh root device argument")
    enabled: bool = Field(default=True, description="Whether target is active for build/all commands")


class BuildConfig(BaseModel):
    """Root build configuration."""

    version: Literal[1] = Field(default=1, description="Schema version")
    l4t: L4TConfig
    toolchain: ToolchainConfig
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    kernel: KernelConfig = Field(default_factory=KernelConfig)
    rootfs: RootfsConfig = Field(default_factory=RootfsConfig)
    targets: list[TargetConfig] = Field(min_length=1)

    @field_validator("targets")
    @classmethod
    def ensure_enabled_target(cls, targets: list[TargetConfig]) -> list[TargetConfig]:
        if not any(target.enabled for target in targets):
            raise ValueError("at least one target must be enabled")
        return targets

    @model_validator(mode="after")
    def validate_target_compatibility(self) -> "BuildConfig":
        target_names: set[str] = set()
        for target in self.targets:
            if target.name in target_names:
                raise ValueError(f"duplicate target name '{target.name}'")
            target_names.add(target.name)

            if target.module == ModuleEnum.ORIN_NX and target.flash_config != FlashConfigEnum.ORIN_NANO_DEVKIT:
                raise ValueError(
                    "Orin NX module p3767 must use flash_config 'jetson-orin-nano-devkit' on R35.2.1"
                )
            if target.module == ModuleEnum.XAVIER_NX and target.flash_config != FlashConfigEnum.XAVIER_NX_DEVKIT_EMMC:
                raise ValueError("Xavier NX module p3668 must use flash_config 'jetson-xavier-nx-devkit-emmc'")

        if self.l4t.release != "35.2.1":
            raise ValueError("this tool currently supports L4T release 35.2.1 only")
        if self.kernel.source_tag != "jetson_35.2.1":
            raise ValueError("kernel.source_tag must be 'jetson_35.2.1' for L4T R35.2.1 builds")
        return self


def export_schema(path: Path) -> None:
    """Write JSON schema for BuildConfig."""

    path.write_text(BuildConfig.model_json_schema_json(indent=2), encoding="utf-8")
