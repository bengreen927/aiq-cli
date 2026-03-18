"""Tests for Git config scanner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from aiq.models import ItemCategory
from aiq.scanner.git import GitScanner


def test_git_scanner_name() -> None:
    scanner = GitScanner()
    assert scanner.name == "git"


def test_git_scanner_reads_gitconfig(tmp_path: Path) -> None:
    gitconfig = tmp_path / ".gitconfig"
    gitconfig.write_text(
        "[user]\n\tname = Test User\n\temail = test@example.com\n"
        "[alias]\n\tco = checkout\n\tst = status\n"
    )

    scanner = GitScanner(home_dir=tmp_path)
    result = scanner.scan()
    config_items = [i for i in result.items if i.category == ItemCategory.GIT_CONFIG]
    assert len(config_items) >= 1
    # Should capture aliases but NOT user identity (PII)
    alias_items = [i for i in config_items if "alias" in i.content.lower()]
    assert len(alias_items) >= 1


@patch("aiq.scanner.git.subprocess.run")
def test_git_scanner_lfs(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="git-lfs/3.4.0\n",
    )
    scanner = GitScanner()
    items = scanner._scan_lfs()
    assert len(items) >= 1


def test_git_scanner_missing_gitconfig() -> None:
    scanner = GitScanner(home_dir=Path("/nonexistent"))
    result = scanner.scan()
    # Should not crash
    assert isinstance(result.items, list)
