"""
Pydantic schemas for policy operations.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    policy_type: str = Field(pattern=r"^(access|device|network|temporal|data)$")
    description: str | None = None
    rego_content: str | None = None
    rules: dict[str, Any] = Field(default_factory=dict)
    attached_to: str | None = None  # React Flow element ID
    canvas_id: uuid.UUID


class PolicyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    rego_content: str | None = None
    rules: dict[str, Any] | None = None
    attached_to: str | None = None


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    policy_type: str
    description: str | None
    rego_content: str | None
    rules: dict[str, Any]
    attached_to: str | None
    canvas_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ── Template schemas ─────────────────────────────────────────

class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=10)
    canvas_data: dict[str, Any]
    policies_data: list[dict[str, Any]] = Field(default_factory=list)
    visibility: str = "public"


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    tags: list[str]
    canvas_data: dict[str, Any]
    policies_data: list[dict[str, Any]]
    forked_from: uuid.UUID | None
    fork_count: int
    visibility: str
    author_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TemplateFork(BaseModel):
    """When forking, you can optionally rename it."""
    name: str | None = Field(default=None, min_length=1, max_length=200)
