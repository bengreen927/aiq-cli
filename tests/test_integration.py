"""End-to-end integration tests: scan → extract → scrub → review pipeline."""

from __future__ import annotations

from pathlib import Path

from aiq.extractor.macf import MacfExtractor
from aiq.extractor.models import MacfDocument
from aiq.models import ItemCategory, ScannedItem, ScanResult, SkillEvaluation
from aiq.review.interactive import ReviewDecision, ReviewSession
from aiq.scanner.claude import ClaudeScanner
from aiq.scanner.registry import ScannerRegistry
from aiq.scrubber.pii import PiiScrubber, ScrubResult

FIXTURE_HOME = Path(__file__).parent / "fixtures" / "claude_home"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_items() -> list[ScannedItem]:
    """Build a small set of scanned items from the test fixture."""
    return [
        ScannedItem(
            source=str(FIXTURE_HOME / ".claude" / "CLAUDE.md"),
            category=ItemCategory.INSTRUCTION_FILE,
            content=(
                "# Global Preferences\n## Language\n- Always use python3\n"
                "## Tools\n- Use gh for GitHub"
            ),
            metadata={"line_count": 5, "scope": "global"},
        ),
        ScannedItem(
            source=str(FIXTURE_HOME / ".claude" / "skills" / "test-skill"),
            category=ItemCategory.SKILL,
            content=(
                "# Test Skill\nA domain-specific skill.\n"
                "## Evaluation Criteria\n- Check for accuracy"
            ),
            metadata={"skill_name": "test-skill", "file_count": 1, "line_count": 4},
        ),
        ScannedItem(
            source="mcp:github",
            category=ItemCategory.MCP_SERVER,
            content=(
                '{"name": "github", "command": "npx", "args": ["@anthropic/mcp-server-github"]}'
            ),
            metadata={"server_name": "github"},
        ),
        ScannedItem(
            source="git:config",
            category=ItemCategory.GIT_CONFIG,
            content="[alias]\n  st = status\n  co = checkout",
            metadata={},
        ),
    ]


# ---------------------------------------------------------------------------
# Stage 1: Scan
# ---------------------------------------------------------------------------


def test_scan_fixture_returns_items() -> None:
    """ClaudeScanner on the fixture home directory finds expected items."""
    scanner = ClaudeScanner(home_dir=FIXTURE_HOME)
    result = scanner.scan()

    assert isinstance(result, ScanResult)
    assert result.scanner_name == "claude_code"
    assert result.item_count > 0
    assert result.errors == []


def test_scan_fixture_finds_claude_md() -> None:
    scanner = ClaudeScanner(home_dir=FIXTURE_HOME)
    result = scanner.scan()

    instruction_items = [i for i in result.items if i.category == ItemCategory.INSTRUCTION_FILE]
    assert len(instruction_items) >= 1
    assert "python3" in instruction_items[0].content


def test_scan_fixture_finds_skill() -> None:
    scanner = ClaudeScanner(home_dir=FIXTURE_HOME)
    result = scanner.scan()

    skill_items = [i for i in result.items if i.category == ItemCategory.SKILL]
    assert len(skill_items) >= 1
    assert skill_items[0].metadata.get("skill_name") == "test-skill"


def test_registry_scan_produces_results() -> None:
    """Default registry runs without crashing and returns 5 results."""
    registry = ScannerRegistry.default()
    results = registry.scan_all()
    assert len(results) == 5
    for result in results:
        assert isinstance(result, ScanResult)


# ---------------------------------------------------------------------------
# Stage 2: Extract → MACF
# ---------------------------------------------------------------------------


def test_extract_produces_macf_document() -> None:
    items = _make_items()
    extractor = MacfExtractor()
    doc = extractor.extract(items, evaluations=[])

    assert isinstance(doc, MacfDocument)
    total = len(doc.domain_knowledge) + len(doc.workflow_patterns) + len(doc.tool_integrations)
    assert total > 0


def test_extract_skills_go_to_domain_knowledge() -> None:
    items = [_make_items()[1]]  # skill item only
    extractor = MacfExtractor()
    doc = extractor.extract(items, evaluations=[])

    assert len(doc.domain_knowledge) >= 1
    assert any(e.source.startswith("skill:") for e in doc.domain_knowledge)


def test_extract_mcp_servers_go_to_tool_integrations() -> None:
    items = [_make_items()[2]]  # mcp item only
    extractor = MacfExtractor()
    doc = extractor.extract(items, evaluations=[])

    assert len(doc.tool_integrations) >= 1
    assert any("mcp" in e.source for e in doc.tool_integrations)


def test_extract_with_evaluation_applies_domain_tags() -> None:
    skill_item = _make_items()[1]
    evaluation = SkillEvaluation(
        source=skill_item.source,
        domain_tags=["regulatory"],
        specificity_score=0.8,
        line_count=4,
    )
    extractor = MacfExtractor()
    doc = extractor.extract([skill_item], evaluations=[evaluation])

    assert len(doc.domain_knowledge) >= 1
    assert doc.domain_knowledge[0].category == "regulatory"


