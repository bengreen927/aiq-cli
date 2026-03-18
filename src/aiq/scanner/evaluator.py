"""Deep evaluation of skills, plugins, and instruction files.

Analyzes structure, specificity, domain coverage, and depth to produce
SkillEvaluation objects that feed into adaptive challenge selection.
"""

from __future__ import annotations

import re

from aiq.models import ItemCategory, ScannedItem, SkillEvaluation

# Domain keyword mappings for tag detection
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "regulatory": [
        "fda",
        "510(k)",
        "pma",
        "de novo",
        "regulatory",
        "submission",
        "clearance",
        "predicate",
        "21 cfr",
        "qsr",
        "mdr",
        "ivdr",
        "ce mark",
    ],
    "engineering": [
        "api",
        "database",
        "docker",
        "kubernetes",
        "ci/cd",
        "git",
        "pytest",
        "architecture",
        "microservice",
        "rest",
        "graphql",
        "sdk",
    ],
    "quality": [
        "iso 13485",
        "iso 9001",
        "capa",
        "nonconformance",
        "audit",
        "sop",
        "quality system",
        "qms",
        "design control",
        "verification",
        "validation",
    ],
    "risk": [
        "iso 14971",
        "risk management",
        "fmea",
        "hazard",
        "risk analysis",
        "risk control",
        "risk assessment",
    ],
    "clinical": [
        "clinical trial",
        "clinical study",
        "ide",
        "irb",
        "informed consent",
        "clinical data",
        "clinical evaluation",
    ],
    "manufacturing": [
        "injection molding",
        "lean",
        "six sigma",
        "oee",
        "spc",
        "dmaic",
        "manufacturing",
        "production",
        "process validation",
    ],
    "testing": [
        "tdd",
        "unit test",
        "integration test",
        "pytest",
        "mock",
        "fixture",
        "test-driven",
        "coverage",
    ],
    "security": [
        "cybersecurity",
        "vulnerability",
        "penetration",
        "threat model",
        "encryption",
        "authentication",
        "authorization",
    ],
    "biocompatibility": [
        "iso 10993",
        "biocompatibility",
        "cytotoxicity",
        "e&l",
        "extractables",
        "leachables",
    ],
    "sterilization": [
        "sterilization",
        "eo",
        "ethylene oxide",
        "radiation",
        "steam",
        "sterile barrier",
        "packaging validation",
    ],
    "data": [
        "data pipeline",
        "etl",
        "analytics",
        "visualization",
        "sql",
        "pandas",
        "statistics",
        "machine learning",
    ],
    "marketing": [
        "seo",
        "content strategy",
        "ad copy",
        "conversion",
        "campaign",
        "social media",
        "email marketing",
    ],
    "product": [
        "roadmap",
        "user story",
        "sprint",
        "backlog",
        "stakeholder",
        "product strategy",
        "okr",
    ],
    "design": [
        "figma",
        "ui/ux",
        "wireframe",
        "prototype",
        "design system",
        "user research",
        "accessibility",
    ],
}

# Phrases that indicate generic/boilerplate content
_GENERIC_PHRASES = [
    "be concise",
    "write clean code",
    "follow best practices",
    "be helpful",
    "use clear language",
    "respond accurately",
    "be professional",
]

# Patterns indicating external tool/API references
_EXTERNAL_TOOL_PATTERNS = re.compile(
    r"\b(api|cli|mcp|sdk|webhook|endpoint|integration|plugin)\b",
    re.IGNORECASE,
)


class DeepEvaluator:
    """Performs deep evaluation of skills, plugins, and instruction files."""

    def evaluate_item(self, item: ScannedItem) -> SkillEvaluation:
        """Evaluate a single scanned item for depth, specificity, and domain coverage."""
        content = item.content
        lines = content.splitlines()

        # Use metadata line_count if provided, otherwise count non-empty lines from content
        meta_line_count = item.metadata.get("line_count")
        if meta_line_count is not None:
            line_count = int(meta_line_count)
        else:
            line_count = len([ln for ln in lines if ln.strip()])

        return SkillEvaluation(
            source=item.source,
            line_count=line_count,
            domain_tags=self._detect_domains(content),
            has_evaluation_criteria=self._has_evaluation_criteria(content),
            references_external_tools=self._references_tools(content),
            specificity_score=self._compute_specificity(content),
            sub_file_count=item.metadata.get("file_count", 0),
            structure_depth=self._compute_structure_depth(content),
        )

    def evaluate_all(self, items: list[ScannedItem]) -> list[SkillEvaluation]:
        """Evaluate all items that qualify for deep evaluation."""
        evaluable_categories: set[ItemCategory] = {
            ItemCategory.SKILL,
            ItemCategory.RULE,
            ItemCategory.INSTRUCTION_FILE,
            ItemCategory.PLUGIN,
        }
        return [self.evaluate_item(item) for item in items if item.category in evaluable_categories]

    def _detect_domains(self, content: str) -> list[str]:
        """Detect domain tags based on keyword presence."""
        content_lower = content.lower()
        detected: list[str] = []

        for domain, keywords in _DOMAIN_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw.lower() in content_lower)
            if matches >= 2:
                detected.append(domain)

        return sorted(detected)

    def _has_evaluation_criteria(self, content: str) -> bool:
        """Check if content includes evaluation/assessment criteria."""
        patterns = [
            r"evaluation\s+criteria",
            r"assessment\s+criteria",
            r"grading\s+rubric",
            r"scoring\s+criteria",
            r"acceptance\s+criteria",
            r"checklist",
        ]
        content_lower = content.lower()
        return any(re.search(p, content_lower) for p in patterns)

    def _references_tools(self, content: str) -> bool:
        """Check if content references external tools or APIs."""
        return bool(_EXTERNAL_TOOL_PATTERNS.search(content))

    def _compute_specificity(self, content: str) -> float:
        """Compute specificity score: 0.0 (generic) to 1.0 (domain-specific).

        Factors:
        - Presence of specific standards, tools, or frameworks (positive)
        - Presence of generic boilerplate phrases (negative)
        - Content length (longer = more likely to be specific)
        - Domain keyword density
        """
        content_lower = content.lower()
        words = content_lower.split()
        if not words:
            return 0.0

        # Count domain-specific keywords
        domain_keyword_count = 0
        for keywords in _DOMAIN_KEYWORDS.values():
            for kw in keywords:
                if kw.lower() in content_lower:
                    domain_keyword_count += 1

        # Count generic phrases
        generic_count = sum(1 for phrase in _GENERIC_PHRASES if phrase in content_lower)

        # Compute factors
        keyword_density = min(domain_keyword_count / max(len(words) / 20, 1), 1.0)
        generic_penalty = min(generic_count * 0.15, 0.5)
        length_bonus = min(len(words) / 200, 0.3)

        # Specific patterns that boost score
        specific_patterns = [
            r"\d+\s*cfr\s*\d+",  # CFR references
            r"iso\s*\d+",  # ISO standards
            r"astm\s*[a-z]?\d+",  # ASTM standards
            r"iec\s*\d+",  # IEC standards
        ]
        pattern_bonus = sum(0.1 for p in specific_patterns if re.search(p, content_lower))

        score = keyword_density + length_bonus + pattern_bonus - generic_penalty
        return max(0.0, min(1.0, score))

    def _compute_structure_depth(self, content: str) -> int:
        """Compute max heading depth (# = 1, ## = 2, etc.)."""
        max_depth = 0
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                hashes = len(stripped) - len(stripped.lstrip("#"))
                max_depth = max(max_depth, hashes)
        return max_depth
