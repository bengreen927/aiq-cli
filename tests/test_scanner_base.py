"""Tests for scanner base class."""

import pytest

from aiq.models import ScanResult
from aiq.scanner.base import BaseScanner


def test_base_scanner_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseScanner()  # type: ignore[abstract]


def test_concrete_scanner_must_implement_scan() -> None:
    class IncompleteScanner(BaseScanner):
        @property
        def name(self) -> str:
            return "incomplete"

    with pytest.raises(TypeError):
        IncompleteScanner()  # type: ignore[abstract]


def test_concrete_scanner_works() -> None:
    class TestScanner(BaseScanner):
        @property
        def name(self) -> str:
            return "test"

        def scan(self) -> ScanResult:
            return ScanResult(scanner_name=self.name)

    scanner = TestScanner()
    assert scanner.name == "test"
    result = scanner.scan()
    assert result.scanner_name == "test"
    assert result.item_count == 0
