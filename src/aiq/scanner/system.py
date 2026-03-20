"""System-wide scanner — Homebrew, npm globals, pip, VS Code, cron, shell config."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from aiq.models import ItemCategory, ScannedItem, ScanResult
from aiq.scanner.base import BaseScanner


class SystemScanner(BaseScanner):
    """Scans system-wide tool installations and configurations."""

    def __init__(self, home_dir: Optional[Path] = None) -> None:
        self._home_dir = home_dir or Path.home()

    @property
    def name(self) -> str:
        return "system"

    def scan(self) -> ScanResult:
        result = ScanResult(scanner_name=self.name)

        collectors = [
            ("brew", self._scan_brew),
            ("npm_globals", self._scan_npm_globals),
            ("pip", self._scan_pip),
            ("vscode", self._scan_vscode_extensions),
            ("cron", self._scan_cron),
            ("shell", self._scan_shell_config),
        ]

        for collector_name, collector_fn in collectors:
            try:
                items = collector_fn()
                result.items.extend(items)
            except Exception as e:
                result.errors.append(f"{collector_name}: {e}")

        return result

    def _run_command(self, cmd: list[str], timeout: int = 30) -> Optional[str]:
        """Run a shell command and return stdout, or None on failure."""
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return None
        if proc.returncode != 0:
            return None
        return proc.stdout

    def _scan_brew(self) -> list[ScannedItem]:
        """Scan Homebrew packages via `brew bundle dump --file=-`."""
        output = self._run_command(["brew", "bundle", "dump", "--file=-"])
        if not output:
            return []

        packages = [line.strip() for line in output.splitlines() if line.strip()]
        return [
            ScannedItem(
                source="homebrew",
                category=ItemCategory.TOOL,
                content="\n".join(packages),
                metadata={"package_count": len(packages)},
            )
        ]

    def _scan_npm_globals(self) -> list[ScannedItem]:
        """Scan npm global packages via `npm list -g --depth=0`."""
        output = self._run_command(["npm", "list", "-g", "--depth=0"])
        if not output:
            return []

        lines = [line.strip() for line in output.splitlines() if "\u2500\u2500" in line]
        if not lines:
            return []

        return [
            ScannedItem(
                source="npm_globals",
                category=ItemCategory.TOOL,
                content="\n".join(lines),
                metadata={"package_count": len(lines)},
            )
        ]

    def _scan_pip(self) -> list[ScannedItem]:
        """Scan pip packages via `pip list --format=freeze`."""
        output = self._run_command(["python3", "-m", "pip", "list", "--format=freeze"])
        if not output:
            return []

        packages = [line.strip() for line in output.splitlines() if line.strip()]
        return [
            ScannedItem(
                source="pip_packages",
                category=ItemCategory.TOOL,
                content="\n".join(packages),
                metadata={"package_count": len(packages)},
            )
        ]

    def _scan_vscode_extensions(self) -> list[ScannedItem]:
        """Scan VS Code extensions via `code --list-extensions`."""
        output = self._run_command(["code", "--list-extensions"])
        if not output:
            return []

        extensions = [line.strip() for line in output.splitlines() if line.strip()]
        if not extensions:
            return []

        return [
            ScannedItem(
                source="vscode_extensions",
                category=ItemCategory.TOOL,
                content="\n".join(extensions),
                metadata={"extension_count": len(extensions)},
            )
        ]

    def _scan_cron(self) -> list[ScannedItem]:
        """Scan cron jobs via `crontab -l`."""
        output = self._run_command(["crontab", "-l"])
        if not output:
            return []

        jobs = [
            line.strip()
            for line in output.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        if not jobs:
            return []

        return [
            ScannedItem(
                source="crontab",
                category=ItemCategory.AUTOMATION,
                content="\n".join(jobs),
                metadata={"job_count": len(jobs)},
            )
        ]

    def _scan_shell_config(self) -> list[ScannedItem]:
        """Scan .zshrc / .bashrc for aliases and functions."""
        items: list[ScannedItem] = []
        shell_files = [".zshrc", ".bashrc", ".bash_profile", ".zprofile"]

        for filename in shell_files:
            filepath = self._home_dir / filename
            if not filepath.is_file():
                continue

            content = filepath.read_text(encoding="utf-8", errors="replace")
            # Extract only aliases and functions (not full file — privacy)
            relevant_lines = []
            in_function = False
            brace_depth = 0
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("alias "):
                    relevant_lines.append(stripped)
                elif stripped.startswith("function ") or (
                    "() {" in stripped and not stripped.startswith("#")
                ):
                    in_function = True
                    brace_depth = 0

                if in_function:
                    relevant_lines.append(line)
                    brace_depth += line.count("{") - line.count("}")
                    if brace_depth <= 0 and "{" in "".join(relevant_lines):
                        in_function = False

            if relevant_lines:
                items.append(
                    ScannedItem(
                        source=str(filepath),
                        category=ItemCategory.SHELL_CONFIG,
                        content="\n".join(relevant_lines),
                        metadata={
                            "filename": filename,
                            "alias_count": sum(
                                1 for line in relevant_lines if line.strip().startswith("alias ")
                            ),
                        },
                    )
                )

        return items
