"""Command-line entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

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
    build_config = load_config(config)
    shell = ShellRunner(logger)
    runner = BuildRunner(build_config, DockerRunner(build_config, shell), logger)
    runner.run_flash(build_config.get_target(target), dry_run=dry_run, force=force)
    logger.success(f"Flash workflow completed for {target}.")


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
