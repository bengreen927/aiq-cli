"""Scanner for MCP server configurations."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from aiq.models import ItemCategory, ScannedItem, ScanResult
from aiq.scanner.base import BaseScanner

# Flag names that precede secret values in args lists
_SECRET_FLAGS = re.compile(
    r"^-{1,2}(token|key|secret|password|credential|auth|api[_-]?key)",
    re.IGNORECASE,
)


class McpScanner(BaseScanner):
    """Scans MCP server configurations from .mcp.json files and claude mcp list."""

    def __init__(self, search_dirs: list[Path] | None = None) -> None:
        self._search_dirs = search_dirs or [Path.cwd(), Path.home()]

    @property
    def name(self) -> str:
        return "mcp"

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)

        # Scan .mcp.json files
        for search_dir in self._search_dirs:
            if not search_dir.is_dir():
                continue
            items = self._scan_mcp_json(search_dir)
            result.items.extend(items)

        # Scan claude mcp list output
        try:
            cli_items = self._scan_claude_mcp_list()
            result.items.extend(cli_items)
        except Exception as e:
            result.errors.append(f"claude mcp list: {e}")

        return result

    def _scan_mcp_json(self, directory: Path) -> list[ScannedItem]:
        """Parse .mcp.json files for server configurations."""
        items: list[ScannedItem] = []
        mcp_json = directory / ".mcp.json"
        if not mcp_json.is_file():
            return items

        try:
            data = json.loads(mcp_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return items

        servers: dict[str, Any] = data.get("mcpServers", {})
        for server_name, config in servers.items():
            # Build a sanitized description — strip secrets
            sanitized = self._sanitize_config(config)
            items.append(
                ScannedItem(
                    source=str(mcp_json),
                    category=ItemCategory.MCP_SERVER,
                    content=f"{server_name}: {json.dumps(sanitized)}",
                    metadata={
                        "server_name": server_name,
                        "has_command": "command" in config,
                    },
                )
            )

        return items

    def _sanitize_config(self, config: Any, _next_is_secret: bool = False) -> Any:
        """Remove secret-looking values from MCP config."""
        if isinstance(config, dict):
            sanitized: dict[str, Any] = {}
            for key, value in config.items():
                lower_key = key.lower()
                if any(
                    s in lower_key
                    for s in ("token", "key", "secret", "password", "credential", "auth")
                ):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize_config(value)
            return sanitized
        elif isinstance(config, list):
            result: list[Any] = []
            redact_next = False
            for item in config:
                if redact_next:
                    result.append("[REDACTED]")
                    redact_next = False
                elif isinstance(item, str) and _SECRET_FLAGS.match(item):
                    result.append(item)
                    redact_next = True
                else:
                    result.append(self._sanitize_config(item))
            return result
        elif isinstance(config, str):
            # Redact long opaque strings that look like tokens
            if len(config) > 20 and re.match(r"^[A-Za-z0-9_\-]+$", config):
                return "[REDACTED]"
            return config
        return config

    def _scan_claude_mcp_list(self) -> list[ScannedItem]:
        """Run `claude mcp list` and parse output."""
        proc = subprocess.run(
            ["claude", "mcp", "list"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            return []

        items: list[ScannedItem] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            items.append(
                ScannedItem(
                    source="claude_mcp_list",
                    category=ItemCategory.MCP_SERVER,
                    content=line,
                    metadata={"detection_method": "cli"},
                )
            )

        return items
