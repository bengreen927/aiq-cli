"""Tests for Claude Code scanner."""

from pathlib import Path

from aiq.models import ItemCategory
from aiq.scanner.claude import ClaudeScanner

FIXTURES = Path(__file__).parent / "fixtures" / "claude_home"


def test_claude_scanner_name() -> None:
    scanner = ClaudeScanner(home_dir=FIXTURES)
    assert scanner.name == "claude_code"


def test_claude_scanner_finds_claude_md() -> None:
    scanner = ClaudeScanner(home_dir=FIXTURES)
    result = scanner.scan()
    md_items = [i for i in result.items if i.category == ItemCategory.INSTRUCTION_FILE]
    assert len(md_items) >= 1
    sources = [i.source for i in md_items]
    assert any("CLAUDE.md" in s for s in sources)


def test_claude_scanner_finds_skills() -> None:
    scanner = ClaudeScanner(home_dir=FIXTURES)
    result = scanner.scan()
    skill_items = [i for i in result.items if i.category == ItemCategory.SKILL]
    assert len(skill_items) >= 1
    assert any("test-skill" in i.source for i in skill_items)


def test_claude_scanner_finds_rules() -> None:
    scanner = ClaudeScanner(home_dir=FIXTURES)
    result = scanner.scan()
    rule_items = [i for i in result.items if i.category == ItemCategory.RULE]
    assert len(rule_items) >= 1
    assert any("code-quality" in i.source for i in rule_items)


def test_claude_scanner_finds_settings() -> None:
    scanner = ClaudeScanner(home_dir=FIXTURES)
    result = scanner.scan()
    config_items = [i for i in result.items if i.category == ItemCategory.CONFIG]
    assert len(config_items) >= 1
    assert any("settings.json" in i.source for i in config_items)


def test_claude_scanner_finds_memory() -> None:
    scanner = ClaudeScanner(home_dir=FIXTURES)
    result = scanner.scan()
    mem_items = [i for i in result.items if i.category == ItemCategory.MEMORY]
    assert len(mem_items) >= 1


def test_claude_scanner_missing_dir() -> None:
    scanner = ClaudeScanner(home_dir=Path("/nonexistent"))
    result = scanner.scan()
    assert result.item_count == 0
    assert len(result.errors) >= 1
