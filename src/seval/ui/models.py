"""Pydantic models for Policy Management UI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class RuleMatch(BaseModel):
    """Rule match patterns."""
    regex: Optional[List[str]] = None
    substrings: Optional[List[str]] = None

    @field_validator("regex", "substrings")
    @classmethod
    def validate_pattern_list(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None and not all(isinstance(item, str) for item in v):
            raise ValueError("All patterns must be strings")
        return v


class PolicyRule(BaseModel):
    """Policy rule definition."""
    id: str = Field(..., description="Unique rule identifier")
    weight: float = Field(..., gt=0, description="Rule weight (must be > 0)")
    action: str = Field(..., description="Action to take (block/pass)")
    match: RuleMatch = Field(..., description="Match patterns")
    languages: Optional[List[str]] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ["block", "pass"]:
            raise ValueError("action must be 'block' or 'pass'")
        return v


class PolicySlice(BaseModel):
    """Policy slice definition."""
    id: Optional[str] = None
    category: str = Field(..., description="Category name")
    language: str = Field(..., description="Language code")
    threshold: float = Field(..., ge=0.0, le=5.0, description="Threshold [0, 5]")
    rules: List[PolicyRule] = Field(..., min_length=1, description="At least one rule required")


class SafeContext(BaseModel):
    """Safe context definition."""
    id: str = Field(..., description="Context identifier")
    type: str = Field(..., description="Context type (regex)")
    patterns: List[str] = Field(..., min_length=1, description="Pattern list")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != "regex":
            raise ValueError("type must be 'regex'")
        return v


class PolicyPenalties(BaseModel):
    """Policy penalties."""
    safe_context: Optional[float] = None


class PolicyMetadata(BaseModel):
    """Policy metadata."""
    name: Optional[str] = None
    description: Optional[str] = None
    default_action: Optional[str] = None


class PolicyModel(BaseModel):
    """Complete policy model with validation."""
    version: int = Field(..., description="Policy version (integer)")
    metadata: Optional[PolicyMetadata] = None
    safe_contexts: Optional[List[SafeContext]] = None
    penalties: Optional[PolicyPenalties] = None
    slices: List[PolicySlice] = Field(..., min_length=1, description="Policy slices")

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: int) -> int:
        if not isinstance(v, int):
            raise ValueError("version must be an integer")
        return v


class PolicyUpdateRequest(BaseModel):
    """Request model for updating a policy."""
    yaml_content: str = Field(..., description="YAML policy content")


class TestRequest(BaseModel):
    """Request model for testing policies."""
    text: str = Field(..., description="Text to test")
    category: str = Field(default="violence", description="Category")
    language: str = Field(default="en", description="Language code")


class TestResponse(BaseModel):
    """Response model for policy test."""
    score: float
    blocked: bool
    category: str
    language: str
    latency_ms: int
    policy_version: str

