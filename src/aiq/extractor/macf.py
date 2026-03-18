"""Extracts scanned items into the Model-Agnostic Config Format (MACF).

Converts platform-specific configurations into a structured JSON format
that can be injected into any model's API as a system prompt.
"""

from __future__ import annotations

import re

from aiq.extractor.models import MacfDocument, MacfEntry
from aiq.models import ItemCategory, ScannedItem, SkillEvaluation

# Categories that map to domain_knowledge
_DOMAIN_CATEGORIES = {ItemCategory.SKILL, ItemCategory.PLUGIN}

# Categories that map to workflow_patterns
_WORKFLOW_CATEGORIES = {ItemCategory.RULE, ItemCategory.SHELL_CONFIG, ItemCategory.AUTOMATION}

# Categories that map to tool_integrations
_TOOL_CATEGORIES = {ItemCategory.MCP_SERVER, ItemCategory.TOOL}

# Instruction files are split: workflow-related content -> workflow_patterns,
# domain-specific content -> domain_knowledge


class MacfExtractor:
    """Converts scan results into a Model-Agnostic Config Format document."""

    def extract(
        self,
        items: list[ScannedItem],
        evaluations: list[SkillEvaluation],
    ) -> MacfDocument:
        """Extract all scanned items into an MACF document."""
        doc = MacfDocument()
        eval_map: dict[str, SkillEvaluation] = {e.source: e for e in evaluations}

        for item in items:
            self._process_item(item, eval_map.get(item.source), doc)

        return doc

    def _process_item(
        self,
        item: ScannedItem,
        evaluation: SkillEvaluation | None,
        doc: MacfDocument,
    ) -> None:
        """Route a scanned item to the appropriate MACF section."""
        content = self._clean_content(item.content)
        if not content.strip():
            return

        if item.category in _DOMAIN_CATEGORIES:
            category = self._determine_category(evaluation)
            doc.domain_knowledge.append(
                MacfEntry(
                    source=self._format_source(item),
                    entry_type=self._classify_entry_type(item, content),
                    content=content,
                    category=category,
                )
            )

        elif item.category in _WORKFLOW_CATEGORIES:
            doc.workflow_patterns.append(
                MacfEntry(
                    source=self._format_source(item),
                    entry_type="process_rule",
                    content=content,
                    category="methodology",
                )
            )

        elif item.category in _TOOL_CATEGORIES:
            doc.tool_integrations.append(
                MacfEntry(
                    source=self._format_source(item),
                    entry_type="tool_manifest",
                    content=content,
                    category="tools",
                )
            )

        elif item.category == ItemCategory.INSTRUCTION_FILE:
            self._process_instruction_file(item, content, doc)

        elif item.category == ItemCategory.MEMORY:
            doc.domain_knowledge.append(
                MacfEntry(
                    source=self._format_source(item),
                    entry_type="context_memory",
                    content=content,
                    category="context",
                )
            )

        elif item.category == ItemCategory.CONFIG:
            doc.workflow_patterns.append(
                MacfEntry(
                    source=self._format_source(item),
                    entry_type="config_preference",
                    content=content,
                    category="preferences",
                )
            )

        elif item.category == ItemCategory.GIT_CONFIG:
            doc.tool_integrations.append(
                MacfEntry(
                    source=self._format_source(item),
                    entry_type="tool_config",
                    content=content,
                    category="tools",
                )
            )

    def _process_instruction_file(self, item: ScannedItem, content: str, doc: MacfDocument) -> None:
        """Split instruction files into domain knowledge and workflow patterns."""
        # Split by sections (## headers)
        sections = re.split(r"(?=^##\s)", content, flags=re.MULTILINE)
        workflow_keywords = [
            "workflow",
            "process",
            "session",
            "commit",
            "planning",
            "communication",
            "permission",
            "context",
        ]
        for section in sections:
            section = section.strip()
            if not section:
                continue
            first_line = section.split("\n")[0].lower()
            if any(kw in first_line for kw in workflow_keywords):
                doc.workflow_patterns.append(
                    MacfEntry(
                        source=self._format_source(item),
                        entry_type="process_rule",
                        content=section,
                        category="methodology",
                    )
                )
            else:
                doc.domain_knowledge.append(
                    MacfEntry(
                        source=self._format_source(item),
                        entry_type="coding_standard",
                        content=section,
                        category="engineering",
                    )
                )

    def _clean_content(self, content: str) -> str:
        """Strip platform-specific syntax while preserving semantic content."""
        # Remove markdown link syntax but keep text
        content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)
        # Remove backtick formatting (keep content)
        content = re.sub(r"`([^`]+)`", r"\1", content)
        # Normalize whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()

    def _format_source(self, item: ScannedItem) -> str:
        """Create a standardized source identifier."""
        category_prefix = item.category.value
        if item.category == ItemCategory.SKILL:
            skill_name = item.metadata.get("skill_name", "unknown")
            return f"skill:{skill_name}"
        elif item.category == ItemCategory.RULE:
            rule_name = item.metadata.get("rule_name", "unknown")
            return f"rule:{rule_name}"
        elif item.category == ItemCategory.INSTRUCTION_FILE:
            scope = item.metadata.get("scope", "")
            return f"instruction:{scope}"
        elif item.category == ItemCategory.MCP_SERVER:
            server_name = item.metadata.get("server_name", "")
            return f"mcp:{server_name}" if server_name else "mcp_servers"
        return f"{category_prefix}:{item.source}"

    def _determine_category(self, evaluation: SkillEvaluation | None) -> str:
        """Determine the domain category from evaluation results."""
        if evaluation and evaluation.domain_tags:
            return evaluation.domain_tags[0]
        return "general"

    def _classify_entry_type(self, item: ScannedItem, content: str) -> str:
        """Classify what type of entry this is based on content analysis."""
        content_lower = content.lower()
        if any(w in content_lower for w in ("when", "if", "evaluate", "check", "decision")):
            return "decision_framework"
        if any(w in content_lower for w in ("always", "never", "must", "standard")):
            return "coding_standard"
        if any(w in content_lower for w in ("step", "process", "workflow", "procedure")):
            return "process_rule"
        return "domain_knowledge"
