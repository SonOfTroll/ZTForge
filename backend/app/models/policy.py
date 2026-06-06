"""
Policy model — Zero Trust policies attached to canvas edges/nodes.

A policy defines access rules between two points in the architecture.
The rego_content field stores the OPA-compatible rule that gets pushed
to OPA for evaluation during simulation and enforcement.

policy_type values:
- "access"     — who/what can access a resource
- "device"     — device compliance requirements
- "network"    — network segmentation rules
- "temporal"   — time-based access restrictions
- "data"       — data classification/handling rules
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The actual Rego policy content
    rego_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured rule definition (used by the simulator before OPA export)
    rules: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Which edge or node this policy is attached to in the canvas
    # Stored as the React Flow element ID
    attached_to: Mapped[str | None] = mapped_column(String(100), nullable=True)

    canvas_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("canvases.id", ondelete="CASCADE"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    canvas: Mapped["Canvas"] = relationship(back_populates="policies")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Policy {self.name!r} type={self.policy_type}>"
