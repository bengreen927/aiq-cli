"""Scanner registry — auto-discovers and runs all scanner modules."""

from __future__ import annotations

from typing import Iterator, Tuple

from aiq.models import ScanResult  # noqa: TCH001
from aiq.scanner.base import BaseScanner  # noqa: TCH001
from aiq.scanner.claude import ClaudeScanner
from aiq.scanner.cursor import CursorScanner
from aiq.scanner.git import GitScanner
from aiq.scanner.iteration import IterationScanner
from aiq.scanner.mcp import McpScanner
from aiq.scanner.system import SystemScanner


class ScannerRegistry:
    """Registry that holds and runs all scanner modules.

    Usage::

        registry = ScannerRegistry.default()
        results = registry.scan_all()
    """

    def __init__(self) -> None:
        self._scanners: list[BaseScanner] = []

    def register(self, scanner: BaseScanner) -> None:
        """Add a scanner to the registry."""
        self._scanners.append(scanner)

    def scan_all(self) -> list[ScanResult]:
        """Run all registered scanners and return their results."""
        results: list[ScanResult] = []
        for scanner in self._scanners:
            result = scanner.scan()
            results.append(result)
        return results

    def iter_scanners(self) -> Iterator[Tuple[str, BaseScanner]]:
        """Iterate over registered scanners as (name, scanner) tuples."""
        for scanner in self._scanners:
            yield scanner.name, scanner

    @property
    def scanner_names(self) -> list[str]:
        """Names of all registered scanners."""
        return [s.name for s in self._scanners]

    @classmethod
    def default(cls) -> ScannerRegistry:
        """Build the default registry with all 6 built-in scanners."""
        registry = cls()
        registry.register(ClaudeScanner())
        registry.register(CursorScanner())
        registry.register(SystemScanner())
        registry.register(McpScanner())
        registry.register(GitScanner())
        registry.register(IterationScanner())
        return registry
