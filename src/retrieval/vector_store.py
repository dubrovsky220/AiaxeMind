"""
Qdrant vector store integration for AiaxeMind.

This module provides vector storage and retrieval operations with workspace isolation
for the RAG (Retrieval-Augmented Generation) pipeline.

Key Features:
- Batch upsert of document chunk embeddings with metadata
- Similarity search with workspace-level filtering (multi-tenancy)
- Optional score threshold filtering for relevance control
- Automatic collection creation and management
- Comprehensive error handling and logging

Usage:
    from src.retrieval.vector_store import QdrantVectorStore, SearchResult

    # Initialize vector store
    store = QdrantVectorStore(url="http://localhost:6333")

    # Upsert chunks with embeddings
    chunks = [
        {
            "chunk_id": uuid.uuid4(),
            "document_id": uuid.uuid4(),
            "workspace_id": uuid.uuid4(),
            "text": "Chunk text...",
            "page": 1,
            "section_title": "Introduction",
            "chunk_index": 0,
            "filename": "document.pdf"
        }
    ]
    embeddings = [[0.1, 0.2, ...], ...]  # 384-dimensional vectors
    store.upsert_chunks(chunks, embeddings)

    # Search for similar chunks
    query_embedding = [0.15, 0.25, ...]
    results = store.search(
        query_embedding=query_embedding,
        workspace_id=workspace_id,
        limit=5,
        score_threshold=0.7
    )

    for result in results:
        print(f"[{result.filename}, Page {result.page}]: {result.text[:100]}...")
"""

import os
import uuid
from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from src.core.logging_config import get_logger
from src.retrieval.exceptions import (
    CollectionNotFoundError,
    VectorStoreConnectionError,
    VectorStoreOperationError,
)

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """
    Single search result with chunk metadata and similarity score.

    This dataclass encapsulates all information needed to display search results
    and generate citations in the RAG pipeline.

    Attributes:
        chunk_id: Unique identifier for the chunk
        document_id: ID of the source document
        workspace_id: ID of the workspace (for multi-tenancy)
        text: Full text content of the chunk
        score: Similarity score (0.0 to 1.0 for cosine similarity)
        page: Page number in source document (None if not available)
        section_title: Section heading associated with chunk (None if not available)
        chunk_index: Sequential position of chunk in document
        filename: Original filename of source document
    """

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    workspace_id: uuid.UUID
    text: str
    score: float
    page: int | None
    section_title: str | None
    chunk_index: int
    filename: str


