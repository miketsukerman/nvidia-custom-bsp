from __future__ import annotations

from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from rich.console import Console

from jetson_fw.config.model import BuildConfig
from jetson_fw.docker.image import ensure_image
from jetson_fw.docker.runner import DockerRunner
from jetson_fw.runner import BuildRunner
from jetson_fw.utils.logging import Logger
from jetson_fw.utils.shell import CommandResult, ShellRunner


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
                "privileged_for_flash": True,
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
            "workspace": {"root": str(tmp_path / "workspace")},
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


def captured_logger(*, verbose: bool, quiet: bool) -> tuple[Logger, Console]:
    console = Console(record=True, stderr=True, color_system=None, width=160)
    return Logger(verbose=verbose, quiet=quiet, console=console), console


def test_shell_runner_verbose_emits_context_and_redacts_sensitive_env(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    logger, console = captured_logger(verbose=True, quiet=False)
    shell = ShellRunner(logger)

    def fake_run(*args: object, **kwargs: object) -> CommandResult:
        del args, kwargs
        return CommandResult(returncode=0, stdout="ok\n", stderr="warn\n")

    monkeypatch.setattr("subprocess.run", fake_run)
    shell.run(
        ["echo", "hello"],
        cwd=tmp_path,
        env={"JOBS": "16", "API_TOKEN": "secret"},
    )

    output = console.export_text()
    assert "command.start" in output
    assert f"command.cwd={tmp_path}" in output
    assert "'API_TOKEN': '<redacted>'" in output
    assert "command.stdout.begin" in output
    assert "command.stderr.begin" in output
    assert "command.end dry_run=False exit_code=0" in output


def test_shell_runner_normal_mode_remains_concise(monkeypatch: MonkeyPatch) -> None:
    logger, console = captured_logger(verbose=False, quiet=False)
    shell = ShellRunner(logger)

    def fake_run(*args: object, **kwargs: object) -> CommandResult:
        del args, kwargs
        return CommandResult(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    shell.run(["echo", "hello"])

    output = console.export_text()
    assert "ok" in output
    assert "command.start" not in output
    assert "command.end" not in output


def test_shell_runner_quiet_mode_suppresses_non_error_output() -> None:
    logger, console = captured_logger(verbose=True, quiet=True)
    shell = ShellRunner(logger)
    shell.run(["echo", "hello"], dry_run=True)
    assert console.export_text() == ""


def test_docker_and_image_verbose_logging(tmp_path: Path) -> None:
    config = build_config(tmp_path)
    logger, console = captured_logger(verbose=True, quiet=False)
    shell = ShellRunner(logger)

    ensure_image(config, shell, dry_run=True)
    DockerRunner(config, shell).run("echo hi", dry_run=True, flash=True)

    output = console.export_text()
    assert "image.resolve image=builder:latest build_mode=build" in output
    assert "image.command docker build" in output
    assert "docker.run image=builder:latest flash=True dry_run=True" in output
    assert "docker.command docker run" in output


def test_build_runner_verbose_stage_logging(tmp_path: Path) -> None:
    config = build_config(tmp_path)
    logger, console = captured_logger(verbose=True, quiet=False)
    shell = ShellRunner(logger)
    docker = DockerRunner(config, shell)
    runner = BuildRunner(config, docker, logger)

    runner.run_build(stage_name="fetch_bsp", dry_run=True, force=False)

    output = console.export_text()
    assert "build.plan final_stage=fetch_bsp" in output
    assert "build.context workspace=" in output
    assert "stage.start name=fetch_bsp" in output
    assert "fetch_bsp.paths" in output
    assert "stage.end name=fetch_bsp" in output
