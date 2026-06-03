"""
Canvas model — the core workspace where ZT architectures are designed.

Design choices:
- nodes/edges stored as JSONB for flexibility. React Flow's data model
  changes frequently; a rigid relational schema would fight the frontend.
- version field enables optimistic concurrency control. The API rejects
  updates where the client's version doesn't match the DB version.
- snapshot_data is the full serialized state for undo/redo support.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Canvas(Base):
    __tablename__ = "canvases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # React Flow serialized state
    nodes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    edges: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    viewport: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=lambda: {"x": 0, "y": 0, "zoom": 1}
    )

    # Optimistic concurrency — reject stale writes
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Visibility: "private", "team", "public"
    visibility: Mapped[str] = mapped_column(
        String(20), default="private", nullable=False
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="canvases")  # noqa: F821
    policies: Mapped[list["Policy"]] = relationship(  # noqa: F821
        back_populates="canvas", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Canvas {self.title!r} v{self.version}>"
