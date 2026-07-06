"""Docker execution helpers for build stages."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from jetson_fw.config.model import BuildConfig
from jetson_fw.utils.shell import ShellRunner

from .image import image_reference


class DockerRunner:
    """Run commands inside the builder container."""

    repo_mount = Path("/workspace/repo")

    def __init__(self, config: BuildConfig, shell: ShellRunner):
        self.config = config
        self.shell = shell

    def container_path(self, host_path: Path) -> Path:
        resolved = host_path.resolve()
        repo_root = self.config.repo_root.resolve()
        try:
            relative = resolved.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError(f"path {resolved} is outside repository root {repo_root}") from exc
        return self.repo_mount / relative

    def build_run_command(
        self,
        inner_command: str,
        *,
        flash: bool = False,
        extra_env: Mapping[str, str] | None = None,
    ) -> list[str]:
        command = [
            "docker",
            "run",
            "--rm",
            "-w",
            str(self.repo_mount),
            "-v",
            f"{self.config.repo_root}:{self.repo_mount}",
        ]
        for volume in self.config.docker.volumes:
            command.extend(["-v", volume])
        environment = dict(self.config.docker.environment)
        if extra_env:
            environment.update(extra_env)
        for key, value in environment.items():
            command.extend(["-e", f"{key}={value}"])
        if flash:
            if self.config.docker.privileged_for_flash:
                command.append("--privileged")
            for device in self.config.docker.devices:
                device_str = str(device)
                if device_str.endswith("/usb") or device.is_dir():
                    command.extend(["-v", f"{device_str}:{device_str}"])
                else:
                    command.extend(["--device", f"{device_str}:{device_str}"])
        command.extend([image_reference(self.config), "bash", "-lc", inner_command])
        return command

    def run(
        self,
        inner_command: str,
        *,
        flash: bool = False,
        dry_run: bool = False,
        extra_env: Mapping[str, str] | None = None,
    ) -> None:
        self.shell.run(
            self.build_run_command(inner_command, flash=flash, extra_env=extra_env),
            dry_run=dry_run,
        )
