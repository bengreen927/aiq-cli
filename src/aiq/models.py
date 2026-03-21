"""Shared data models for AIQ CLI."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ItemCategory(str, Enum):
    """Category of a scanned item."""

    SKILL = "skill"
    RULE = "rule"
    INSTRUCTION_FILE = "instruction_file"
    MCP_SERVER = "mcp_server"
    TOOL = "tool"
    MEMORY = "memory"
    CONFIG = "config"
    AUTOMATION = "automation"
    PLUGIN = "plugin"
    SHELL_CONFIG = "shell_config"
    GIT_CONFIG = "git_config"
    ITERATION_METRICS = "ITERATION_METRICS"


class ScannedItem(BaseModel):
    """A single item discovered by a scanner."""

    source: str = Field(description="Where this item was found (file path, command, etc.)")
    category: ItemCategory
    content: str = Field(description="The raw content or description of the item")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScanResult(BaseModel):
    """Result from a single scanner module."""

    scanner_name: str
    items: list[ScannedItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @property
    def item_count(self) -> int:
        return len(self.items)


class SkillEvaluation(BaseModel):
    """Deep evaluation result for a skill/plugin/instruction file."""

    source: str
    line_count: int = 0
    domain_tags: list[str] = Field(default_factory=list)
    has_evaluation_criteria: bool = False
    references_external_tools: bool = False
    specificity_score: float = Field(
        default=0.0, description="0.0 (generic boilerplate) to 1.0 (highly domain-specific)"
    )
    sub_file_count: int = 0
    structure_depth: int = Field(
        default=0, description="Heading depth / organizational structure level"
    )


class UserProfile(BaseModel):
    """User profile created during aiq init."""

    company_name: Optional[str] = None  # noqa: UP045
    role_category: Optional[str] = None  # noqa: UP045
    email: Optional[str] = None  # noqa: UP045