def test_extract_empty_items_produces_empty_document() -> None:
    extractor = MacfExtractor()
    doc = extractor.extract([], evaluations=[])

    assert doc.domain_knowledge == []
    assert doc.workflow_patterns == []
    assert doc.tool_integrations == []


# ---------------------------------------------------------------------------
# Stage 3: Scrub PII
# ---------------------------------------------------------------------------


def test_scrub_no_pii_returns_unchanged() -> None:
    items = _make_items()
    extractor = MacfExtractor()
    doc = extractor.extract(items, evaluations=[])
    macf_json = doc.model_dump_json()

    scrubber = PiiScrubber()
    result = scrubber.scrub_macf(macf_json)

    assert isinstance(result, ScrubResult)
    # No PII in fixture content
    assert result.replacement_count == 0


def test_scrub_removes_email_from_macf() -> None:
    items = [
        ScannedItem(
            source="test",
            category=ItemCategory.MEMORY,
            content="Contact admin at admin@example.com for access.",
            metadata={},
        )
    ]
    extractor = MacfExtractor()
    doc = extractor.extract(items, evaluations=[])
    macf_json = doc.model_dump_json()

    scrubber = PiiScrubber()
    result = scrubber.scrub_macf(macf_json)

    assert "admin@example.com" not in result.scrubbed_text
    assert "[EMAIL]" in result.scrubbed_text
    assert result.replacement_count >= 1
    assert "email" in result.categories_found


def test_scrub_replaces_company_name() -> None:
    items = [
        ScannedItem(
            source="test",
            category=ItemCategory.INSTRUCTION_FILE,
            content="We are at Acme Corp building AI tools.",
            metadata={"scope": "global"},
        )
    ]
    extractor = MacfExtractor()
    doc = extractor.extract(items, evaluations=[])
    macf_json = doc.model_dump_json()

    scrubber = PiiScrubber(company_name="Acme Corp")
    result = scrubber.scrub_macf(macf_json)

    assert "Acme Corp" not in result.scrubbed_text
    assert "[COMPANY]" in result.scrubbed_text
    assert "company" in result.categories_found


# ---------------------------------------------------------------------------
# Stage 4: Review (auto-approve path)
# ---------------------------------------------------------------------------


def test_review_session_auto_approve_all() -> None:
    items = _make_items()
    extractor = MacfExtractor()
    doc = extractor.extract(items, evaluations=[])

    session = ReviewSession(doc)
    session.approve_all()

    decisions = session.get_decisions()
    assert all(d == ReviewDecision.APPROVED for d in decisions.values())
    assert session.redacted_count == 0


def test_review_session_redact_one() -> None:
    items = _make_items()
    extractor = MacfExtractor()
    doc = extractor.extract(items, evaluations=[])

    session = ReviewSession(doc)
    session.approve_all()
    if session.total_entries > 0:
        session.redact(0)

    assert session.redacted_count == 1


def test_review_approved_document_excludes_redacted() -> None:
    items = _make_items()
    extractor = MacfExtractor()
    doc = extractor.extract(items, evaluations=[])

    session = ReviewSession(doc)
    session.approve_all()
    original_total = session.total_entries

    if original_total > 0:
        session.redact(0)

    approved_doc = session.get_approved_document()
    approved_total = (
        len(approved_doc.domain_knowledge)
        + len(approved_doc.workflow_patterns)
        + len(approved_doc.tool_integrations)
    )
    assert approved_total == original_total - 1


# ---------------------------------------------------------------------------
# Full pipeline test
# ---------------------------------------------------------------------------


def test_full_pipeline_scan_to_review() -> None:
    """The complete scan → extract → scrub → review pipeline produces valid output."""
    # 1. Scan
    scanner = ClaudeScanner(home_dir=FIXTURE_HOME)
    scan_result = scanner.scan()
    assert scan_result.item_count > 0

    # 2. Extract
    extractor = MacfExtractor()
    doc = extractor.extract(scan_result.items, evaluations=[])
    total_entries = (
        len(doc.domain_knowledge) + len(doc.workflow_patterns) + len(doc.tool_integrations)
    )
    assert total_entries > 0

    # 3. Scrub
    scrubber = PiiScrubber()
    macf_json = doc.model_dump_json()
    scrub_result = scrubber.scrub_macf(macf_json)
    assert isinstance(scrub_result.scrubbed_text, str)
    assert len(scrub_result.scrubbed_text) > 0

    # 4. Review (auto-approve)
    session = ReviewSession(doc)
    session.approve_all()
    approved_doc = session.get_approved_document()

    approved_total = (
        len(approved_doc.domain_knowledge)
        + len(approved_doc.workflow_patterns)
        + len(approved_doc.tool_integrations)
    )
    # All entries approved, none redacted
    assert approved_total == total_entries
    assert session.redacted_count == 0

    # 5. Approved document serializes cleanly
    output_json = approved_doc.model_dump_json()
    assert len(output_json) > 0
    assert "domain_knowledge" in output_json
