"""Command-line entrypoint."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from jetson_fw import udev as _udev
from jetson_fw.config.model import export_schema
from jetson_fw.config.parser import load_config
from jetson_fw.docker.image import ensure_image
from jetson_fw.docker.runner import DockerRunner
from jetson_fw.runner import BuildRunner
from jetson_fw.utils.logging import Logger, get_logger
from jetson_fw.utils.shell import ShellRunner

app = typer.Typer(help="Jetson firmware build automation")


def _logger(verbose: bool, quiet: bool) -> Logger:
    return get_logger(verbose=verbose, quiet=quiet)


@app.command()
def validate(
    config: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    schema_out: Annotated[Path | None, typer.Option("--schema-out")] = None,
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Parse and validate a config file."""

    logger = _logger(verbose, quiet)
    build_config = load_config(config)
    if schema_out is not None:
        export_schema(schema_out)
        logger.success(f"Wrote schema to {schema_out}")
    logger.success(f"Configuration is valid: {build_config.config_path}")


@app.command(name="image")
def image_cmd(
    config: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Build or pull the builder image."""

    logger = _logger(verbose, quiet)
    build_config = load_config(config)
    ensure_image(build_config, ShellRunner(logger), dry_run=dry_run)
    logger.success("Builder image ready.")


@app.command()
def build(
    config: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    stage: Annotated[str | None, typer.Option("--stage")] = None,
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force"),
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Run full or partial build stages inside Docker."""

    logger = _logger(verbose, quiet)
    build_config = load_config(config)
    shell = ShellRunner(logger)
    runner = BuildRunner(build_config, DockerRunner(build_config, shell), logger)
    runner.run_build(stage_name=stage, dry_run=dry_run, force=force)
    logger.success("Build stages completed.")


@app.command()
def flash(
    config: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    target: Annotated[str, typer.Option("--target")],
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force"),
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Flash a specific board target inside Docker."""

    logger = _logger(verbose, quiet)
    _udev.preflight_check(logger)
    build_config = load_config(config)
    shell = ShellRunner(logger)
    runner = BuildRunner(build_config, DockerRunner(build_config, shell), logger)
    runner.run_flash(build_config.get_target(target), dry_run=dry_run, force=force)
    logger.success(f"Flash workflow completed for {target}.")


@app.command(name="install-udev-rules")
def install_udev_rules_cmd(
    dest_dir: Annotated[Path, typer.Option("--dest-dir")] = Path("/etc/udev/rules.d"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Install udev rules for sudo-less Jetson USB flashing.

    Copies 99-tegra-devices.rules to DEST_DIR (default /etc/udev/rules.d) and
    reloads udev so the rule takes effect immediately.  Writing to the default
    destination requires root; run this command with sudo.

    After installation, add your user to the plugdev group if not already a
    member, then log out and back in:

        sudo usermod -aG plugdev $USER
    """
    logger = _logger(verbose, quiet)
    shell = ShellRunner(logger)
    src = _udev.rules_source()
    dest = dest_dir / _udev.RULES_FILENAME
    if dry_run:
        logger.info(f"[dry-run] Would copy {src} -> {dest}")
        logger.info("[dry-run] Would run: udevadm control --reload-rules")
        logger.info("[dry-run] Would run: udevadm trigger")
    else:
        _udev.install_rules(dest_dir, shell=shell, logger=logger)
    if not _udev.check_plugdev_membership():
        username = os.getenv("USER") or os.getenv("LOGNAME") or "<user>"
        logger.warning(
            f"User '{username}' is not in the 'plugdev' group. "
            f"Run 'sudo usermod -aG plugdev {username}' then log out and back in."
        )
    logger.success("udev rules installed.")


@app.command(name="all")
def all_cmd(
    config: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force"),
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Build image, run build stages, and flash all enabled targets."""

    logger = _logger(verbose, quiet)
    build_config = load_config(config)
    shell = ShellRunner(logger)
    ensure_image(build_config, shell, dry_run=dry_run)
    runner = BuildRunner(build_config, DockerRunner(build_config, shell), logger)
    runner.run_all(dry_run=dry_run, force=force)
    logger.success("Image, build, and flash workflows completed.")


if __name__ == "__main__":
    app()
