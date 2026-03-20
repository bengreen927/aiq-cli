"""Scanner for Claude Code configuration (~/.claude/)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from aiq.models import ItemCategory, ScannedItem, ScanResult
from aiq.scanner.base import BaseScanner


class ClaudeScanner(BaseScanner):
    """Scans Claude Code configuration files."""

    def __init__(self, home_dir: Optional[Path] = None) -> None:
        self._home_dir = home_dir or Path.home()

    @property
    def name(self) -> str:
        return "claude_code"

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)
        claude_dir = self._home_dir / ".claude"

        if not claude_dir.is_dir():
            result.errors.append(f"Claude directory not found: {claude_dir}")
            return result

        self._scan_claude_md(claude_dir, result)
        self._scan_settings(claude_dir, result)
        self._scan_skills(claude_dir, result)
        self._scan_rules(claude_dir, result)
        self._scan_memory(claude_dir, result)

        return result

    def _scan_claude_md(self, claude_dir: Path, result: ScanResult) -> None:
        """Scan CLAUDE.md (global instruction file)."""
        claude_md = claude_dir / "CLAUDE.md"
        if claude_md.is_file():
            content = claude_md.read_text(encoding="utf-8", errors="replace")
            result.items.append(
                ScannedItem(
                    source=str(claude_md),
                    category=ItemCategory.INSTRUCTION_FILE,
                    content=content,
                    metadata={
                        "line_count": len(content.splitlines()),
                        "scope": "global",
                    },
                )
            )

    def _scan_settings(self, claude_dir: Path, result: ScanResult) -> None:
        """Scan settings.json (permissions, preferences)."""
        settings = claude_dir / "settings.json"
        if settings.is_file():
            content = settings.read_text(encoding="utf-8", errors="replace")
            result.items.append(
                ScannedItem(
                    source=str(settings),
                    category=ItemCategory.CONFIG,
                    content=content,
                    metadata={"format": "json"},
                )
            )

    def _scan_skills(self, claude_dir: Path, result: ScanResult) -> None:
        """Scan skills/ directory — each subdirectory is a skill."""
        skills_dir = claude_dir / "skills"
        if not skills_dir.is_dir():
            return

        for skill_dir in sorted(skills_dir.iterdir()):
            # Check symlinks first — is_dir() follows symlinks, so a
            # symlinked directory would pass the is_dir() gate and the
            # is_symlink() check below would never be reached.
            if skill_dir.is_symlink():
                result.items.append(
                    ScannedItem(
                        source=str(skill_dir),
                        category=ItemCategory.SKILL,
                        content=f"Symlinked skill: {skill_dir.name}",
                        metadata={"symlink": True, "target": str(skill_dir.resolve())},
                    )
                )
                continue
            if not skill_dir.is_dir():
                continue

            # Read all markdown files in the skill directory
            skill_content_parts = []
            file_count = 0
            total_lines = 0
            for md_file in sorted(skill_dir.rglob("*.md")):
                file_count += 1
                text = md_file.read_text(encoding="utf-8", errors="replace")
                total_lines += len(text.splitlines())
                skill_content_parts.append(text)

            combined = "\n---\n".join(skill_content_parts)
            result.items.append(
                ScannedItem(
                    source=str(skill_dir),
                    category=ItemCategory.SKILL,
                    content=combined if combined else f"Empty skill directory: {skill_dir.name}",
                    metadata={
                        "skill_name": skill_dir.name,
                        "file_count": file_count,
                        "line_count": total_lines,
                    },
                )
            )

    def _scan_rules(self, claude_dir: Path, result: ScanResult) -> None:
        """Scan rules/ directory — each .md file is a rule."""
        rules_dir = claude_dir / "rules"
        if not rules_dir.is_dir():
            return

        for rule_file in sorted(rules_dir.glob("*.md")):
            content = rule_file.read_text(encoding="utf-8", errors="replace")
            result.items.append(
                ScannedItem(
                    source=str(rule_file),
                    category=ItemCategory.RULE,
                    content=content,
                    metadata={
                        "rule_name": rule_file.stem,
                        "line_count": len(content.splitlines()),
                    },
                )
            )

    def _scan_memory(self, claude_dir: Path, result: ScanResult) -> None:
        """Scan memory/ directory and project memory files."""
        # Global memory
        memory_dir = claude_dir / "memory"
        if memory_dir.is_dir():
            for mem_file in sorted(memory_dir.rglob("*.md")):
                content = mem_file.read_text(encoding="utf-8", errors="replace")
                result.items.append(
                    ScannedItem(
                        source=str(mem_file),
                        category=ItemCategory.MEMORY,
                        content=content,
                        metadata={"line_count": len(content.splitlines()), "scope": "global"},
                    )
                )

        # Project memory
        projects_dir = claude_dir / "projects"
        if projects_dir.is_dir():
            for mem_file in projects_dir.rglob("MEMORY.md"):
                content = mem_file.read_text(encoding="utf-8", errors="replace")
                result.items.append(
                    ScannedItem(
                        source=str(mem_file),
                        category=ItemCategory.MEMORY,
                        content=content,
                        metadata={
                            "line_count": len(content.splitlines()),
                            "scope": "project",
                        },
                    )
                )
