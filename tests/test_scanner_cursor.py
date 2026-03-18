"""Tests for Cursor scanner."""

from pathlib import Path

from aiq.models import ItemCategory
from aiq.scanner.cursor import CursorScanner

FIXTURES = Path(__file__).parent / "fixtures" / "cursor_project"


def test_cursor_scanner_name() -> None:
    scanner = CursorScanner(search_dirs=[FIXTURES])
    assert scanner.name == "cursor"


def test_cursor_finds_cursorrules() -> None:
    scanner = CursorScanner(search_dirs=[FIXTURES])
    result = scanner.scan()
    instruction_items = [i for i in result.items if i.category == ItemCategory.INSTRUCTION_FILE]
    assert len(instruction_items) >= 1
    assert any(".cursorrules" in i.source for i in instruction_items)


def test_cursor_finds_cursor_dir_rules() -> None:
    scanner = CursorScanner(search_dirs=[FIXTURES])
    result = scanner.scan()
    rule_items = [i for i in result.items if i.category == ItemCategory.RULE]
    assert len(rule_items) >= 1
    assert any("api" in i.source for i in rule_items)


def test_cursor_no_cursor_files() -> None:
    scanner = CursorScanner(search_dirs=[Path("/nonexistent")])
    result = scanner.scan()
    assert result.item_count == 0
