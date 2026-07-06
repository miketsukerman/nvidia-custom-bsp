from __future__ import annotations

from pathlib import Path

import pytest

from jetson_fw.config.errors import ConfigLoadError, ConfigValidationError
from jetson_fw.config.parser import load_config


def test_load_config_expands_relative_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    (repo_root / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0.0.0"\n', encoding="utf-8")
    config_dir = repo_root / "configs"
    fixture_dir = repo_root / "fixtures"
    (fixture_dir / "configs").mkdir(parents=True)
    (fixture_dir / "dts").mkdir(parents=True)
    (fixture_dir / "overlays" / "etc").mkdir(parents=True)
    (repo_root / "docker").mkdir()
    (repo_root / "docker" / "Dockerfile").write_text("FROM ubuntu:20.04\n", encoding="utf-8")
    (fixture_dir / "configs" / "enable-can.config").write_text("", encoding="utf-8")
    (fixture_dir / "dts" / "board.dts").write_text("", encoding="utf-8")
    (fixture_dir / "overlays" / "etc" / "motd").write_text("hi\n", encoding="utf-8")
    config_dir.mkdir()
    monkeypatch.setenv("JOBS", "12")
    config_path = config_dir / "sample.yaml"
    config_path.write_text(
        """version: 1

docker:
  image: builder:latest
  dockerfile: ../docker/Dockerfile
  build: true
  registry: ""
  privileged_for_flash: false
  devices:
    - /dev/bus/usb
  volumes:
    - ../build:/workspace/build
  environment:
    JOBS: "${JOBS}"
l4t:
  release: 35.2.1
  bsp_url: https://example.com/bsp.tbz2
  bsp_sha256: "1111111111111111111111111111111111111111111111111111111111111111"
  sample_rootfs_url: https://example.com/rootfs.tbz2
  sample_rootfs_sha256: "2222222222222222222222222222222222222222222222222222222222222222"
toolchain:
  url: https://example.com/toolchain.tar.xz
  sha256: "3333333333333333333333333333333333333333333333333333333333333333"
workspace:
  root: /workspace/build
kernel:
  config_fragments:
    - ../fixtures/configs/enable-can.config
  extra_dts:
    - ../fixtures/dts/board.dts
rootfs:
  overlays:
    - src: ../fixtures/overlays/etc
      dest: /etc
targets:
  - name: xavier-nx
    module: p3668
    flash_config: jetson-xavier-nx-devkit-emmc
    root_device: mmcblk0p1
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_config(config_path)
    assert config.docker.environment["JOBS"] == "12"
    assert config.docker.dockerfile.is_absolute()
    assert config.kernel.config_fragments[0].is_absolute()
    assert config.rootfs.overlays[0].src.is_absolute()
    assert config.repo_root == repo_root


def test_load_config_rejects_invalid_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "broken.yaml"
    config_path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ConfigLoadError):
        load_config(config_path)


def test_load_config_reports_validation_errors(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.yaml"
    config_path.write_text(
        "version: 1\n\ndocker:\n  image: builder\nl4t:\n  release: 35.2.1\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigValidationError):
        load_config(config_path)
