"""Abstract base class for all scanner modules."""

from abc import ABC, abstractmethod

from aiq.models import ScanResult


class BaseScanner(ABC):
    """Base class that all scanner modules must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this scanner."""
        ...

    @abstractmethod
    def scan(self) -> ScanResult:
        """Run the scan and return results."""
        ...
