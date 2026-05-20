"""
SQLAlchemy declarative base and model registry.

All models import Base from here. The metadata object is used by
Alembic for migration autogeneration.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Import all models so Alembic can discover them via Base.metadata
from app.models.user import User  # noqa: E402, F401
from app.models.canvas import Canvas  # noqa: E402, F401
from app.models.policy import Policy  # noqa: E402, F401
from app.models.template import Template  # noqa: E402, F401

__all__ = ["Base", "User", "Canvas", "Policy", "Template"]
