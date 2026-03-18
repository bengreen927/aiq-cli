"""Pydantic models for the Model-Agnostic Config Format (MACF)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MacfEntry(BaseModel):
    """A single entry in the MACF document."""

    source: str = Field(description="Where this entry was extracted from")
    entry_type: str = Field(
        description=("Type: decision_framework, process_rule, coding_standard, tool_manifest, etc.")
    )
    content: str = Field(description="The extracted content, stripped of platform syntax")
    category: str = Field(
        description="Domain category: engineering, regulatory, methodology, tools, etc."
    )


class MacfDocument(BaseModel):
    """The complete Model-Agnostic Config Format document."""

    domain_knowledge: list[MacfEntry] = Field(default_factory=list)
    workflow_patterns: list[MacfEntry] = Field(default_factory=list)
    tool_integrations: list[MacfEntry] = Field(default_factory=list)
