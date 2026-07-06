"""Subprocess execution wrapper."""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

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

    def _safe_env_overrides(self, env: Mapping[str, str] | None) -> Mapping[str, str]:
        if not env:
            return {}
        safe: dict[str, str] = {}
        for key, value in env.items():
            normalized = key.lower()
            if any(token in normalized for token in ("token", "secret", "password", "key")):
                safe[key] = "<redacted>"
            else:
                safe[key] = value
        return safe

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
        safe_env = self._safe_env_overrides(env)
        cwd_text = str(cwd) if cwd else os.getcwd()
        self.logger.debug("command.start")
        self.logger.debug(f"command.cwd={cwd_text}")
        if safe_env:
            self.logger.debug(f"command.env_overrides={safe_env}")
        self.logger.debug(f"$ {rendered}")
        if dry_run:
            self.logger.info(rendered)
            self.logger.debug("command.end dry_run=True exit_code=0 duration_seconds=0.000")
            return CommandResult(returncode=0, stdout="", stderr="")

        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        started = time.perf_counter()
        completed = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd else None,
            env=run_env,
            check=False,
            capture_output=True,
            text=True,
        )
        duration = time.perf_counter() - started
        if completed.stdout and self.logger.verbose and not self.logger.quiet:
            self.logger.debug("command.stdout.begin")
        if completed.stdout:
            self.logger.info(completed.stdout.rstrip())
        if completed.stdout and self.logger.verbose and not self.logger.quiet:
            self.logger.debug("command.stdout.end")
        if completed.stderr and self.logger.verbose and not self.logger.quiet:
            self.logger.debug("command.stderr.begin")
        if completed.stderr:
            self.logger.warning(completed.stderr.rstrip())
        if completed.stderr and self.logger.verbose and not self.logger.quiet:
            self.logger.debug("command.stderr.end")
        self.logger.debug(
            f"command.end dry_run=False exit_code={completed.returncode} "
            f"duration_seconds={duration:.3f}"
        )
        if check and completed.returncode != 0:
            raise ShellError(
                f"command failed with exit code {completed.returncode}: {rendered}\n{completed.stderr.strip()}"
            )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
