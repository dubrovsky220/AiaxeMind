"""
Retrieval module for AiaxeMind RAG pipeline.

This module provides vector storage and retrieval functionality using Qdrant,
with support for workspace isolation, similarity search, and citation generation.

Main Components:
- QdrantVectorStore: Vector database client for storing and searching embeddings
- SearchResult: Structured search result with metadata for citations
- Custom exceptions: Specific error types for retrieval operations

Usage:
    from src.retrieval import QdrantVectorStore, SearchResult

    # Initialize vector store
    store = QdrantVectorStore()

    # Upsert chunks
    store.upsert_chunks(chunks, embeddings)

    # Search
    results = store.search(query_embedding, workspace_id)
"""

from src.retrieval.exceptions import (
    CollectionNotFoundError,
    RetrievalError,
    VectorStoreConnectionError,
    VectorStoreOperationError,
)
from src.retrieval.vector_store import QdrantVectorStore, SearchResult

__all__ = [
    # Main classes
    "QdrantVectorStore",
    "SearchResult",
    # Exceptions
    "RetrievalError",
    "VectorStoreConnectionError",
    "CollectionNotFoundError",
    "VectorStoreOperationError",
]
