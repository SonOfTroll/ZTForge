"""
Pydantic schemas for canvas operations.

Separates wire format from DB models. Schemas handle validation and
serialization; models handle persistence.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Node/Edge Types ──────────────────────────────────────────
# Mirror React Flow's data model closely to minimize frontend mapping

class Position(BaseModel):
    x: float
    y: float


class NodeData(BaseModel):
    """Common fields for all node types on the canvas."""
    label: str
    node_type: str  # identity, device, application, data, network_segment, policy_gate
    properties: dict[str, Any] = Field(default_factory=dict)
    compliance_status: str | None = None  # for device nodes
    classification: str | None = None  # for data nodes


class CanvasNode(BaseModel):
    id: str
    type: str
    position: Position
    data: NodeData
    width: float | None = None
    height: float | None = None


class EdgePolicy(BaseModel):
    """Policy attached to an edge — determines if traffic is allowed."""
    action: str = "deny"  # "allow" or "deny"
    conditions: dict[str, Any] = Field(default_factory=dict)
    # e.g. {"require_mfa": true, "allowed_hours": "09:00-17:00", "require_compliant_device": true}


class CanvasEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None
    animated: bool = False
    policy: EdgePolicy | None = None


# ── Canvas CRUD Schemas ──────────────────────────────────────

class CanvasCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    visibility: str = "private"


class CanvasUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    nodes: list[CanvasNode] | None = None
    edges: list[CanvasEdge] | None = None
    viewport: dict[str, Any] | None = None
    version: int  # required for OCC — client must send current version


class CanvasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    viewport: dict[str, Any]
    version: int
    visibility: str
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CanvasListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    visibility: str
    version: int
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
