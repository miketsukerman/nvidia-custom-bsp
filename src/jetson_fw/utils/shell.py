"""Subprocess execution wrapper."""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .logging import Logger, get_logger


class ShellError(RuntimeError):
    """Raised when a shell command fails."""


@dataclass
class CommandResult:
    """Captured command execution result."""

    returncode: int
    stdout: str
    stderr: str


class ShellRunner:
    """Run subprocess commands with dry-run support."""

    def __init__(self, logger: Logger | None = None):
        self.logger = logger or get_logger()

    def format_command(self, command: Sequence[str]) -> str:
        return shlex.join(command)

    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        dry_run: bool = False,
        check: bool = True,
    ) -> CommandResult:
        rendered = self.format_command(command)
        self.logger.debug(f"$ {rendered}")
        if dry_run:
            self.logger.info(rendered)
            return CommandResult(returncode=0, stdout="", stderr="")

        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        completed = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd else None,
            env=run_env,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.stdout:
            self.logger.info(completed.stdout.rstrip())
        if completed.stderr:
            self.logger.warning(completed.stderr.rstrip())
        if check and completed.returncode != 0:
            raise ShellError(
                f"command failed with exit code {completed.returncode}: {rendered}\n{completed.stderr.strip()}"
            )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
