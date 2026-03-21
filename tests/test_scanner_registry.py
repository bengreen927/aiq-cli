"""Tests for the scanner registry."""

from __future__ import annotations

from aiq.models import ScanResult
from aiq.scanner.base import BaseScanner
from aiq.scanner.registry import ScannerRegistry


class _StubScanner(BaseScanner):
    """Minimal scanner for testing."""

    def __init__(self, scanner_name: str, item_count: int = 0) -> None:
        self._scanner_name = scanner_name
        self._item_count = item_count

    @property
    def name(self) -> str:
        return self._scanner_name

    def scan(self) -> ScanResult:
        return ScanResult(scanner_name=self._scanner_name)


def test_registry_starts_empty() -> None:
    registry = ScannerRegistry()
    assert registry.scanner_names == []


def test_register_single_scanner() -> None:
    registry = ScannerRegistry()
    registry.register(_StubScanner("alpha"))
    assert registry.scanner_names == ["alpha"]


def test_register_multiple_scanners() -> None:
    registry = ScannerRegistry()
    registry.register(_StubScanner("alpha"))
    registry.register(_StubScanner("beta"))
    registry.register(_StubScanner("gamma"))
    assert registry.scanner_names == ["alpha", "beta", "gamma"]


def test_scan_all_returns_one_result_per_scanner() -> None:
    registry = ScannerRegistry()
    registry.register(_StubScanner("alpha"))
    registry.register(_StubScanner("beta"))

    results = registry.scan_all()
    assert len(results) == 2
    assert results[0].scanner_name == "alpha"
    assert results[1].scanner_name == "beta"


def test_scan_all_empty_registry() -> None:
    registry = ScannerRegistry()
    results = registry.scan_all()
    assert results == []


def test_default_registry_has_six_scanners() -> None:
    registry = ScannerRegistry.default()
    assert len(registry.scanner_names) == 6


def test_default_registry_scanner_names() -> None:
    registry = ScannerRegistry.default()
    names = registry.scanner_names
    assert "claude_code" in names
    assert "cursor" in names
    assert "system" in names
    assert "mcp" in names
    assert "git" in names
    assert "iteration" in names


def test_default_registry_scan_all_returns_results() -> None:
    """Default registry can run without errors (results may be empty on CI)."""
    registry = ScannerRegistry.default()
    results = registry.scan_all()
    # Should return exactly 6 results
    assert len(results) == 6
    # Each result should have the right scanner name
    for result in results:
        assert result.scanner_name in registry.scanner_names


def test_registry_preserves_insertion_order() -> None:
    registry = ScannerRegistry()
    names = ["first", "second", "third", "fourth"]
    for name in names:
        registry.register(_StubScanner(name))
    assert registry.scanner_names == names
