from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from jetson_fw.utils.logging import Logger
from jetson_fw.utils.shell import ShellError, ShellRunner


def make_logger(buffer: StringIO, *, verbose: bool = False, quiet: bool = False) -> Logger:
    return Logger(
        verbose=verbose,
        quiet=quiet,
        console=Console(file=buffer, color_system=None, force_terminal=False),
    )


def test_logger_warning_renders_bracketed_message_as_plain_text() -> None:
    buffer = StringIO()
    logger = make_logger(buffer)
    message = (
        "make[1]: Leaving directory '/workspace/build/out/kernel'\n"
        "[/workspace/build/Linux_for_Tegra/sources/kernel/kernel-5.10/arch/arm64/boot/dts/Makefile:96: dtbs]"
    )

    logger.warning(message)

    assert buffer.getvalue().strip() == message


def test_shell_runner_preserves_bracketed_stderr_output() -> None:
    buffer = StringIO()
    runner = ShellRunner(make_logger(buffer))
    command = [
        "python3",
        "-c",
        (
            "import sys; "
            'sys.stderr.write("[/workspace/build/Linux_for_Tegra/sources/kernel/kernel-5.10/arch/arm64/boot/dts/Makefile:96: dtbs]\\n"); '
            "raise SystemExit(2)"
        ),
    ]

    with pytest.raises(ShellError):
        runner.run(command)

    assert (
        "[/workspace/build/Linux_for_Tegra/sources/kernel/kernel-5.10/arch/arm64/boot/dts/Makefile:96: dtbs]"
        in buffer.getvalue()
    )


def test_status_context_manager_normal_mode() -> None:
    buffer = StringIO()
    logger = make_logger(buffer, verbose=False, quiet=False)

    assert logger._active_status is None
    entered: list[bool] = []
    with logger.status("doing work"):
        # spinner is active inside the context
        active = logger._active_status
        entered.append(active is not None)
        # update_status delegates to the live spinner (not to info)
        assert active is not None
        mock_update = MagicMock()
        active.update = mock_update
        logger._active_status = active
        logger.update_status("step 1")
        mock_update.assert_called_once_with("step 1")

    assert entered == [True]
    assert logger._active_status is None
    # no plain-text output was emitted by status() itself
    assert buffer.getvalue() == ""


def test_status_context_manager_quiet_mode() -> None:
    buffer = StringIO()
    logger = make_logger(buffer, verbose=False, quiet=True)

    with logger.status("doing work"):
        assert logger._active_status is None

    assert logger._active_status is None
    assert buffer.getvalue() == ""


def test_status_context_manager_verbose_mode() -> None:
    buffer = StringIO()
    logger = make_logger(buffer, verbose=True, quiet=False)

    with logger.status("doing work"):
        assert logger._active_status is None

    assert logger._active_status is None
    assert "doing work" in buffer.getvalue()


def test_update_status_without_active_status_falls_through_to_info() -> None:
    buffer = StringIO()
    logger = make_logger(buffer, verbose=False, quiet=False)

    assert logger._active_status is None
    logger.update_status("fallback message")

    assert "fallback message" in buffer.getvalue()
