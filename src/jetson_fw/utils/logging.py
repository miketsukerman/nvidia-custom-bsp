"""Rich-backed console logging helpers.

Logging contract:
- normal mode: info/success/warning/error are emitted, debug is suppressed.
- verbose mode: debug emits additional execution metadata.
- quiet mode: only errors are emitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console


@dataclass
class Logger:
    """Minimal structured logger honoring normal/verbose/quiet output modes."""

    verbose: bool = False
    quiet: bool = False
    console: Console = field(default_factory=lambda: Console(stderr=True))

    def info(self, message: str) -> None:
        if not self.quiet:
            self.console.print(message)

    def success(self, message: str) -> None:
        if not self.quiet:
            self.console.print(f"[green]{message}[/green]")

    def warning(self, message: str) -> None:
        if not self.quiet:
            self.console.print(f"[yellow]{message}[/yellow]")

    def error(self, message: str) -> None:
        self.console.print(f"[red]{message}[/red]")

    def debug(self, message: str) -> None:
        if self.verbose and not self.quiet:
            self.console.print(f"[dim]{message}[/dim]")


def get_logger(verbose: bool = False, quiet: bool = False) -> Logger:
    """Create a console logger."""

    return Logger(verbose=verbose, quiet=quiet)
