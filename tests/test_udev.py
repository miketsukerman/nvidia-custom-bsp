"""Tests for jetson_fw.udev module."""

from __future__ import annotations

import grp
from pathlib import Path
from unittest.mock import patch

import pytest

import jetson_fw.udev as udev_mod
from jetson_fw.utils.logging import get_logger
from jetson_fw.utils.shell import ShellRunner

# ---------------------------------------------------------------------------
# rules_source
# ---------------------------------------------------------------------------


def test_rules_source_returns_existing_file() -> None:
    src = udev_mod.rules_source()
    assert src.exists(), f"Bundled rules file not found at {src}"
    assert src.name == udev_mod.RULES_FILENAME


def test_rules_source_contains_tegra_vendor_rule() -> None:
    src = udev_mod.rules_source()
    content = src.read_text(encoding="utf-8")
    assert 'ATTR{idVendor}=="0955"' in content
    assert 'GROUP="plugdev"' in content


# ---------------------------------------------------------------------------
# install_rules
# ---------------------------------------------------------------------------


def test_install_rules_copies_file_and_reloads(tmp_path: Path) -> None:
    dest_dir = tmp_path / "udev" / "rules.d"
    logger = get_logger()
    shell = ShellRunner(logger)

    with patch.object(shell, "run") as mock_run:
        installed = udev_mod.install_rules(dest_dir, shell=shell, logger=logger)

    assert installed == dest_dir / udev_mod.RULES_FILENAME
    assert installed.exists()
    content = installed.read_text(encoding="utf-8")
    assert 'ATTR{idVendor}=="0955"' in content

    # Should have called reload-rules and trigger
    calls = [list(call.args[0]) for call in mock_run.call_args_list]
    assert ["udevadm", "control", "--reload-rules"] in calls
    assert ["udevadm", "trigger"] in calls


def test_install_rules_creates_dest_dir(tmp_path: Path) -> None:
    dest_dir = tmp_path / "deep" / "nested" / "rules.d"
    assert not dest_dir.exists()
    logger = get_logger()
    shell = ShellRunner(logger)

    with patch.object(shell, "run"):
        udev_mod.install_rules(dest_dir, shell=shell, logger=logger)

    assert dest_dir.is_dir()


# ---------------------------------------------------------------------------
# reload_rules
# ---------------------------------------------------------------------------


def test_reload_rules_invokes_udevadm() -> None:
    logger = get_logger()
    shell = ShellRunner(logger)

    with patch.object(shell, "run") as mock_run:
        udev_mod.reload_rules(shell)

    assert mock_run.call_count == 2
    first_call_args = list(mock_run.call_args_list[0].args[0])
    second_call_args = list(mock_run.call_args_list[1].args[0])
    assert first_call_args == ["udevadm", "control", "--reload-rules"]
    assert second_call_args == ["udevadm", "trigger"]


# ---------------------------------------------------------------------------
# check_plugdev_membership
# ---------------------------------------------------------------------------


def test_check_plugdev_membership_true_when_member(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER", "alice")
    fake_group = grp.struct_group(("plugdev", "x", 1000, ["alice", "bob"]))
    with patch("grp.getgrnam", return_value=fake_group):
        assert udev_mod.check_plugdev_membership() is True


def test_check_plugdev_membership_false_when_not_member(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER", "carol")
    fake_group = grp.struct_group(("plugdev", "x", 1000, ["alice", "bob"]))
    with patch("grp.getgrnam", return_value=fake_group):
        assert udev_mod.check_plugdev_membership() is False


def test_check_plugdev_membership_false_when_group_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USER", "alice")
    with patch("grp.getgrnam", side_effect=KeyError("plugdev")):
        assert udev_mod.check_plugdev_membership() is False


def test_check_plugdev_membership_false_when_no_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("USER", raising=False)
    monkeypatch.delenv("LOGNAME", raising=False)
    assert udev_mod.check_plugdev_membership() is False


def test_check_plugdev_membership_uses_logname_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("USER", raising=False)
    monkeypatch.setenv("LOGNAME", "dave")
    fake_group = grp.struct_group(("plugdev", "x", 1000, ["dave"]))
    with patch("grp.getgrnam", return_value=fake_group):
        assert udev_mod.check_plugdev_membership() is True


# ---------------------------------------------------------------------------
# preflight_check
# ---------------------------------------------------------------------------


def test_preflight_check_warns_when_rules_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(udev_mod, "SYSTEM_RULES_DIR", tmp_path / "nonexistent")
    logger = get_logger()
    warnings: list[str] = []
    monkeypatch.setattr(logger, "warning", lambda msg: warnings.append(msg))

    with patch.object(udev_mod, "check_plugdev_membership", return_value=True):
        udev_mod.preflight_check(logger)

    assert any("install-udev-rules" in w for w in warnings)


def test_preflight_check_warns_when_not_in_plugdev(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Rule file exists
    rules_dir = tmp_path / "rules.d"
    rules_dir.mkdir()
    (rules_dir / udev_mod.RULES_FILENAME).touch()
    monkeypatch.setattr(udev_mod, "SYSTEM_RULES_DIR", rules_dir)
    monkeypatch.setenv("USER", "testuser")

    logger = get_logger()
    warnings: list[str] = []
    monkeypatch.setattr(logger, "warning", lambda msg: warnings.append(msg))

    with patch.object(udev_mod, "check_plugdev_membership", return_value=False):
        udev_mod.preflight_check(logger)

    assert any("plugdev" in w for w in warnings)
    assert any("usermod" in w for w in warnings)


def test_preflight_check_no_warnings_when_all_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rules_dir = tmp_path / "rules.d"
    rules_dir.mkdir()
    (rules_dir / udev_mod.RULES_FILENAME).touch()
    monkeypatch.setattr(udev_mod, "SYSTEM_RULES_DIR", rules_dir)

    logger = get_logger()
    warnings: list[str] = []
    monkeypatch.setattr(logger, "warning", lambda msg: warnings.append(msg))

    with patch.object(udev_mod, "check_plugdev_membership", return_value=True):
        udev_mod.preflight_check(logger)

    assert warnings == []
