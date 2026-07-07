"""udev rule management for sudo-less Jetson USB flashing.

Installing the bundled 99-tegra-devices.rules file grants members of the
``plugdev`` group read/write access to NVIDIA Tegra recovery-mode USB devices
(VID 0x0955) without requiring sudo.  The remaining privilege need is for
loopback and mount operations (losetup/mount/umount) used by
``apply_binaries.sh`` while building system.img; those still require root.
"""

from __future__ import annotations

import grp
import os
import shutil
from pathlib import Path

from jetson_fw.utils.logging import Logger, get_logger
from jetson_fw.utils.shell import ShellRunner

RULES_FILENAME = "99-tegra-devices.rules"
SYSTEM_RULES_DIR = Path("/etc/udev/rules.d")


def rules_source() -> Path:
    """Return the path to the bundled udev rules file.

    The file lives in ``src/jetson_fw/data/`` inside the installed package.
    """
    return Path(__file__).parent / "data" / RULES_FILENAME


def install_rules(
    dest_dir: Path = SYSTEM_RULES_DIR,
    *,
    shell: ShellRunner | None = None,
    logger: Logger | None = None,
) -> Path:
    """Copy the Tegra udev rules file to *dest_dir* and reload udev.

    Args:
        dest_dir: Directory to install the rules file into (default
            ``/etc/udev/rules.d``).  Writing here typically requires root.
        shell: :class:`~jetson_fw.utils.shell.ShellRunner` used to invoke
            ``udevadm``.  A default logger-backed runner is created if omitted.
        logger: Logger for progress messages.  A default silent logger is used
            if omitted.

    Returns:
        The absolute path of the installed rules file.
    """
    log = logger or get_logger()
    _shell = shell or ShellRunner(log)
    src = rules_source()
    dest = dest_dir / RULES_FILENAME
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dest))
    log.success(f"Installed {src.name} -> {dest}")
    reload_rules(_shell)
    return dest


def reload_rules(shell: ShellRunner) -> None:
    """Ask udevd to reload rule files and re-trigger device events."""
    shell.run(["udevadm", "control", "--reload-rules"])
    shell.run(["udevadm", "trigger"])


def check_plugdev_membership() -> bool:
    """Return ``True`` if the current user is a member of the *plugdev* group.

    The check inspects the system group database; it does not verify effective
    supplemental groups in the running process (which requires a log-out/log-in
    cycle after ``usermod``).
    """
    username = os.getenv("USER") or os.getenv("LOGNAME") or ""
    if not username:
        return False
    try:
        group = grp.getgrnam("plugdev")
    except KeyError:
        return False
    return username in group.gr_mem


def preflight_check(logger: Logger) -> None:
    """Emit warnings when the udev rule or plugdev membership is missing.

    This is a non-fatal advisory check intended to be called before the flash
    workflow so that users have a clear path to enabling sudo-less flashing.

    Remaining privilege requirement:
        Even with the udev rule in place, ``apply_binaries.sh`` uses
        ``losetup`` and ``mount`` during the ``assemble_rootfs`` stage and
        therefore still needs root (or appropriate Linux capabilities) when
        building ``system.img``.  The udev rule only eliminates the need for
        root during the USB flashing step itself.
    """
    rules_installed = (SYSTEM_RULES_DIR / RULES_FILENAME).exists()
    if not rules_installed:
        logger.warning(
            f"udev rule not found at {SYSTEM_RULES_DIR / RULES_FILENAME}. "
            "Run 'sudo jetson-fw install-udev-rules' to enable sudo-less USB access."
        )
    if not check_plugdev_membership():
        username = os.getenv("USER") or os.getenv("LOGNAME") or "<user>"
        logger.warning(
            f"User '{username}' is not in the 'plugdev' group. "
            f"Run 'sudo usermod -aG plugdev {username}' then log out and back in."
        )
