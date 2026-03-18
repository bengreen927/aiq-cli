"""Tests for MACF (Model-Agnostic Config Format) extractor."""

import json

from aiq.extractor.macf import MacfExtractor
from aiq.extractor.models import MacfDocument, MacfEntry
from aiq.models import ItemCategory, ScannedItem, SkillEvaluation


def test_macf_entry_serialization() -> None:
    entry = MacfEntry(
        source="skill:fda-regulatory",
        entry_type="decision_framework",
        content="When evaluating pathway, check predicates first.",
        category="regulatory",
    )
    data = entry.model_dump()
    assert data["source"] == "skill:fda-regulatory"
    assert data["entry_type"] == "decision_framework"


def test_macf_document_to_json() -> None:
    doc = MacfDocument()
    doc.domain_knowledge.append(
        MacfEntry(
            source="skill:test",
            entry_type="domain_rule",
            content="Always validate input.",
            category="engineering",
        )
    )
    json_str = doc.model_dump_json(indent=2)
    parsed = json.loads(json_str)
    assert len(parsed["domain_knowledge"]) == 1


def test_extractor_skill_to_domain_knowledge() -> None:
    items = [
        ScannedItem(
            source="/home/user/.claude/skills/fda-reg",
            category=ItemCategory.SKILL,
            content="When evaluating regulatory pathway: check predicate availability.",
            metadata={"skill_name": "fda-reg", "line_count": 5},
        )
    ]
    evaluations = [
        SkillEvaluation(
            source="/home/user/.claude/skills/fda-reg",
            line_count=5,
            domain_tags=["regulatory"],
            specificity_score=0.8,
        )
    ]
    extractor = MacfExtractor()
    doc = extractor.extract(items, evaluations)
    assert len(doc.domain_knowledge) >= 1
    assert doc.domain_knowledge[0].category == "regulatory"


def test_extractor_rule_to_workflow() -> None:
    items = [
        ScannedItem(
            source="/home/user/.claude/rules/workflow.md",
            category=ItemCategory.RULE,
            content="Plan first for non-trivial tasks. Use subagents for parallel research.",
            metadata={"rule_name": "workflow", "line_count": 2},
        )
    ]
    extractor = MacfExtractor()
    doc = extractor.extract(items, [])
    assert len(doc.workflow_patterns) >= 1


def test_extractor_mcp_to_tools() -> None:
    items = [
        ScannedItem(
            source="claude_mcp_list",
            category=ItemCategory.MCP_SERVER,
            content="qualio: QMS document management",
            metadata={"server_name": "qualio"},
        )
    ]
    extractor = MacfExtractor()
    doc = extractor.extract(items, [])
    assert len(doc.tool_integrations) >= 1


def test_extractor_tool_to_tools() -> None:
    items = [
        ScannedItem(
            source="homebrew",
            category=ItemCategory.TOOL,
            content='brew "node"\nbrew "python3"',
            metadata={"package_count": 2},
        )
    ]
    extractor = MacfExtractor()
    doc = extractor.extract(items, [])
    assert len(doc.tool_integrations) >= 1


def test_extractor_strips_platform_syntax() -> None:
    items = [
        ScannedItem(
            source="/home/user/.claude/CLAUDE.md",
            category=ItemCategory.INSTRUCTION_FILE,
            content="## Language & Runtime\n- Always use `python3`, never `python`",
            metadata={"line_count": 2, "scope": "global"},
        )
    ]
    extractor = MacfExtractor()
    doc = extractor.extract(items, [])
    # Content should be extracted, platform-specific formatting minimized
    assert len(doc.domain_knowledge) + len(doc.workflow_patterns) >= 1
