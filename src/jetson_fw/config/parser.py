"""YAML config loader and validator."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .errors import ConfigLoadError, ConfigValidationError
from .model import BuildConfig


def load_config(config_path: str | Path) -> BuildConfig:
    """Load and validate a build config from YAML."""

    path = Path(config_path).expanduser().resolve()
    yaml = YAML(typ="safe")
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigLoadError(f"config file not found: {path}") from exc
    except YAMLError as exc:
        raise ConfigLoadError(f"failed to parse YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigLoadError(f"config file {path} must contain a YAML mapping at the top level")

    expanded = _expand_env(raw)
    normalized = _normalize_paths(expanded, path.parent)
    repo_root = _discover_repo_root(path.parent)

    try:
        config = BuildConfig.model_validate(normalized)
    except ValidationError as exc:
        details = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        raise ConfigValidationError(f"configuration validation failed for {path}", details) from exc

    config.attach_metadata(path, path.parent, repo_root)
    return config


def _expand_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, str):
        return os.path.expandvars(value)
    return value


def _normalize_paths(data: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    normalized = dict(data)

    docker = dict(normalized.get("docker", {}))
    if "dockerfile" in docker:
        docker["dockerfile"] = str(_to_absolute_host_path(docker["dockerfile"], base_dir))
    docker["volumes"] = [
        _normalize_volume(volume, base_dir) for volume in docker.get("volumes", [])
    ]
    docker["devices"] = [
        str(_to_absolute_host_path(device, base_dir)) for device in docker.get("devices", [])
    ]
    normalized["docker"] = docker

    kernel = dict(normalized.get("kernel", {}))
    kernel["config_fragments"] = [
        str(_to_absolute_host_path(item, base_dir)) for item in kernel.get("config_fragments", [])
    ]
    kernel["extra_dts"] = [
        str(_to_absolute_host_path(item, base_dir)) for item in kernel.get("extra_dts", [])
    ]
    normalized["kernel"] = kernel

    rootfs = dict(normalized.get("rootfs", {}))
    overlays: list[dict[str, Any]] = []
    for overlay in rootfs.get("overlays", []):
        overlay_copy = dict(overlay)
        overlay_copy["src"] = str(_to_absolute_host_path(overlay_copy["src"], base_dir))
        overlays.append(overlay_copy)
    rootfs["overlays"] = overlays
    normalized["rootfs"] = rootfs

    bsp = dict(normalized.get("bsp", {}))
    bsp_overlays: list[dict[str, Any]] = []
    for overlay in bsp.get("overlays", []):
        overlay_copy = dict(overlay)
        overlay_copy["src"] = str(_to_absolute_host_path(overlay_copy["src"], base_dir))
        bsp_overlays.append(overlay_copy)
    bsp["overlays"] = bsp_overlays
    normalized["bsp"] = bsp

    targets: list[dict[str, Any]] = []
    for target in normalized.get("targets", []):
        target_copy = dict(target)

        target_kernel = dict(target_copy.get("kernel", {}))
        target_kernel["config_fragments"] = [
            str(_to_absolute_host_path(item, base_dir))
            for item in target_kernel.get("config_fragments", [])
        ]
        target_kernel["extra_dts"] = [
            str(_to_absolute_host_path(item, base_dir))
            for item in target_kernel.get("extra_dts", [])
        ]
        if target_kernel:
            target_copy["kernel"] = target_kernel

        target_rootfs = dict(target_copy.get("rootfs", {}))
        target_rootfs_overlays: list[dict[str, Any]] = []
        for overlay in target_rootfs.get("overlays", []):
            overlay_copy = dict(overlay)
            overlay_copy["src"] = str(_to_absolute_host_path(overlay_copy["src"], base_dir))
            target_rootfs_overlays.append(overlay_copy)
        if target_rootfs_overlays:
            target_rootfs["overlays"] = target_rootfs_overlays
        if target_rootfs:
            target_copy["rootfs"] = target_rootfs

        target_bsp = dict(target_copy.get("bsp", {}))
        target_bsp_overlays: list[dict[str, Any]] = []
        for overlay in target_bsp.get("overlays", []):
            overlay_copy = dict(overlay)
            overlay_copy["src"] = str(_to_absolute_host_path(overlay_copy["src"], base_dir))
            target_bsp_overlays.append(overlay_copy)
        if target_bsp_overlays:
            target_bsp["overlays"] = target_bsp_overlays
        if target_bsp:
            target_copy["bsp"] = target_bsp

        targets.append(target_copy)
    normalized["targets"] = targets
    return normalized


def _normalize_volume(value: str, base_dir: Path) -> str:
    parts = value.split(":")
    if len(parts) not in {2, 3}:
        return value
    host = _to_absolute_host_path(parts[0], base_dir)
    return ":".join([str(host), *parts[1:]])


def _to_absolute_host_path(raw: str, base_dir: Path) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (base_dir / path).resolve()


def _discover_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    return start
