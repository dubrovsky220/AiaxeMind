"""Unit tests for QdrantVectorStore."""

import uuid
from unittest.mock import Mock, patch

import pytest
from qdrant_client.models import PointStruct, ScoredPoint, VectorParams

from src.retrieval.exceptions import (
    CollectionNotFoundError,
    VectorStoreConnectionError,
    VectorStoreOperationError,
)
from src.retrieval.vector_store import QdrantVectorStore, SearchResult


class TestQdrantVectorStore:
    """Test suite for QdrantVectorStore."""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock QdrantClient for testing."""
        with patch("src.retrieval.vector_store.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock get_collections to return empty list (collection doesn't exist)
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            yield mock_client

    @pytest.fixture
    def vector_store(self, mock_qdrant_client):
        """Create QdrantVectorStore instance with mocked client."""
        return QdrantVectorStore(url="http://localhost:6333", collection_name="test_chunks")

    def test_initialization_default_params(self, mock_qdrant_client):
        """Test vector store initialization with default parameters."""
        with patch.dict("os.environ", {"QDRANT_URL": "http://test:6333"}):
            store = QdrantVectorStore()

            assert store.url == "http://test:6333"
            assert store.collection_name == "chunks"
            assert store.vector_size == 384

    def test_initialization_custom_params(self, mock_qdrant_client):
        """Test vector store initialization with custom parameters."""
        store = QdrantVectorStore(
            url="http://custom:6333", collection_name="custom_collection", vector_size=512
        )

        assert store.url == "http://custom:6333"
        assert store.collection_name == "custom_collection"
        assert store.vector_size == 512

    def test_initialization_connection_error(self):
        """Test initialization raises VectorStoreConnectionError on connection failure."""
        with patch("src.retrieval.vector_store.QdrantClient") as mock_client_class:
            mock_client_class.side_effect = Exception("Connection refused")

            with pytest.raises(VectorStoreConnectionError) as exc_info:
                QdrantVectorStore(url="http://localhost:6333")

            assert "Connection refused" in str(exc_info.value)
            assert exc_info.value.url == "http://localhost:6333"

    def test_ensure_collection_creates_new_collection(self, mock_qdrant_client):
        """Test collection is created if it doesn't exist."""
        # Mock get_collections to return empty list
        mock_collections = Mock()
        mock_collections.collections = []
        mock_qdrant_client.get_collections.return_value = mock_collections

        QdrantVectorStore(url="http://localhost:6333", collection_name="test_chunks")

        # Verify create_collection was called
        mock_qdrant_client.create_collection.assert_called_once()
        call_args = mock_qdrant_client.create_collection.call_args
        assert call_args.kwargs["collection_name"] == "test_chunks"
        assert isinstance(call_args.kwargs["vectors_config"], VectorParams)

    def test_ensure_collection_skips_if_exists(self, mock_qdrant_client):
        """Test collection creation is skipped if collection already exists."""
        # Mock get_collections to return existing collection
        mock_collection = Mock()
        mock_collection.name = "test_chunks"
        mock_collections = Mock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections

        QdrantVectorStore(url="http://localhost:6333", collection_name="test_chunks")

        # Verify create_collection was NOT called
        mock_qdrant_client.create_collection.assert_not_called()

    def test_upsert_chunks_success(self, vector_store, mock_qdrant_client):
        """Test successful batch upsert of chunks."""
        workspace_id = uuid.uuid4()
        document_id = uuid.uuid4()
        chunk_id = uuid.uuid4()

        chunks = [
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "workspace_id": workspace_id,
                "text": "Test chunk text",
                "page": 1,
                "section_title": "Introduction",
                "chunk_index": 0,
                "filename": "test.pdf",
            }
        ]
        embeddings = [[0.1] * 384]

        vector_store.upsert_chunks(chunks, embeddings)

        # Verify upsert was called
        mock_qdrant_client.upsert.assert_called_once()
        call_args = mock_qdrant_client.upsert.call_args
        assert call_args.kwargs["collection_name"] == "test_chunks"

        # Verify point structure
        points = call_args.kwargs["points"]
        assert len(points) == 1
        assert isinstance(points[0], PointStruct)
        assert points[0].id == str(chunk_id)
        assert points[0].vector == embeddings[0]
        assert points[0].payload["text"] == "Test chunk text"
        assert points[0].payload["workspace_id"] == str(workspace_id)

    def test_upsert_chunks_multiple(self, vector_store, mock_qdrant_client):
        """Test batch upsert with multiple chunks."""
        workspace_id = uuid.uuid4()
        document_id = uuid.uuid4()

        chunks = [
            {
                "chunk_id": uuid.uuid4(),
                "document_id": document_id,
                "workspace_id": workspace_id,
                "text": f"Chunk {i}",
                "page": i + 1,
                "section_title": f"Section {i}",
                "chunk_index": i,
                "filename": "test.pdf",
            }
            for i in range(3)
        ]
        embeddings = [[0.1 * i] * 384 for i in range(3)]

        vector_store.upsert_chunks(chunks, embeddings)

        # Verify all chunks were upserted
        call_args = mock_qdrant_client.upsert.call_args
        points = call_args.kwargs["points"]
        assert len(points) == 3

    def test_upsert_chunks_length_mismatch(self, vector_store):
        """Test upsert raises ValueError when chunks and embeddings have different lengths."""
        chunks = [{"chunk_id": uuid.uuid4()}]
        embeddings = [[0.1] * 384, [0.2] * 384]

        with pytest.raises(ValueError, match="must have same length"):
            vector_store.upsert_chunks(chunks, embeddings)

    def test_upsert_chunks_empty_list(self, vector_store, mock_qdrant_client):
        """Test upsert with empty list does nothing."""
        vector_store.upsert_chunks([], [])

        # Verify upsert was NOT called
        mock_qdrant_client.upsert.assert_not_called()

    def test_upsert_chunks_dimension_mismatch(self, vector_store):
        """Test upsert raises ValueError when embedding dimension is wrong."""
        chunks = [
            {
                "chunk_id": uuid.uuid4(),
                "document_id": uuid.uuid4(),
                "workspace_id": uuid.uuid4(),
                "text": "Test",
                "page": 1,
                "section_title": None,
                "chunk_index": 0,
                "filename": "test.pdf",
            }
        ]
        embeddings = [[0.1] * 512]  # Wrong dimension (should be 384)

        with pytest.raises(ValueError, match="Embedding dimension mismatch"):
            vector_store.upsert_chunks(chunks, embeddings)

    def test_upsert_chunks_operation_error(self, vector_store, mock_qdrant_client):
        """Test upsert raises VectorStoreOperationError on Qdrant failure."""
        mock_qdrant_client.upsert.side_effect = Exception("Qdrant error")

        chunks = [
            {
                "chunk_id": uuid.uuid4(),
                "document_id": uuid.uuid4(),
                "workspace_id": uuid.uuid4(),
                "text": "Test",
                "page": 1,
                "section_title": None,
                "chunk_index": 0,
                "filename": "test.pdf",
            }
        ]
        embeddings = [[0.1] * 384]

        with pytest.raises(VectorStoreOperationError) as exc_info:
            vector_store.upsert_chunks(chunks, embeddings)

        assert exc_info.value.operation == "upsert"
        assert "Qdrant error" in str(exc_info.value.original_error)

    def test_search_success(self, vector_store, mock_qdrant_client):
        """Test successful search with results."""
        workspace_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        document_id = uuid.uuid4()

        # Mock search results
        mock_hit = Mock(spec=ScoredPoint)
        mock_hit.score = 0.95
        mock_hit.payload = {
            "chunk_id": str(chunk_id),
            "document_id": str(document_id),
            "workspace_id": str(workspace_id),
            "text": "Test chunk",
            "page": 1,
            "section_title": "Introduction",
            "chunk_index": 0,
            "filename": "test.pdf",
        }
        mock_response = Mock()
        mock_response.points = [mock_hit]
        mock_qdrant_client.query_points.return_value = mock_response

        query_embedding = [0.1] * 384
        results = vector_store.search(query_embedding, workspace_id, limit=5)

        # Verify query_points was called with correct parameters
        mock_qdrant_client.query_points.assert_called_once()
        call_args = mock_qdrant_client.query_points.call_args
        assert call_args.kwargs["collection_name"] == "test_chunks"
        assert call_args.kwargs["query"] == query_embedding
        assert call_args.kwargs["limit"] == 5

        # Verify results
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].chunk_id == chunk_id
        assert results[0].score == 0.95
        assert results[0].text == "Test chunk"

    def test_search_with_score_threshold(self, vector_store, mock_qdrant_client):
        """Test search with score threshold filtering."""
        workspace_id = uuid.uuid4()
        mock_response = Mock()
        mock_response.points = []
        mock_qdrant_client.query_points.return_value = mock_response

        query_embedding = [0.1] * 384
        results = vector_store.search(query_embedding, workspace_id, limit=5, score_threshold=0.8)

        # Verify score_threshold was passed
        call_args = mock_qdrant_client.query_points.call_args
        assert call_args.kwargs["score_threshold"] == 0.8

        # Verify empty results
        assert results == []

    def test_search_workspace_filtering(self, vector_store, mock_qdrant_client):
        """Test search applies workspace filter."""
        workspace_id = uuid.uuid4()
        mock_response = Mock()
        mock_response.points = []
        mock_qdrant_client.query_points.return_value = mock_response

        query_embedding = [0.1] * 384
        vector_store.search(query_embedding, workspace_id)

        # Verify filter was applied
        call_args = mock_qdrant_client.query_points.call_args
        query_filter = call_args.kwargs["query_filter"]
        assert query_filter is not None
        # Filter should contain workspace_id condition
        assert len(query_filter.must) == 1

    def test_search_dimension_mismatch(self, vector_store):
        """Test search raises ValueError when query embedding dimension is wrong."""
        workspace_id = uuid.uuid4()
        query_embedding = [0.1] * 512  # Wrong dimension

        with pytest.raises(ValueError, match="Query embedding dimension mismatch"):
            vector_store.search(query_embedding, workspace_id)

    def test_search_collection_not_found(self, vector_store, mock_qdrant_client):
        """Test search raises CollectionNotFoundError when collection doesn't exist."""
        mock_qdrant_client.query_points.side_effect = Exception("Collection not found")

        workspace_id = uuid.uuid4()
        query_embedding = [0.1] * 384

        with pytest.raises(CollectionNotFoundError):
            vector_store.search(query_embedding, workspace_id)

    def test_search_operation_error(self, vector_store, mock_qdrant_client):
        """Test search raises VectorStoreOperationError on other failures."""
        mock_qdrant_client.query_points.side_effect = Exception("Network timeout")

        workspace_id = uuid.uuid4()
        query_embedding = [0.1] * 384

        with pytest.raises(VectorStoreOperationError) as exc_info:
            vector_store.search(query_embedding, workspace_id)

        assert exc_info.value.operation == "search"

    def test_delete_document(self, vector_store, mock_qdrant_client):
        """Test deleting all chunks for a document."""
        document_id = uuid.uuid4()

        # Mock delete response
        mock_result = Mock()
        mock_result.operation_id = 12345
        mock_qdrant_client.delete.return_value = mock_result

        vector_store.delete_document(document_id)

        # Verify delete was called
        mock_qdrant_client.delete.assert_called_once()
        call_args = mock_qdrant_client.delete.call_args
        assert call_args.kwargs["collection_name"] == "test_chunks"

        # Verify filter contains document_id
        points_selector = call_args.kwargs["points_selector"]
        assert points_selector is not None

    def test_delete_document_error(self, vector_store, mock_qdrant_client):
        """Test delete_document raises VectorStoreOperationError on failure."""
        mock_qdrant_client.delete.side_effect = Exception("Delete failed")

        document_id = uuid.uuid4()

        with pytest.raises(VectorStoreOperationError) as exc_info:
            vector_store.delete_document(document_id)

        assert exc_info.value.operation == "delete_document"

    def test_delete_workspace(self, vector_store, mock_qdrant_client):
        """Test deleting all chunks for a workspace."""
        workspace_id = uuid.uuid4()

        # Mock delete response
        mock_result = Mock()
        mock_result.operation_id = 12345
        mock_qdrant_client.delete.return_value = mock_result

        vector_store.delete_workspace(workspace_id)

        # Verify delete was called
        mock_qdrant_client.delete.assert_called_once()
        call_args = mock_qdrant_client.delete.call_args
        assert call_args.kwargs["collection_name"] == "test_chunks"

    def test_delete_workspace_error(self, vector_store, mock_qdrant_client):
        """Test delete_workspace raises VectorStoreOperationError on failure."""
        mock_qdrant_client.delete.side_effect = Exception("Delete failed")

        workspace_id = uuid.uuid4()

        with pytest.raises(VectorStoreOperationError) as exc_info:
            vector_store.delete_workspace(workspace_id)

        assert exc_info.value.operation == "delete_workspace"

    def test_get_collection_info_success(self, vector_store, mock_qdrant_client):
        """Test getting collection information."""
        # Mock collection info
        mock_info = Mock()
        mock_info.config.params.vectors.size = 384
        mock_info.config.params.vectors.distance.name = "COSINE"
        mock_info.points_count = 100
        mock_info.status.name = "GREEN"
        mock_qdrant_client.get_collection.return_value = mock_info

        info = vector_store.get_collection_info()

        # Verify info structure
        assert info["name"] == "test_chunks"
        assert info["vector_size"] == 384
        assert info["distance"] == "COSINE"
        assert info["points_count"] == 100
        assert info["status"] == "GREEN"

    def test_get_collection_info_not_found(self, vector_store, mock_qdrant_client):
        """Test get_collection_info raises CollectionNotFoundError."""
        mock_qdrant_client.get_collection.side_effect = Exception("Collection not found")

        with pytest.raises(CollectionNotFoundError):
            vector_store.get_collection_info()

    def test_get_collection_info_error(self, vector_store, mock_qdrant_client):
        """Test get_collection_info raises VectorStoreOperationError on other failures."""
        mock_qdrant_client.get_collection.side_effect = Exception("Network error")

        with pytest.raises(VectorStoreOperationError) as exc_info:
            vector_store.get_collection_info()

        assert exc_info.value.operation == "get_collection_info"


class TestSearchResult:
    """Test suite for SearchResult dataclass."""

    def test_search_result_creation(self):
        """Test SearchResult can be created with all fields."""
        chunk_id = uuid.uuid4()
        document_id = uuid.uuid4()
        workspace_id = uuid.uuid4()

        result = SearchResult(
            chunk_id=chunk_id,
            document_id=document_id,
            workspace_id=workspace_id,
            text="Test chunk text",
            score=0.95,
            page=1,
            section_title="Introduction",
            chunk_index=0,
            filename="test.pdf",
        )

        assert result.chunk_id == chunk_id
        assert result.document_id == document_id
        assert result.workspace_id == workspace_id
        assert result.text == "Test chunk text"
        assert result.score == 0.95
        assert result.page == 1
        assert result.section_title == "Introduction"
        assert result.chunk_index == 0
        assert result.filename == "test.pdf"

    def test_search_result_with_none_values(self):
        """Test SearchResult with optional None values."""
        result = SearchResult(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            text="Test",
            score=0.8,
            page=None,
            section_title=None,
            chunk_index=0,
            filename="test.pdf",
        )

        assert result.page is None
        assert result.section_title is None
