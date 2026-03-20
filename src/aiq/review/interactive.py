"""Pre-transmission interactive review.

Presents the user with every entry that will be transmitted and allows
line-by-line redaction before anything leaves the machine.
"""

from __future__ import annotations

from enum import Enum

from aiq.extractor.models import MacfDocument, MacfEntry


class ReviewDecision(str, Enum):
    """Decision for each entry in the review."""

    PENDING = "pending"
    APPROVED = "approved"
    REDACTED = "redacted"


class ReviewSession:
    """Manages the pre-transmission review process.

    Entries are indexed in a flat list across all MACF sections.
    The user can approve or redact each entry by index.
    """

    def __init__(self, document: MacfDocument) -> None:
        self._document = document
        self._entries: list[tuple[str, MacfEntry]] = []
        self._decisions: dict[int, ReviewDecision] = {}

        # Build flat index: (section_name, entry)
        for entry in document.domain_knowledge:
            self._entries.append(("domain_knowledge", entry))
        for entry in document.workflow_patterns:
            self._entries.append(("workflow_patterns", entry))
        for entry in document.tool_integrations:
            self._entries.append(("tool_integrations", entry))

        # Default all to pending
        for i in range(len(self._entries)):
            self._decisions[i] = ReviewDecision.PENDING

    def get_all_entries(self) -> list[tuple[int, str, MacfEntry]]:
        """Return all entries with their index and section name."""
        return [(i, section, entry) for i, (section, entry) in enumerate(self._entries)]

    def approve(self, index: int) -> None:
        """Approve an entry for transmission."""
        if 0 <= index < len(self._entries):
            self._decisions[index] = ReviewDecision.APPROVED

    def redact(self, index: int) -> None:
        """Redact an entry -- it will not be transmitted."""
        if 0 <= index < len(self._entries):
            self._decisions[index] = ReviewDecision.REDACTED

    def approve_all(self) -> None:
        """Approve all entries."""
        for i in range(len(self._entries)):
            self._decisions[i] = ReviewDecision.APPROVED

    def get_decisions(self) -> dict[int, ReviewDecision]:
        """Return current decisions for all entries."""
        return dict(self._decisions)

    def get_approved_document(self) -> MacfDocument:
        """Build a new MACF document containing only approved entries."""
        domain: list[MacfEntry] = []
        workflow: list[MacfEntry] = []
        tools: list[MacfEntry] = []

        for i, (section, entry) in enumerate(self._entries):
            if self._decisions[i] != ReviewDecision.APPROVED:
                continue
            if section == "domain_knowledge":
                domain.append(entry)
            elif section == "workflow_patterns":
                workflow.append(entry)
            elif section == "tool_integrations":
                tools.append(entry)

        return MacfDocument(
            domain_knowledge=domain,
            workflow_patterns=workflow,
            tool_integrations=tools,
        )

    @property
    def total_entries(self) -> int:
        return len(self._entries)

    @property
    def redacted_count(self) -> int:
        return sum(1 for d in self._decisions.values() if d == ReviewDecision.REDACTED)
