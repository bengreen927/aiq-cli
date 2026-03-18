"""Scanner for Cursor IDE configuration (.cursorrules, .cursor/)."""

from __future__ import annotations

from pathlib import Path

from aiq.models import ItemCategory, ScannedItem, ScanResult
from aiq.scanner.base import BaseScanner


class CursorScanner(BaseScanner):
    """Scans Cursor IDE configuration files."""

    def __init__(self, search_dirs: list[Path] | None = None) -> None:
        self._search_dirs = search_dirs or [Path.cwd(), Path.home()]

    @property
    def name(self) -> str:
        return "cursor"

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)

        for search_dir in self._search_dirs:
            if not search_dir.is_dir():
                continue
            self._scan_cursorrules(search_dir, result)
            self._scan_cursor_dir(search_dir, result)

        return result

    def _scan_cursorrules(self, directory: Path, result: ScanResult) -> None:
        """Scan .cursorrules file."""
        cursorrules = directory / ".cursorrules"
        if cursorrules.is_file():
            content = cursorrules.read_text(encoding="utf-8", errors="replace")
            result.items.append(
                ScannedItem(
                    source=str(cursorrules),
                    category=ItemCategory.INSTRUCTION_FILE,
                    content=content,
                    metadata={
                        "line_count": len(content.splitlines()),
                        "platform": "cursor",
                    },
                )
            )

    def _scan_cursor_dir(self, directory: Path, result: ScanResult) -> None:
        """Scan .cursor/ directory for rules and config."""
        cursor_dir = directory / ".cursor"
        if not cursor_dir.is_dir():
            return

        # Scan rules subdirectory
        rules_dir = cursor_dir / "rules"
        if rules_dir.is_dir():
            for rule_file in sorted(rules_dir.rglob("*.md")):
                content = rule_file.read_text(encoding="utf-8", errors="replace")
                result.items.append(
                    ScannedItem(
                        source=str(rule_file),
                        category=ItemCategory.RULE,
                        content=content,
                        metadata={
                            "rule_name": rule_file.stem,
                            "line_count": len(content.splitlines()),
                            "platform": "cursor",
                        },
                    )
                )

        # Scan any JSON config files
        for config_file in sorted(cursor_dir.glob("*.json")):
            content = config_file.read_text(encoding="utf-8", errors="replace")
            result.items.append(
                ScannedItem(
                    source=str(config_file),
                    category=ItemCategory.CONFIG,
                    content=content,
                    metadata={"format": "json", "platform": "cursor"},
                )
            )
