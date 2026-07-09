"""Typed build configuration model."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    PrivateAttr,
    field_validator,
    model_validator,
)


class ModuleEnum(str, Enum):
    """Supported Jetson modules."""

    XAVIER_NX = "p3668"
    ORIN_NX = "p3767"


class RootDeviceEnum(str, Enum):
    """Supported root device targets."""

    MMCBLK0P1 = "mmcblk0p1"
    NVME0N1 = "nvme0n1"
    INTERNAL = "internal"


class DockerConfig(BaseModel):
    """Docker execution settings."""

    model_config = ConfigDict(extra="forbid")

    image: str = Field(description="Docker image tag used for builder containers")
    dockerfile: Path = Field(
        default=Path("docker/Dockerfile"),
        description="Path to Dockerfile used when build is true",
    )
    build: bool = Field(default=True, description="Build image locally instead of pulling")
    registry: str = Field(default="", description="Optional registry prefix for image pulls/builds")
    privileged_for_flash: bool = Field(
        default=True,
        description="Run flash containers with --privileged",
    )
    devices: list[Path] = Field(
        default_factory=lambda: [Path("/dev/bus/usb")],
        description="Host device paths passed through for flashing",
    )
    volumes: list[str] = Field(
        default_factory=lambda: ["./build:/workspace/build"],
        description="Additional host:container[:mode] bind mounts",
    )
    environment: dict[str, str] = Field(
        default_factory=lambda: {"JOBS": "8"},
        description="Additional environment variables for the container",
    )

    @field_validator("image")
    @classmethod
    def validate_image(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or "://" in cleaned or " " in cleaned:
            raise ValueError("must be a valid Docker image reference")
        return cleaned

    @field_validator("registry")
    @classmethod
    def validate_registry(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        if " " in cleaned:
            raise ValueError("must not contain spaces")
        return cleaned

    @field_validator("devices")
    @classmethod
    def validate_devices(cls, values: list[Path]) -> list[Path]:
        for value in values:
            if not str(value).startswith("/"):
                raise ValueError(f"device path '{value}' must be absolute")
        return values

    @field_validator("volumes")
    @classmethod
    def validate_volumes(cls, values: list[str]) -> list[str]:
        for value in values:
            parts = value.split(":")
            if len(parts) not in {2, 3}:
                raise ValueError(f"volume '{value}' must use host:container[:mode] syntax")
            host, container = parts[0], parts[1]
            if not host:
                raise ValueError(f"volume '{value}' is missing a host path")
            if not container.startswith("/"):
                raise ValueError(f"volume '{value}' must mount to an absolute container path")
            if len(parts) == 3 and parts[2] not in {"ro", "rw"}:
                raise ValueError(f"volume '{value}' has unsupported mode '{parts[2]}'")
        return values

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, values: dict[str, str]) -> dict[str, str]:
        for key in values:
            if not key or any(char.isspace() for char in key) or "=" in key:
                raise ValueError(f"environment key '{key}' is invalid")
        return values

    @model_validator(mode="after")
    def validate_flash_settings(self) -> DockerConfig:
        if not self.privileged_for_flash and not self.devices:
            raise ValueError("docker.devices must be set when privileged_for_flash is false")
        return self


class L4TConfig(BaseModel):
    """Jetson Linux archive inputs."""

    model_config = ConfigDict(extra="forbid")

    release: str = Field(default="35.2.1", description="L4T release version")
    bsp_url: HttpUrl = Field(description="URL to Jetson Linux BSP archive")
    bsp_sha256: str = Field(description="SHA256 for bsp_url artifact")
    sample_rootfs_url: HttpUrl = Field(description="URL to sample root filesystem archive")
    sample_rootfs_sha256: str = Field(description="SHA256 for sample_rootfs_url artifact")

    @field_validator("bsp_sha256", "sample_rootfs_sha256")
    @classmethod
    def validate_sha(cls, value: str) -> str:
        return _validate_sha256(value)


class ToolchainConfig(BaseModel):
    """Cross compilation toolchain metadata."""

    model_config = ConfigDict(extra="forbid")

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
        return _validate_sha256(value)


class WorkspaceConfig(BaseModel):
    """Workspace options inside the builder container."""

    model_config = ConfigDict(extra="forbid")

    root: Path = Field(
        default=Path("/workspace/build"), description="Workspace root inside container"
    )
    keep_intermediate: bool = Field(default=True, description="Keep intermediate artifacts")

    @field_validator("root")
    @classmethod
    def validate_root(cls, value: Path) -> Path:
        if not str(value).startswith("/"):
            raise ValueError("workspace.root must be an absolute path inside the container")
        return value


class KernelConfig(BaseModel):
    """Kernel build options."""

    model_config = ConfigDict(extra="forbid")

    source_tag: str = Field(
        default="",
        description=(
            "Kernel/device-tree tag used for the filtered source_sync.sh kernel sync; "
            "defaults to jetson_<l4t.release> when omitted"
        ),
    )
    defconfig: str = Field(default="tegra_defconfig", description="Kernel defconfig target")
    config_fragments: list[Path] = Field(
        default_factory=list,
        description="Optional kernel config fragment files",
    )
    extra_dts: list[Path] = Field(
        default_factory=list,
        description="Optional custom DTS files to include in the build",
    )


class RootfsOverlay(BaseModel):
    """Overlay content copied into rootfs."""

    model_config = ConfigDict(extra="forbid")

    src: Path = Field(description="Source file or directory path")
    dest: str = Field(description="Absolute destination path within rootfs")

    @field_validator("dest")
    @classmethod
    def validate_dest(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("must be an absolute rootfs path starting with '/'")
        return value


class RootfsConfig(BaseModel):
    """Rootfs customization options."""

    model_config = ConfigDict(extra="forbid")

    install_modules: bool = Field(default=True, description="Install kernel modules into rootfs")
    extra_packages: list[str] = Field(default_factory=list, description="Optional apt packages")
    overlays: list[RootfsOverlay] = Field(
        default_factory=list,
        description="Files or directories copied into rootfs",
    )


class BspOverlay(BaseModel):
    """Files or directories copied into Linux_for_Tegra before later stages."""

    model_config = ConfigDict(extra="forbid")

    src: Path = Field(description="Source file or directory path")
    dest: str = Field(description="Absolute destination path within Linux_for_Tegra")

    @field_validator("dest")
    @classmethod
    def validate_dest(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("must be an absolute Linux_for_Tegra path starting with '/'")
        if ".." in Path(value).parts:
            raise ValueError("must not contain parent-directory traversal")
        return value


class BspConfig(BaseModel):
    """Linux_for_Tegra customization options."""

    model_config = ConfigDict(extra="forbid")

    overlays: list[BspOverlay] = Field(
        default_factory=list,
        description="Files or directories copied into Linux_for_Tegra after extraction",
    )


class TargetKernelConfig(BaseModel):
    """Per-target kernel overrides."""

    model_config = ConfigDict(extra="forbid")

    source_tag: str | None = Field(
        default=None,
        description="Optional kernel/device-tree source tag override for this target",
    )
    defconfig: str | None = Field(
        default=None,
        description="Optional kernel defconfig override for this target",
    )
    config_fragments: list[Path] | None = Field(
        default=None,
        description="Optional additional kernel config fragments for this target",
    )
    extra_dts: list[Path] | None = Field(
        default=None,
        description="Optional additional custom DTS files for this target",
    )


class TargetRootfsConfig(BaseModel):
    """Per-target rootfs overrides."""

    model_config = ConfigDict(extra="forbid")

    install_modules: bool | None = Field(
        default=None,
        description="Optional override for installing kernel modules into rootfs",
    )
    extra_packages: list[str] | None = Field(
        default=None,
        description="Optional additional apt packages for this target",
    )
    overlays: list[RootfsOverlay] | None = Field(
        default=None,
        description="Optional additional files or directories copied into rootfs",
    )


class TargetBspConfig(BaseModel):
    """Per-target Linux_for_Tegra overrides."""

    model_config = ConfigDict(extra="forbid")

    overlays: list[BspOverlay] | None = Field(
        default=None,
        description="Optional additional files or directories copied into Linux_for_Tegra",
    )


class TargetConfig(BaseModel):
    """Per-target flashing options."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Target name used by the CLI")
    module: ModuleEnum = Field(description="Jetson module identifier")
    flash_config: str = Field(description="flash.sh board configuration name")
    root_device: RootDeviceEnum = Field(description="flash.sh root device argument")
    kernel: TargetKernelConfig | None = Field(
        default=None,
        description="Optional per-target kernel overrides",
    )
    rootfs: TargetRootfsConfig | None = Field(
        default=None,
        description="Optional per-target rootfs overrides",
    )
    bsp: TargetBspConfig | None = Field(
        default=None,
        description="Optional per-target Linux_for_Tegra overrides",
    )
    enabled: bool = Field(
        default=True, description="Whether target is active for build/all commands"
    )

    @field_validator("flash_config")
    @classmethod
    def validate_flash_config(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or any(char.isspace() for char in cleaned):
            raise ValueError("flash_config must be a non-empty value without spaces")
        return cleaned


class BuildConfig(BaseModel):
    """Root build configuration."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = Field(default=1, description="Schema version")
    docker: DockerConfig
    l4t: L4TConfig
    toolchain: ToolchainConfig
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    kernel: KernelConfig = Field(default_factory=KernelConfig)
    rootfs: RootfsConfig = Field(default_factory=RootfsConfig)
    bsp: BspConfig = Field(default_factory=BspConfig)
    targets: list[TargetConfig] = Field(
        min_length=1,
        description="Jetson targets sharing the same kernel and rootfs build",
    )

    _config_path: Path | None = PrivateAttr(default=None)
    _base_dir: Path | None = PrivateAttr(default=None)
    _repo_root: Path | None = PrivateAttr(default=None)

    @field_validator("targets")
    @classmethod
    def ensure_enabled_target(cls, targets: list[TargetConfig]) -> list[TargetConfig]:
        if not any(target.enabled for target in targets):
            raise ValueError("at least one target must be enabled")
        return targets

    @model_validator(mode="after")
    def validate_target_compatibility(self) -> BuildConfig:
        known_flash_configs = {
            "jetson-xavier-nx-devkit-emmc": ModuleEnum.XAVIER_NX,
            "jetson-orin-nano-devkit": ModuleEnum.ORIN_NX,
        }
        target_names: set[str] = set()
        for target in self.targets:
            if target.name in target_names:
                raise ValueError(f"duplicate target name '{target.name}'")
            target_names.add(target.name)
            expected_module = known_flash_configs.get(target.flash_config)
            if expected_module is not None and target.module != expected_module:
                raise ValueError(
                    f"flash_config '{target.flash_config}' requires module '{expected_module.value}'"
                )
        if not self.kernel.source_tag:
            self.kernel.source_tag = f"jetson_{self.l4t.release}"
        return self

    @property
    def config_path(self) -> Path:
        if self._config_path is None:
            raise RuntimeError("config metadata has not been attached")
        return self._config_path

    @property
    def base_dir(self) -> Path:
        if self._base_dir is None:
            raise RuntimeError("config metadata has not been attached")
        return self._base_dir

    @property
    def repo_root(self) -> Path:
        if self._repo_root is None:
            raise RuntimeError("config metadata has not been attached")
        return self._repo_root

    def attach_metadata(self, config_path: Path, base_dir: Path, repo_root: Path) -> None:
        self._config_path = config_path
        self._base_dir = base_dir
        self._repo_root = repo_root

    def enabled_targets(self) -> list[TargetConfig]:
        return [target for target in self.targets if target.enabled]

    def get_target(self, name: str) -> TargetConfig:
        for target in self.targets:
            if target.name == name:
                return target
        raise KeyError(name)

    def effective_kernel(self, target: TargetConfig | None = None) -> KernelConfig:
        kernel = self.kernel.model_copy(deep=True)
        if target is None or target.kernel is None:
            return kernel
        if target.kernel.source_tag is not None:
            kernel.source_tag = target.kernel.source_tag
        if target.kernel.defconfig is not None:
            kernel.defconfig = target.kernel.defconfig
        if target.kernel.config_fragments is not None:
            kernel.config_fragments = [*kernel.config_fragments, *target.kernel.config_fragments]
        if target.kernel.extra_dts is not None:
            kernel.extra_dts = [*kernel.extra_dts, *target.kernel.extra_dts]
        return kernel

    def effective_rootfs(self, target: TargetConfig | None = None) -> RootfsConfig:
        rootfs = self.rootfs.model_copy(deep=True)
        if target is None or target.rootfs is None:
            return rootfs
        if target.rootfs.install_modules is not None:
            rootfs.install_modules = target.rootfs.install_modules
        if target.rootfs.extra_packages is not None:
            rootfs.extra_packages = [*rootfs.extra_packages, *target.rootfs.extra_packages]
        if target.rootfs.overlays is not None:
            rootfs.overlays = [*rootfs.overlays, *target.rootfs.overlays]
        return rootfs

    def effective_bsp(self, target: TargetConfig | None = None) -> BspConfig:
        bsp = self.bsp.model_copy(deep=True)
        if target is None or target.bsp is None:
            return bsp
        if target.bsp.overlays is not None:
            bsp.overlays = [*bsp.overlays, *target.bsp.overlays]
        return bsp


def _validate_sha256(value: str) -> str:
    if len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise ValueError("must be a 64-character SHA256 hex digest")
    return value.lower()


def export_schema(path: Path) -> None:
    """Write JSON schema for BuildConfig."""

    path.write_text(json.dumps(BuildConfig.model_json_schema(), indent=2), encoding="utf-8")
