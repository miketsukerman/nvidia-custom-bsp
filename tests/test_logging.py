from __future__ import annotations

from io import StringIO

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
            "sys.stderr.write(\"[/workspace/build/Linux_for_Tegra/sources/kernel/kernel-5.10/arch/arm64/boot/dts/Makefile:96: dtbs]\\n\"); "
            "raise SystemExit(2)"
        ),
    ]

    with pytest.raises(ShellError):
        runner.run(command)

    assert (
        "[/workspace/build/Linux_for_Tegra/sources/kernel/kernel-5.10/arch/arm64/boot/dts/Makefile:96: dtbs]"
        in buffer.getvalue()
    )
