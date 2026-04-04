"""
SQLAlchemy base configuration and mixins for AiaxeMind models.

This module provides:
- DeclarativeBase: Modern SQLAlchemy 2.0 base class for all models
- TimestampMixin: Reusable mixin that adds created_at and updated_at fields
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    SQLAlchemy DeclarativeBase for all ORM models.
    """

    pass


class TimestampMixin:
    """
    Mixin that adds automatic timestamp tracking to models.

    Provides:
    - created_at: Timestamp when record was created (immutable)
    - updated_at: Timestamp when record was last modified (auto-updated)
    """

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
