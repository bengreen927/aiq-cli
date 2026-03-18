"""Tests for system-wide scanner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from aiq.models import ItemCategory
from aiq.scanner.system import SystemScanner


def test_system_scanner_name() -> None:
    scanner = SystemScanner()
    assert scanner.name == "system"


@patch("aiq.scanner.system.subprocess.run")
def test_system_scanner_brew_packages(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='brew "node"\nbrew "python3"\n',
    )
    scanner = SystemScanner()
    result = scanner._scan_brew()
    assert len(result) >= 1
    assert any("node" in i.content for i in result)


@patch("aiq.scanner.system.subprocess.run")
def test_system_scanner_npm_globals(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="/usr/lib\n├── firecrawl-cli@1.10.0\n└── typescript@5.4.0\n",
    )
    scanner = SystemScanner()
    result = scanner._scan_npm_globals()
    assert len(result) >= 1


@patch("aiq.scanner.system.subprocess.run")
def test_system_scanner_pip_packages(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="click 8.1.7\nrich 13.7.0\nhttpx 0.27.0\n",
    )
    scanner = SystemScanner()
    result = scanner._scan_pip()
    assert len(result) >= 1


@patch("aiq.scanner.system.subprocess.run")
def test_system_scanner_cron_jobs(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="0 8 * * * /usr/bin/python3 /home/user/scripts/report.py\n",
    )
    scanner = SystemScanner()
    result = scanner._scan_cron()
    assert len(result) >= 1
    assert result[0].category == ItemCategory.AUTOMATION


def test_system_scanner_shell_config() -> None:
    """Shell config scan should handle missing files gracefully."""
    scanner = SystemScanner(home_dir=Path("/nonexistent"))
    result = scanner._scan_shell_config()
    assert result == []


@patch("aiq.scanner.system.subprocess.run")
def test_system_scanner_command_failure(mock_run: MagicMock) -> None:
    mock_run.side_effect = FileNotFoundError("brew not found")
    scanner = SystemScanner()
    result = scanner.scan()
    # Should not crash; errors recorded
    assert isinstance(result.errors, list)