class QdrantVectorStore:
    """
    Vector store implementation using Qdrant for document chunk embeddings.

    This class manages the storage and retrieval of document chunk embeddings
    in Qdrant, with support for workspace isolation, batch operations, and
    flexible search parameters.

    Architecture:
    - Single collection strategy: All chunks stored in one collection
    - Workspace isolation: Filtering via workspace_id in payload
    - Vector dimension: 384 (for multilingual-e5-small embeddings)
    - Distance metric: Cosine similarity

    The vector store automatically creates the collection on first use and
    handles all Qdrant client operations with comprehensive error handling.

    Example:
        store = QdrantVectorStore(url="http://localhost:6333")

        # Upsert chunks
        store.upsert_chunks(chunks, embeddings)

        # Search with workspace filtering
        results = store.search(query_embedding, workspace_id, limit=5)
    """

    def __init__(
        self,
        url: str | None = None,
        collection_name: str = "chunks",
        vector_size: int = 384,
    ) -> None:
        """
        Initialize Qdrant vector store client.

        Args:
            url: Qdrant server URL (defaults to QDRANT_URL env var or http://localhost:6333)
            collection_name: Name of the Qdrant collection (default: "chunks")
            vector_size: Dimension of embedding vectors (default: 384 for multilingual-e5-small)

        Raises:
            VectorStoreConnectionError: If connection to Qdrant fails
        """
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection_name = collection_name
        self.vector_size = vector_size

        try:
            self.client = QdrantClient(url=self.url)
            logger.info(
                "QdrantVectorStore initialized",
                extra={
                    "url": self.url,
                    "collection": self.collection_name,
                    "vector_size": self.vector_size,
                },
            )
        except Exception as e:
            logger.error(
                "Failed to initialize Qdrant client",
                extra={"url": self.url, "error": str(e)},
            )
            raise VectorStoreConnectionError(
                url=self.url or "http://localhost:6333", original_error=e
            )

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """
        Create collection if it doesn't exist.

        This method is called during initialization to ensure the collection
        is ready for operations. It's idempotent - safe to call multiple times.

        Raises:
            VectorStoreOperationError: If collection creation fails
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name in collection_names:
                logger.info(
                    "Collection already exists",
                    extra={"collection": self.collection_name},
                )
                return

            # Create collection with cosine distance metric
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

            logger.info(
                "Collection created successfully",
                extra={
                    "collection": self.collection_name,
                    "vector_size": self.vector_size,
                    "distance": "COSINE",
                },
            )

        except Exception as e:
            logger.error(
                "Failed to ensure collection exists",
                extra={"collection": self.collection_name, "error": str(e)},
            )
            raise VectorStoreOperationError(
                operation="create_collection",
                details=f"Failed to create collection '{self.collection_name}'",
                original_error=e,
            )

    def upsert_chunks(self, chunks: list[dict[str, Any]], embeddings: list[list[float]]) -> None:
        """
        Upsert chunk embeddings with metadata to Qdrant.

        This method performs a batch upsert operation, storing embeddings along
        with all metadata needed for retrieval and citation generation.

        Args:
            chunks: List of chunk dictionaries with metadata. Each dict must contain:
                - chunk_id (uuid.UUID): Unique chunk identifier
                - document_id (uuid.UUID): Source document ID
                - workspace_id (uuid.UUID): Workspace ID for filtering
                - text (str): Full chunk text
                - page (int | None): Page number
                - section_title (str | None): Section heading
                - chunk_index (int): Position in document
                - filename (str): Source filename
            embeddings: List of embedding vectors (same length as chunks)

        Raises:
            ValueError: If chunks and embeddings have different lengths
            VectorStoreOperationError: If upsert operation fails

        Example:
            chunks = [
                {
                    "chunk_id": uuid.uuid4(),
                    "document_id": doc_id,
                    "workspace_id": ws_id,
                    "text": "Introduction to machine learning...",
                    "page": 1,
                    "section_title": "Chapter 1",
                    "chunk_index": 0,
                    "filename": "ml_book.pdf"
                }
            ]
            embeddings = [[0.1, 0.2, ...]]  # 384-dimensional
            store.upsert_chunks(chunks, embeddings)
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks and embeddings must have same length: {len(chunks)} != {len(embeddings)}"
            )

        if not chunks:
            logger.warning("Attempted to upsert empty chunk list, skipping")
            return

        try:
            # Build points for batch upsert
            points = []
            for chunk, embedding in zip(chunks, embeddings):
                # Validate embedding dimension
                if len(embedding) != self.vector_size:
                    raise ValueError(
                        f"Embedding dimension mismatch: expected {self.vector_size}, got {len(embedding)}"
                    )

                point = PointStruct(
                    id=str(chunk["chunk_id"]),  # Use chunk_id as Qdrant point ID
                    vector=embedding,
                    payload={
                        "chunk_id": str(chunk["chunk_id"]),
                        "document_id": str(chunk["document_id"]),
                        "workspace_id": str(chunk["workspace_id"]),
                        "text": chunk["text"],
                        "page": chunk["page"],
                        "section_title": chunk["section_title"],
                        "chunk_index": chunk["chunk_index"],
                        "filename": chunk["filename"],
                    },
                )
                points.append(point)

            # Perform batch upsert
            self.client.upsert(collection_name=self.collection_name, points=points)

            logger.info(
                "Successfully upserted chunks to Qdrant",
                extra={
                    "collection": self.collection_name,
                    "chunk_count": len(chunks),
                    "workspace_id": str(chunks[0]["workspace_id"]),
                    "document_id": str(chunks[0]["document_id"]),
                },
            )

        except ValueError as e:
            # Re-raise validation errors as-is
            logger.error("Validation error during upsert", extra={"error": str(e)})
            raise

        except Exception as e:
            logger.error(
                "Failed to upsert chunks to Qdrant",
                extra={
                    "collection": self.collection_name,
                    "chunk_count": len(chunks),
                    "error": str(e),
                },
            )
            raise VectorStoreOperationError(
                operation="upsert",
                details=f"Failed to upsert {len(chunks)} chunks",
                original_error=e,
            )

    def search(
        self,
        query_embedding: list[float],
        workspace_id: uuid.UUID,
        limit: int = 5,
        score_threshold: float | None = None,
    ) -> list[SearchResult]:
        """
        Search for similar chunks within a workspace.

        Performs similarity search using cosine distance, with mandatory workspace
        filtering for multi-tenancy isolation. Optionally filters results by
        minimum similarity score.

        Args:
            query_embedding: Query vector (must match vector_size dimension)
            workspace_id: Workspace ID to filter results (ensures multi-tenancy)
            limit: Maximum number of results to return (default: 5)
            score_threshold: Minimum similarity score (0.0-1.0). If None, returns
                top-k results regardless of score. If set, only returns results
                with score >= threshold.

        Returns:
            List of SearchResult objects, sorted by similarity score (highest first).
            Returns empty list if no results match the criteria.

        Raises:
            ValueError: If query_embedding dimension doesn't match vector_size
            CollectionNotFoundError: If collection doesn't exist
            VectorStoreOperationError: If search operation fails

        Example:
            # Search with score threshold
            results = store.search(
                query_embedding=[0.1, 0.2, ...],
                workspace_id=workspace_id,
                limit=5,
                score_threshold=0.7
            )

            if not results:
                print("No relevant documents found")
            else:
                for result in results:
                    print(f"Score: {result.score:.3f} - {result.text[:100]}")
        """
        # Validate query embedding dimension
        if len(query_embedding) != self.vector_size:
            raise ValueError(
                f"Query embedding dimension mismatch: expected {self.vector_size}, got {len(query_embedding)}"
            )

        try:
            # Build workspace filter
            workspace_filter = Filter(
                must=[FieldCondition(key="workspace_id", match=MatchValue(value=str(workspace_id)))]
            )

            # Perform search using query_points
            search_results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=workspace_filter,
                limit=limit,
                score_threshold=score_threshold,
            ).points

            # Convert to SearchResult objects
            results = []
            for hit in search_results:
                payload = hit.payload
                if payload is None:
                    continue
                result = SearchResult(
                    chunk_id=uuid.UUID(payload["chunk_id"]),
                    document_id=uuid.UUID(payload["document_id"]),
                    workspace_id=uuid.UUID(payload["workspace_id"]),
                    text=payload["text"],
                    score=hit.score,
                    page=payload["page"],
                    section_title=payload["section_title"],
                    chunk_index=payload["chunk_index"],
                    filename=payload["filename"],
                )
                results.append(result)

            logger.info(
                "Search completed successfully",
                extra={
                    "collection": self.collection_name,
                    "workspace_id": str(workspace_id),
                    "limit": limit,
                    "score_threshold": score_threshold,
                    "result_count": len(results),
                },
            )

            return results

        except Exception as e:
            # Check if it's a collection not found error
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                logger.error(
                    "Collection not found during search",
                    extra={"collection": self.collection_name, "error": str(e)},
                )
                raise CollectionNotFoundError(collection_name=self.collection_name)

            logger.error(
                "Search operation failed",
                extra={
                    "collection": self.collection_name,
                    "workspace_id": str(workspace_id),
                    "limit": limit,
                    "error": str(e),
                },
            )
            raise VectorStoreOperationError(
                operation="search",
                details=f"Failed to search in workspace {workspace_id}",
                original_error=e,
            )

    def delete_document(self, document_id: uuid.UUID) -> int:
        """
        Delete all chunks belonging to a document.

        This is useful when a document is deleted from the system and its
        embeddings should be removed from the vector store.

        Args:
            document_id: ID of the document whose chunks should be deleted

        Returns:
            Number of chunks deleted

        Raises:
            VectorStoreOperationError: If delete operation fails

        Example:
            deleted_count = store.delete_document(document_id)
            print(f"Deleted {deleted_count} chunks")
        """
        try:
            # Delete points with matching document_id
            delete_filter = Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))]
            )

            result = self.client.delete(
                collection_name=self.collection_name, points_selector=delete_filter
            )

            # Qdrant returns operation_id, not count, so we log the operation
            logger.info(
                "Document chunks deleted from Qdrant",
                extra={
                    "collection": self.collection_name,
                    "document_id": str(document_id),
                    "operation_id": result.operation_id
                    if hasattr(result, "operation_id")
                    else None,
                },
            )

            # Return 0 as we can't get exact count without additional query
            return 0

        except Exception as e:
            logger.error(
                "Failed to delete document chunks",
                extra={
                    "collection": self.collection_name,
                    "document_id": str(document_id),
                    "error": str(e),
                },
            )
            raise VectorStoreOperationError(
                operation="delete_document",
                details=f"Failed to delete chunks for document {document_id}",
                original_error=e,
            )

    def delete_workspace(self, workspace_id: uuid.UUID) -> int:
        """
        Delete all chunks belonging to a workspace.

        This is useful when a workspace is deleted and all its data should
        be removed from the vector store.

        Args:
            workspace_id: ID of the workspace whose chunks should be deleted

        Returns:
            Number of chunks deleted

        Raises:
            VectorStoreOperationError: If delete operation fails

        Example:
            deleted_count = store.delete_workspace(workspace_id)
            print(f"Deleted {deleted_count} chunks from workspace")
        """
        try:
            # Delete points with matching workspace_id
            delete_filter = Filter(
                must=[FieldCondition(key="workspace_id", match=MatchValue(value=str(workspace_id)))]
            )

            result = self.client.delete(
                collection_name=self.collection_name, points_selector=delete_filter
            )

            logger.info(
                "Workspace chunks deleted from Qdrant",
                extra={
                    "collection": self.collection_name,
                    "workspace_id": str(workspace_id),
                    "operation_id": result.operation_id
                    if hasattr(result, "operation_id")
                    else None,
                },
            )

            return 0

        except Exception as e:
            logger.error(
                "Failed to delete workspace chunks",
                extra={
                    "collection": self.collection_name,
                    "workspace_id": str(workspace_id),
                    "error": str(e),
                },
            )
            raise VectorStoreOperationError(
                operation="delete_workspace",
                details=f"Failed to delete chunks for workspace {workspace_id}",
                original_error=e,
            )

    def get_collection_info(self) -> dict[str, Any]:
        """
        Get collection statistics and configuration.

        Useful for debugging, monitoring, and verifying collection state.

        Returns:
            Dictionary with collection information:
                - name: Collection name
                - vector_size: Dimension of vectors
                - distance: Distance metric used
                - points_count: Number of points in collection
                - status: Collection status

        Raises:
            CollectionNotFoundError: If collection doesn't exist
            VectorStoreOperationError: If operation fails

        Example:
            info = store.get_collection_info()
            print(f"Collection has {info['points_count']} chunks")
        """
        try:
            collection_info = self.client.get_collection(collection_name=self.collection_name)

            # Handle both single vector and named vectors config
            vectors_config = collection_info.config.params.vectors
            vector_params: VectorParams
            if isinstance(vectors_config, dict):
                # Named vectors - use first vector config
                first_vector = next(iter(vectors_config.values()))
                if first_vector is None:
                    raise VectorStoreOperationError(
                        operation="get_collection_info",
                        details="Vector configuration is missing",
                    )
                vector_params = first_vector
            else:
                # Single vector config
                if vectors_config is None:
                    raise VectorStoreOperationError(
                        operation="get_collection_info",
                        details="Vector configuration is missing",
                    )
                vector_params = vectors_config

            info = {
                "name": self.collection_name,
                "vector_size": vector_params.size,
                "distance": vector_params.distance.name,
                "points_count": collection_info.points_count,
                "status": collection_info.status.name,
            }

            logger.info(
                "Retrieved collection info",
                extra={"collection": self.collection_name, "points_count": info["points_count"]},
            )

            return info

        except Exception as e:
            if "not found" in str(e).lower():
                raise CollectionNotFoundError(collection_name=self.collection_name)

            logger.error(
                "Failed to get collection info",
                extra={"collection": self.collection_name, "error": str(e)},
            )
            raise VectorStoreOperationError(
                operation="get_collection_info",
                details=f"Failed to get info for collection '{self.collection_name}'",
                original_error=e,
            )


