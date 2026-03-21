"""Tests for iteration scanner — skill refinement metrics."""

import subprocess
from pathlib import Path

from aiq.models import ItemCategory
from aiq.scanner.iteration import IterationScanner


def test_scanner_name() -> None:
    scanner = IterationScanner()
    assert scanner.name == "iteration"


def test_scan_with_git_history(tmp_path: Path) -> None:
    """Create a mini git repo with skill files and multiple commits, then verify metrics."""
    claude_dir = tmp_path / ".claude"
    skills_dir = claude_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=str(claude_dir), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(claude_dir), capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(claude_dir), capture_output=True, check=True,
    )

    # First commit — create a skill
    skill_file = skills_dir / "README.md"
    skill_file.write_text("# Test Skill\nLine 1\nLine 2\n")
    subprocess.run(["git", "add", "."], cwd=str(claude_dir), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "add test-skill"],
        cwd=str(claude_dir), capture_output=True, check=True,
    )

    # Second commit — modify it
    skill_file.write_text("# Test Skill\nLine 1\nLine 2\nLine 3\n")
    subprocess.run(["git", "add", "."], cwd=str(claude_dir), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "update test-skill"],
        cwd=str(claude_dir), capture_output=True, check=True,
    )

    # Third commit — add another skill then delete it
    skill2_dir = skills_dir.parent / "deleted-skill"
    skill2_dir.mkdir()
    (skill2_dir / "README.md").write_text("# Deleted\n")
    subprocess.run(["git", "add", "."], cwd=str(claude_dir), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "add deleted-skill"],
        cwd=str(claude_dir), capture_output=True, check=True,
    )

    # Fourth commit — remove it
    import shutil
    shutil.rmtree(str(skill2_dir))
    subprocess.run(["git", "add", "."], cwd=str(claude_dir), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "remove deleted-skill"],
        cwd=str(claude_dir), capture_output=True, check=True,
    )

    # Scan
    scanner = IterationScanner(claude_dir=claude_dir)
    result = scanner.scan()

    assert result.scanner_name == "iteration"
    assert result.item_count == 1
    assert len(result.errors) == 0

    item = result.items[0]
    assert item.category == ItemCategory.ITERATION_METRICS
    meta = item.metadata

    # File metrics
    assert meta["total_skills"] == 1  # only test-skill remains
    assert meta["avg_lines"] > 0
    assert meta["max_lines"] > 0

    # Git metrics
    assert meta["git_available"] is True
    assert meta["git_total_commits"] >= 2  # at least the 2 commits touching skills/
    assert meta["git_unique_files_modified"] >= 1
    assert meta["git_skills_deleted"] >= 1  # deleted-skill/README.md is gone
    assert meta["git_first_commit"] is not None
    assert meta["git_last_commit"] is not None


def test_scan_without_git(tmp_path: Path) -> None:
    """Skills dir without git repo — should produce timestamp-only metrics."""
    claude_dir = tmp_path / ".claude"
    skills_dir = claude_dir / "skills" / "my-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "README.md").write_text("# My Skill\nSome content\nMore content\n")

    scanner = IterationScanner(claude_dir=claude_dir)
    result = scanner.scan()

    assert result.scanner_name == "iteration"
    assert result.item_count == 1
    assert len(result.errors) == 0

    meta = result.items[0].metadata

    # File metrics should be present
    assert meta["total_skills"] == 1
    assert meta["avg_lines"] == 3
    assert meta["max_lines"] == 3
    assert meta["oldest_mtime"] is not None
    assert meta["newest_mtime"] is not None

    # Git metrics should indicate unavailable
    assert meta["git_available"] is False


def test_scan_missing_dir(tmp_path: Path) -> None:
    """Nonexistent directory should return empty results with an error."""
    scanner = IterationScanner(claude_dir=tmp_path / "nonexistent" / ".claude")
    result = scanner.scan()

    assert result.scanner_name == "iteration"
    assert result.item_count == 0
    assert len(result.errors) >= 1
