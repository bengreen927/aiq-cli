"""Scanner for Git configuration (.gitconfig, remotes, LFS)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from aiq.models import ItemCategory, ScannedItem, ScanResult
from aiq.scanner.base import BaseScanner


class GitScanner(BaseScanner):
    """Scans Git configuration files and features."""

    def __init__(self, home_dir: Optional[Path] = None) -> None:
        self._home_dir = home_dir or Path.home()

    @property
    def name(self) -> str:
        return "git"

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)

        try:
            items = self._scan_gitconfig()
            result.items.extend(items)
        except Exception as e:
            result.errors.append(f"gitconfig: {e}")

        try:
            items = self._scan_lfs()
            result.items.extend(items)
        except Exception as e:
            result.errors.append(f"lfs: {e}")

        return result

    def _scan_gitconfig(self) -> list[ScannedItem]:
        """Parse .gitconfig, extracting aliases and tool config (not identity)."""
        items: list[ScannedItem] = []
        gitconfig = self._home_dir / ".gitconfig"
        if not gitconfig.is_file():
            return items

        content = gitconfig.read_text(encoding="utf-8", errors="replace")

        # Extract alias section
        aliases = self._extract_section(content, "alias")
        if aliases:
            items.append(
                ScannedItem(
                    source=str(gitconfig),
                    category=ItemCategory.GIT_CONFIG,
                    content=f"[alias]\n{aliases}",
                    metadata={"section": "alias"},
                )
            )

        # Extract tool-related sections (diff, merge, core settings)
        for section in ("diff", "merge", "core", "pull", "push", "lfs"):
            section_content = self._extract_section(content, section)
            if section_content:
                items.append(
                    ScannedItem(
                        source=str(gitconfig),
                        category=ItemCategory.GIT_CONFIG,
                        content=f"[{section}]\n{section_content}",
                        metadata={"section": section},
                    )
                )

        return items

    def _extract_section(self, content: str, section_name: str) -> str:
        """Extract a [section] and its subsections from gitconfig text."""
        lines = content.splitlines()
        in_section = False
        section_lines: list[str] = []
        section_lower = section_name.lower()

        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith(f"[{section_lower}]") or stripped.lower().startswith(f"[{section_lower} "):
                in_section = True
                continue
            elif stripped.startswith("[") and in_section:
                # Check if this is a subsection of the current section
                header_lower = stripped.lower()
                if header_lower.startswith(f"[{section_lower} ") or header_lower.startswith(f"[{section_lower}\""):
                    # Subsection like [core "autocrlf"] — keep collecting
                    continue
                # Different section entirely — stop
                break
            elif in_section and stripped:
                # Skip lines that look like they contain PII
                lower = stripped.lower()
                if any(k in lower for k in ("name =", "email =", "signingkey")):
                    continue
                section_lines.append(stripped)

        return "\n".join(section_lines)

    def _scan_lfs(self) -> list[ScannedItem]:
        """Check if Git LFS is installed."""
        proc = subprocess.run(
            ["git", "lfs", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return []

        return [
            ScannedItem(
                source="git_lfs",
                category=ItemCategory.TOOL,
                content=proc.stdout.strip(),
                metadata={"tool": "git-lfs"},
            )
        ]
