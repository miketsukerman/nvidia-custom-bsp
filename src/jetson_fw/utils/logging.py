"""Rich-backed console logging helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console
from rich.text import Text


@dataclass
class Logger:
    """Minimal structured logger."""

    verbose: bool = False
    quiet: bool = False
    console: Console = field(default_factory=lambda: Console(stderr=True))

    def _print(self, message: str, *, style: str | None = None) -> None:
        text = Text(message, no_wrap=True)
        if style is not None:
            text.stylize(style)
        self.console.print(text, highlight=False, soft_wrap=True)

    def info(self, message: str) -> None:
        if not self.quiet:
            self._print(message)

    def success(self, message: str) -> None:
        if not self.quiet:
            self._print(message, style="green")

    def warning(self, message: str) -> None:
        if not self.quiet:
            self._print(message, style="yellow")

    def error(self, message: str) -> None:
        self._print(message, style="red")

    def debug(self, message: str) -> None:
        if self.verbose and not self.quiet:
            self._print(message, style="dim")


def get_logger(verbose: bool = False, quiet: bool = False) -> Logger:
    """Create a console logger."""

    return Logger(verbose=verbose, quiet=quiet)
