"""Tests for deep evaluator of skills, plugins, and instruction files."""

from aiq.models import ItemCategory, ScannedItem
from aiq.scanner.evaluator import DeepEvaluator


def _make_skill_item(content: str, name: str = "test-skill") -> ScannedItem:
    return ScannedItem(
        source=f"/home/user/.claude/skills/{name}",
        category=ItemCategory.SKILL,
        content=content,
        metadata={"skill_name": name, "file_count": 1, "line_count": len(content.splitlines())},
    )


def test_evaluator_line_count() -> None:
    content = "line1\nline2\nline3\n"
    item = _make_skill_item(content)
    evaluator = DeepEvaluator()
    result = evaluator.evaluate_item(item)
    assert result.line_count == 3


def test_evaluator_detects_domain_tags() -> None:
    content = """# FDA Regulatory Strategy
    Evaluate 510(k) pathway. Check ISO 14971 risk management.
    Review ASTM standards for biocompatibility."""
    item = _make_skill_item(content, "fda-regulatory")
    evaluator = DeepEvaluator()
    result = evaluator.evaluate_item(item)
    assert "regulatory" in result.domain_tags or "fda" in result.domain_tags


def test_evaluator_detects_evaluation_criteria() -> None:
    content = """# Test Skill
    ## Evaluation Criteria
    - Check for accuracy
    - Verify completeness"""
    item = _make_skill_item(content)
    evaluator = DeepEvaluator()
    result = evaluator.evaluate_item(item)
    assert result.has_evaluation_criteria is True


def test_evaluator_detects_external_tools() -> None:
    content = """# Skill
    Uses the Qualio API for document management.
    Integrates with GitHub via gh CLI."""
    item = _make_skill_item(content)
    evaluator = DeepEvaluator()
    result = evaluator.evaluate_item(item)
    assert result.references_external_tools is True


def test_evaluator_specificity_generic_vs_specific() -> None:
    generic = _make_skill_item("Be concise. Write clean code. Follow best practices.")
    specific = _make_skill_item(
        """# FDA 510(k) Regulatory Strategy
        When evaluating predicate devices, check GUDID database.
        Use ISO 14971:2019 risk management framework.
        Cross-reference 21 CFR 820 design controls.
        Apply ASTM F2502 for spinal implant testing."""
    )
    evaluator = DeepEvaluator()
    generic_result = evaluator.evaluate_item(generic)
    specific_result = evaluator.evaluate_item(specific)
    assert specific_result.specificity_score > generic_result.specificity_score


def test_evaluator_structure_depth() -> None:
    content = """# Top Level
    ## Second Level
    ### Third Level
    Content here."""
    item = _make_skill_item(content)
    evaluator = DeepEvaluator()
    result = evaluator.evaluate_item(item)
    assert result.structure_depth == 3


def test_evaluator_instruction_file() -> None:
    item = ScannedItem(
        source="/home/user/.claude/CLAUDE.md",
        category=ItemCategory.INSTRUCTION_FILE,
        content="# Preferences\n## Language\n- Use python3\n## Tools\n- Use gh CLI",
        metadata={"line_count": 4, "scope": "global"},
    )
    evaluator = DeepEvaluator()
    result = evaluator.evaluate_item(item)
    assert result.line_count == 4
    assert result.structure_depth >= 2


def test_evaluator_rule_file() -> None:
    item = ScannedItem(
        source="/home/user/.claude/rules/testing.md",
        category=ItemCategory.RULE,
        content=(
            "# Testing Philosophy\nMock at system boundaries only.\nNever mock internal classes."
        ),
        metadata={"rule_name": "testing", "line_count": 3},
    )
    evaluator = DeepEvaluator()
    result = evaluator.evaluate_item(item)
    assert result.line_count == 3
