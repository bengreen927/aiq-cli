"""Tests for shared data models."""

from aiq.models import ItemCategory, ScannedItem, ScanResult


def test_scan_result_empty() -> None:
    result = ScanResult(scanner_name="test")
    assert result.scanner_name == "test"
    assert result.items == []
    assert result.item_count == 0


def test_scan_result_with_items() -> None:
    item = ScannedItem(
        source="~/.claude/CLAUDE.md",
        category=ItemCategory.INSTRUCTION_FILE,
        content="Always use python3",
        metadata={"line_count": 50},
    )
    result = ScanResult(scanner_name="claude", items=[item])
    assert result.item_count == 1
    assert result.items[0].source == "~/.claude/CLAUDE.md"


def test_scanned_item_category_values() -> None:
    assert ItemCategory.SKILL == "skill"
    assert ItemCategory.RULE == "rule"
    assert ItemCategory.INSTRUCTION_FILE == "instruction_file"
    assert ItemCategory.MCP_SERVER == "mcp_server"
    assert ItemCategory.TOOL == "tool"
    assert ItemCategory.MEMORY == "memory"
    assert ItemCategory.CONFIG == "config"
    assert ItemCategory.AUTOMATION == "automation"
