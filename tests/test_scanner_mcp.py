"""Tests for MCP server scanner."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from aiq.models import ItemCategory
from aiq.scanner.mcp import McpScanner


def test_mcp_scanner_name() -> None:
    scanner = McpScanner()
    assert scanner.name == "mcp"


def test_mcp_scanner_reads_mcp_json(tmp_path: Path) -> None:
    mcp_config = {
        "mcpServers": {
            "github": {"command": "gh", "args": ["mcp"]},
            "qualio": {"command": "qualio-mcp", "args": ["--token", "SECRET"]},
        }
    }
    mcp_json = tmp_path / ".mcp.json"
    mcp_json.write_text(json.dumps(mcp_config))

    scanner = McpScanner(search_dirs=[tmp_path])
    result = scanner.scan()
    mcp_items = [i for i in result.items if i.category == ItemCategory.MCP_SERVER]
    assert len(mcp_items) >= 1
    # Should NOT contain the token value
    for item in mcp_items:
        assert "SECRET" not in item.content


@patch("aiq.scanner.mcp.subprocess.run")
def test_mcp_scanner_claude_mcp_list(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="github: gh mcp (user)\nqualio: qualio-mcp (user)\n",
    )
    scanner = McpScanner()
    items = scanner._scan_claude_mcp_list()
    assert len(items) >= 1


def test_mcp_scanner_no_config(tmp_path: Path) -> None:
    scanner = McpScanner(search_dirs=[tmp_path])
    result = scanner.scan()
    # Should not crash, just find nothing from file scan
    assert isinstance(result.items, list)
