"""
Template model — shared policy templates in the community hub.

Fork mechanics: forking creates a deep copy with a reference back to
the original template_id. fork_count on the original is incremented.
This is eventually consistent — we don't need transactions for a counter.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list)

    # Serialized canvas state (nodes + edges + policies)
    canvas_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    policies_data: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    # Fork tracking
    forked_from: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    fork_count: Mapped[int] = mapped_column(Integer, default=0)

    # Visibility: "public", "unlisted"
    visibility: Mapped[str] = mapped_column(
        String(20), default="public", nullable=False
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    author: Mapped["User"] = relationship(back_populates="templates")  # noqa: F821
    forks: Mapped[list["Template"]] = relationship(
        back_populates="parent",
        cascade="all",
    )
    parent: Mapped["Template | None"] = relationship(
        back_populates="forks",
        remote_side="Template.id",
    )

    def __repr__(self) -> str:
        return f"<Template {self.name!r} forks={self.fork_count}>"
