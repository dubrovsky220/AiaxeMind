"""
Conversation model for AiaxeMind.

Represents chat sessions where students interact with the Socratic mentor.
"""

import uuid

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """
    Conversation model for chat sessions.

    Stores conversation metadata and relationships to messages.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (Index("ix_conversations_workspace_id", "workspace_id"),)