def main() -> None:
    """
    Manual test script for QdrantVectorStore.

    Usage:
        # Start Qdrant first
        docker compose up qdrant -d

        # Run test
        uv run python -m src.retrieval.vector_store

    This script tests:
    - Collection creation
    - Batch upsert
    - Search with workspace filtering
    - Search with score threshold
    - Delete operations
    """
    import time

    from src.core.logging_config import setup_logging

    setup_logging(level="INFO")

    print("\n" + "=" * 80)
    print("QDRANT VECTOR STORE MANUAL TEST")
    print("=" * 80 + "\n")

    # Initialize vector store
    print("Step 1: Initializing vector store...")
    store = QdrantVectorStore(url="http://localhost:6333")
    print("✓ Vector store initialized\n")

    # Get collection info
    print("Step 2: Getting collection info...")
    info = store.get_collection_info()
    print(f"✓ Collection: {info['name']}")
    print(f"  - Vector size: {info['vector_size']}")
    print(f"  - Distance: {info['distance']}")
    print(f"  - Points: {info['points_count']}")
    print(f"  - Status: {info['status']}\n")

    # Create test data
    print("Step 3: Creating test data...")
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    chunks = [
        {
            "chunk_id": uuid.uuid4(),
            "document_id": document_id,
            "workspace_id": workspace_id,
            "text": "Machine learning is a subset of artificial intelligence.",
            "page": 1,
            "section_title": "Introduction",
            "chunk_index": 0,
            "filename": "ml_intro.pdf",
        },
        {
            "chunk_id": uuid.uuid4(),
            "document_id": document_id,
            "workspace_id": workspace_id,
            "text": "Deep learning uses neural networks with multiple layers.",
            "page": 2,
            "section_title": "Deep Learning",
            "chunk_index": 1,
            "filename": "ml_intro.pdf",
        },
        {
            "chunk_id": uuid.uuid4(),
            "document_id": document_id,
            "workspace_id": workspace_id,
            "text": "Natural language processing enables computers to understand text.",
            "page": 3,
            "section_title": "NLP",
            "chunk_index": 2,
            "filename": "ml_intro.pdf",
        },
    ]

    # Generate dummy embeddings (384 dimensions)
    embeddings = [[0.1 * i] * 384 for i in range(len(chunks))]
    print(f"✓ Created {len(chunks)} test chunks\n")

    # Upsert chunks
    print("Step 4: Upserting chunks...")
    start = time.time()
    store.upsert_chunks(chunks, embeddings)
    elapsed = time.time() - start
    print(f"✓ Upserted {len(chunks)} chunks in {elapsed:.3f}s\n")

    # Search without threshold
    print("Step 5: Searching without score threshold...")
    query_embedding = [0.15] * 384
    results = store.search(query_embedding=query_embedding, workspace_id=workspace_id, limit=5)
    print(f"✓ Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. Score: {result.score:.4f} | Page: {result.page} | {result.text[:60]}...")
    print()

    # Search with threshold
    print("Step 6: Searching with score threshold (0.9)...")
    results_filtered = store.search(
        query_embedding=query_embedding,
        workspace_id=workspace_id,
        limit=5,
        score_threshold=0.9,
    )
    print(f"✓ Found {len(results_filtered)} results above threshold\n")

    # Test workspace isolation
    print("Step 7: Testing workspace isolation...")
    other_workspace_id = uuid.uuid4()
    results_other = store.search(
        query_embedding=query_embedding, workspace_id=other_workspace_id, limit=5
    )
    print(f"✓ Found {len(results_other)} results in different workspace (should be 0)\n")

    # Delete document
    print("Step 8: Deleting document...")
    store.delete_document(document_id)
    print(f"✓ Deleted chunks for document {document_id}\n")

    # Verify deletion
    print("Step 9: Verifying deletion...")
    results_after_delete = store.search(
        query_embedding=query_embedding, workspace_id=workspace_id, limit=5
    )
    print(f"✓ Found {len(results_after_delete)} results after deletion (should be 0)\n")

    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
