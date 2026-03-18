"""Tests for pre-transmission interactive review."""

from aiq.extractor.models import MacfDocument, MacfEntry
from aiq.review.interactive import ReviewDecision, ReviewSession


def _make_doc() -> MacfDocument:
    return MacfDocument(
        domain_knowledge=[
            MacfEntry(
                source="skill:fda-reg",
                entry_type="decision_framework",
                content="Check predicate availability for 510(k).",
                category="regulatory",
            ),
            MacfEntry(
                source="skill:testing",
                entry_type="coding_standard",
                content="Always write tests first.",
                category="engineering",
            ),
        ],
        workflow_patterns=[
            MacfEntry(
                source="rule:workflow",
                entry_type="process_rule",
                content="Plan before implementing.",
                category="methodology",
            ),
        ],
        tool_integrations=[
            MacfEntry(
                source="mcp:github",
                entry_type="tool_manifest",
                content="github: code repository management",
                category="tools",
            ),
        ],
    )


def test_review_session_lists_all_entries() -> None:
    doc = _make_doc()
    session = ReviewSession(doc)
    entries = session.get_all_entries()
    assert len(entries) == 4


def test_review_session_redact_entry() -> None:
    doc = _make_doc()
    session = ReviewSession(doc)
    # Redact the first entry
    session.redact(0)
    approved = session.get_approved_document()
    assert len(approved.domain_knowledge) == 1  # Was 2, now 1
    assert approved.domain_knowledge[0].source == "skill:testing"


def test_review_session_approve_all() -> None:
    doc = _make_doc()
    session = ReviewSession(doc)
    session.approve_all()
    approved = session.get_approved_document()
    assert len(approved.domain_knowledge) == 2
    assert len(approved.workflow_patterns) == 1
    assert len(approved.tool_integrations) == 1


def test_review_session_redact_multiple() -> None:
    doc = _make_doc()
    session = ReviewSession(doc)
    session.redact(0)
    session.redact(1)
    approved = session.get_approved_document()
    total = (
        len(approved.domain_knowledge)
        + len(approved.workflow_patterns)
        + len(approved.tool_integrations)
    )
    assert total == 2


def test_review_decision_tracking() -> None:
    doc = _make_doc()
    session = ReviewSession(doc)
    session.redact(0)
    session.approve(1)
    decisions = session.get_decisions()
    assert decisions[0] == ReviewDecision.REDACTED
    assert decisions[1] == ReviewDecision.APPROVED
