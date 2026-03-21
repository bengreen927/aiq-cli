"""Scanner for skill iteration metrics — measures how actively a user refines their AI skills."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiq.models import ItemCategory, ScannedItem, ScanResult
from aiq.scanner.base import BaseScanner


class IterationScanner(BaseScanner):
    """Measures skill refinement activity by analyzing file metadata and git history.

    Produces a single ScannedItem with category ITERATION_METRICS containing:
    - Skill counts and size statistics
    - File modification timestamps and age spread
    - Git commit history for skills/ (if available)
    - Changelog/tracking file presence
    """

    def __init__(self, claude_dir: Optional[Path] = None) -> None:
        self._claude_dir = claude_dir or (Path.home() / ".claude")

    @property
    def name(self) -> str:
        return "iteration"

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)
        skills_dir = self._claude_dir / "skills"

        if not skills_dir.is_dir():
            result.errors.append(f"Skills directory not found: {skills_dir}")
            return result

        metrics: Dict[str, Any] = {}

        try:
            self._collect_file_metrics(skills_dir, metrics)
        except Exception as e:
            result.errors.append(f"file_metrics: {e}")

        try:
            self._collect_git_metrics(metrics)
        except Exception as e:
            result.errors.append(f"git_metrics: {e}")

        try:
            self._collect_tracking_files(metrics)
        except Exception as e:
            result.errors.append(f"tracking_files: {e}")

        summary_parts: List[str] = []
        summary_parts.append(f"{metrics.get('total_skills', 0)} skills")
        if metrics.get("git_total_commits"):
            summary_parts.append(f"{metrics['git_total_commits']} commits")
        if metrics.get("git_skills_deleted"):
            summary_parts.append(f"{metrics['git_skills_deleted']} deleted/consolidated")

        result.items.append(
            ScannedItem(
                source=str(skills_dir),
                category=ItemCategory.ITERATION_METRICS,
                content="; ".join(summary_parts),
                metadata=metrics,
            )
        )

        return result

    # ------------------------------------------------------------------
    # File-based metrics
    # ------------------------------------------------------------------

    def _collect_file_metrics(self, skills_dir: Path, metrics: Dict[str, Any]) -> None:
        """Count skills, measure file sizes, and check modification timestamps."""
        skill_dirs: List[Path] = [
            p for p in sorted(skills_dir.iterdir())
            if p.is_dir() or p.is_symlink()
        ]
        metrics["total_skills"] = len(skill_dirs)

        if not skill_dirs:
            metrics["avg_lines"] = 0
            metrics["max_lines"] = 0
            metrics["oldest_mtime"] = None
            metrics["newest_mtime"] = None
            metrics["age_spread_days"] = 0
            return

        line_counts: List[int] = []
        mtimes: List[float] = []

        for skill_path in skill_dirs:
            # Symlinks — just record mtime of the link itself
            if skill_path.is_symlink():
                try:
                    mtimes.append(skill_path.lstat().st_mtime)
                except OSError:
                    pass
                line_counts.append(0)
                continue

            # Regular skill directory — sum lines across markdown files
            skill_lines = 0
            for md_file in skill_path.rglob("*.md"):
                try:
                    text = md_file.read_text(encoding="utf-8", errors="replace")
                    skill_lines += len(text.splitlines())
                    mtimes.append(md_file.stat().st_mtime)
                except OSError:
                    pass
            line_counts.append(skill_lines)

        metrics["avg_lines"] = round(sum(line_counts) / len(line_counts), 1) if line_counts else 0
        metrics["max_lines"] = max(line_counts) if line_counts else 0

        if mtimes:
            oldest = min(mtimes)
            newest = max(mtimes)
            metrics["oldest_mtime"] = datetime.fromtimestamp(oldest, tz=timezone.utc).isoformat()
            metrics["newest_mtime"] = datetime.fromtimestamp(newest, tz=timezone.utc).isoformat()
            metrics["age_spread_days"] = round((newest - oldest) / 86400, 1)
        else:
            metrics["oldest_mtime"] = None
            metrics["newest_mtime"] = None
            metrics["age_spread_days"] = 0

    # ------------------------------------------------------------------
    # Git-based metrics
    # ------------------------------------------------------------------

    def _collect_git_metrics(self, metrics: Dict[str, Any]) -> None:
        """If ~/.claude/ is a git repo, extract commit history for skills/."""
        if not self._is_git_repo():
            metrics["git_available"] = False
            return

        metrics["git_available"] = True

        # Total commits touching skills/
        total_commits = self._git_count_commits("skills/")
        metrics["git_total_commits"] = total_commits

        # Unique skill files ever modified
        unique_files = self._git_unique_files("skills/")
        metrics["git_unique_files_modified"] = len(unique_files)

        # Skills deleted/consolidated (files that existed in history but not on disk)
        current_files = set()
        skills_dir = self._claude_dir / "skills"
        if skills_dir.is_dir():
            for p in skills_dir.rglob("*"):
                if p.is_file():
                    try:
                        current_files.add(str(p.relative_to(self._claude_dir)))
                    except ValueError:
                        pass

        deleted = [f for f in unique_files if f not in current_files]
        metrics["git_skills_deleted"] = len(deleted)

        # Date range of skill commits
        date_range = self._git_date_range("skills/")
        metrics["git_first_commit"] = date_range[0]
        metrics["git_last_commit"] = date_range[1]

    def _is_git_repo(self) -> bool:
        """Check if claude_dir is inside a git repository."""
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self._claude_dir),
            )
            return proc.returncode == 0 and proc.stdout.strip() == "true"
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    def _git_count_commits(self, path: str) -> int:
        """Count commits that touched the given path."""
        try:
            proc = subprocess.run(
                ["git", "log", "--oneline", "--follow", "--", path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self._claude_dir),
            )
            if proc.returncode != 0:
                return 0
            lines = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
            return len(lines)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return 0

    def _git_unique_files(self, path: str) -> List[str]:
        """Return unique file paths ever modified under the given path."""
        try:
            proc = subprocess.run(
                ["git", "log", "--all", "--pretty=format:", "--name-only", "--diff-filter=ACDMR", "--", path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self._claude_dir),
            )
            if proc.returncode != 0:
                return []
            files = set()
            for line in proc.stdout.strip().splitlines():
                stripped = line.strip()
                if stripped:
                    files.add(stripped)
            return sorted(files)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return []

    def _git_date_range(self, path: str) -> tuple:
        """Return (first_commit_date, last_commit_date) for commits touching path."""
        try:
            # Oldest commit
            proc_oldest = subprocess.run(
                ["git", "log", "--reverse", "--format=%aI", "--", path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self._claude_dir),
            )
            # Newest commit
            proc_newest = subprocess.run(
                ["git", "log", "-1", "--format=%aI", "--", path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self._claude_dir),
            )

            first = None
            last = None

            if proc_oldest.returncode == 0:
                lines = proc_oldest.stdout.strip().splitlines()
                if lines:
                    first = lines[0].strip()

            if proc_newest.returncode == 0:
                line = proc_newest.stdout.strip()
                if line:
                    last = line.splitlines()[0].strip()

            return (first, last)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return (None, None)

    # ------------------------------------------------------------------
    # Tracking / changelog files
    # ------------------------------------------------------------------

    def _collect_tracking_files(self, metrics: Dict[str, Any]) -> None:
        """Check for changelog, tracking, or memory files that indicate iteration."""
        tracking_indicators: List[str] = []

        # Check memory directory for changelog-like files
        memory_dir = self._claude_dir / "memory"
        if memory_dir.is_dir():
            for mem_file in memory_dir.rglob("*.md"):
                try:
                    content = mem_file.read_text(encoding="utf-8", errors="replace")
                    lower = content.lower()
                    if any(kw in lower for kw in ("changelog", "changes log", "skills", "installed skills")):
                        tracking_indicators.append(str(mem_file.name))
                except OSError:
                    pass

        # Check for project memory files
        projects_dir = self._claude_dir / "projects"
        if projects_dir.is_dir():
            for mem_file in projects_dir.rglob("MEMORY.md"):
                try:
                    content = mem_file.read_text(encoding="utf-8", errors="replace")
                    lower = content.lower()
                    if any(kw in lower for kw in ("changelog", "changes log", "skills", "installed skills")):
                        tracking_indicators.append(str(mem_file.name))
                except OSError:
                    pass

        metrics["has_tracking_files"] = len(tracking_indicators) > 0
        metrics["tracking_files"] = tracking_indicators
