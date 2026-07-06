"""Docker image build/pull helpers."""

from __future__ import annotations

from jetson_fw.config.model import BuildConfig
from jetson_fw.utils.shell import ShellRunner


def image_reference(config: BuildConfig) -> str:
    """Resolve the configured Docker image reference."""

    if config.docker.registry:
        return f"{config.docker.registry}/{config.docker.image}"
    return config.docker.image


def ensure_image(config: BuildConfig, shell: ShellRunner, *, dry_run: bool = False) -> None:
    """Build or pull the builder image."""

    image = image_reference(config)
    shell.logger.debug(
        f"image.resolve image={image} build_mode={'build' if config.docker.build else 'pull'}"
    )
    if config.docker.build:
        command = [
            "docker",
            "build",
            "-t",
            image,
            "-f",
            str(config.docker.dockerfile),
            str(config.repo_root),
        ]
    else:
        command = ["docker", "pull", image]
    shell.logger.debug(f"image.command {shell.format_command(command)}")
    shell.run(command, dry_run=dry_run)
