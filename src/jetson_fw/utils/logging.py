"""Rich-backed console logging helpers.

Logging contract:
- normal mode: info/success/warning/error are emitted, debug is suppressed.
- verbose mode: debug emits additional execution metadata.
- quiet mode: only errors are emitted.
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from dataclasses import dataclass, field

from rich.console import Console
from rich.status import Status
from rich.text import Text


@dataclass
class Logger:
    """Minimal structured logger honoring normal/verbose/quiet output modes."""

    verbose: bool = False
    quiet: bool = False
    console: Console = field(default_factory=lambda: Console(stderr=True))
    _active_status: Status | None = field(default=None, init=False, repr=False, compare=False)

    def _print(self, message: str, *, style: str | None = None) -> None:
        text = Text(message, no_wrap=True)
        if style is not None:
            text.stylize(style)
        self.console.print(text, highlight=False, soft_wrap=True)

    def info(self, message: str) -> None:
        if not self.quiet:
            self._print(message, style="cyan")

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
            self._print(message, style="dim blue")

    @contextlib.contextmanager
    def status(self, message: str) -> Generator[None, None, None]:
        """Context manager that shows an animated spinner in normal mode.

        - quiet mode: no-op.
        - verbose mode: emits the message as a debug line, no spinner.
        - normal mode: shows a Rich spinner; the spinner text can be updated
          via :meth:`update_status` from any call site within the context.
        """
        if self.quiet or self.verbose:
            if self.verbose:
                self.debug(message)
            yield
            return
        with self.console.status(message, spinner="dots") as active:
            self._active_status = active
            try:
                yield
            finally:
                self._active_status = None

    def update_status(self, message: str) -> None:
        """Update spinner text when active, otherwise emit as info."""
        if self._active_status is not None:
            self._active_status.update(message)
        else:
            self.info(message)


def get_logger(verbose: bool = False, quiet: bool = False) -> Logger:
    """Create a console logger."""

    return Logger(verbose=verbose, quiet=quiet)
