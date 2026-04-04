"""
Chunk model for AiaxeMind.

Represents document fragments created during chunking for RAG retrieval.
"""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class Chunk(Base, TimestampMixin):
    """
    Chunk model for document fragments.

    Stores text chunks extracted from documents, with metadata for retrieval.
    """

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # Chunk number in the document
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="chunks")

    # Indexes
    __table_args__ = (Index("ix_chunks_document_id", "document_id"),)
