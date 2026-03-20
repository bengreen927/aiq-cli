"""PII auto-scrub — client-side, dual-layer with replacement not deletion.

Detects and replaces personal identifiable information with anonymous
placeholders. Replacements preserve sentence structure and functional
context. Original PII is never logged or stored.
"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field

from aiq.scrubber.patterns import get_patterns


class ScrubResult(BaseModel):
    """Result of a PII scrub operation."""

    scrubbed_text: str
    replacement_count: int = 0
    categories_found: list[str] = Field(default_factory=list)


class PiiScrubber:
    """Detects and replaces PII with anonymous placeholders."""

    def __init__(self, company_name: Optional[str] = None) -> None:
        self._company_name = company_name
        self._patterns = get_patterns()

    def scrub(self, text: str) -> ScrubResult:
        """Scrub PII from text, returning scrubbed text and metadata."""
        scrubbed = text
        total_replacements = 0
        categories: set[str] = set()

        # Company name replacement (user-declared, highest priority)
        if self._company_name:
            pattern = re.compile(re.escape(self._company_name), re.IGNORECASE)
            new_text = pattern.sub("[COMPANY]", scrubbed)
            if new_text != scrubbed:
                count = len(pattern.findall(scrubbed))
                total_replacements += count
                categories.add("company")
                scrubbed = new_text

        # Apply all regex patterns
        for category, pattern, replacement in self._patterns:
            matches = pattern.findall(scrubbed)
            if matches:
                scrubbed = pattern.sub(replacement, scrubbed)
                total_replacements += len(matches)
                categories.add(category)

        return ScrubResult(
            scrubbed_text=scrubbed,
            replacement_count=total_replacements,
            categories_found=sorted(categories),
        )

    def scrub_macf(self, macf_json: str) -> ScrubResult:
        """Scrub PII from a serialized MACF document."""
        return self.scrub(macf_json)
