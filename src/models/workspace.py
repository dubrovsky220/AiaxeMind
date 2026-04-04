"""
Workspace model for AiaxeMind.

Represents a multi-tenant workspace where users organize documents and conversations.
"""

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class Workspace(Base, TimestampMixin):
    """
    Workspace model for multi-tenancy.

    Each workspace is an isolated container for documents and conversations.
    """

    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    documents: Mapped[list["Document"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
