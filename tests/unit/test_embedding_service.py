"""Unit tests for Embedding Service endpoints."""

import pytest
from fastapi.testclient import TestClient
from sentence_transformers import SentenceTransformer

from services.embedding.app import app


class TestEmbeddingServiceEndpoints:
    """Test suite for Embedding Service HTTP endpoints."""

    @pytest.fixture
    def client(self, embedding_model: SentenceTransformer) -> TestClient:
        """Create FastAPI test client with loaded model."""
        # Inject the model into app state before creating client
        app.state.model = embedding_model
        return TestClient(app)

    def test_health_endpoint_returns_healthy(self, client: TestClient) -> None:
        """Test /health endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "model" in data
        assert "device" in data

    def test_root_endpoint_returns_metadata(self, client: TestClient) -> None:
        """Test / endpoint returns service metadata."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Embedding Service"
        assert "model" in data
        assert "device" in data
        assert "default_batch_size" in data
        assert "endpoints" in data
        assert data["endpoints"]["health"] == "/health"
        assert data["endpoints"]["embed"] == "/embed"

    def test_embed_single_text(self, client: TestClient) -> None:
        """Test /embed with single text returns valid embedding."""
        payload = {"texts": ["Hello world"]}
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "embeddings" in data
        assert "token_counts" in data
        assert "model" in data
        assert "dimension" in data

        assert len(data["embeddings"]) == 1
        assert len(data["token_counts"]) == 1
        assert isinstance(data["embeddings"][0], list)
        assert len(data["embeddings"][0]) == data["dimension"]
        assert all(isinstance(x, float) for x in data["embeddings"][0])

    def test_embed_multiple_texts(self, client: TestClient) -> None:
        """Test /embed with multiple texts returns correct number of embeddings."""
        texts = [
            "Machine learning is a subset of AI",
            "Deep learning uses neural networks",
            "Natural language processing handles text",
        ]
        payload = {"texts": texts}
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data["embeddings"]) == len(texts)
        assert len(data["token_counts"]) == len(texts)
        assert all(len(emb) == data["dimension"] for emb in data["embeddings"])

    def test_embed_with_query_prefix(self, client: TestClient) -> None:
        """Test /embed with query prefix type."""
        payload = {
            "texts": ["What is machine learning?"],
            "prefix_type": "query",
        }
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data["embeddings"]) == 1

    def test_embed_with_passage_prefix(self, client: TestClient) -> None:
        """Test /embed with passage prefix type."""
        payload = {
            "texts": ["Machine learning is a field of AI"],
            "prefix_type": "passage",
        }
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data["embeddings"]) == 1

    def test_embed_with_custom_batch_size(self, client: TestClient) -> None:
        """Test /embed with custom batch_size parameter."""
        texts = ["Text " + str(i) for i in range(10)]
        payload = {
            "texts": texts,
            "batch_size": 5,
        }
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data["embeddings"]) == len(texts)

    def test_embed_empty_texts_returns_400(self, client: TestClient) -> None:
        """Test /embed with empty texts list returns 400."""
        payload: dict[str, list[str]] = {"texts": []}
        response = client.post("/embed", json=payload)

        assert response.status_code == 400
        assert "No texts provided" in response.json()["detail"]

    def test_embed_too_many_texts_returns_400(self, client: TestClient) -> None:
        """Test /embed with too many texts returns 400."""
        payload = {"texts": ["text"] * 101}  # MAX_TEXTS_PER_REQUEST = 100
        response = client.post("/embed", json=payload)

        assert response.status_code == 400
        assert "Maximum" in response.json()["detail"]

    def test_embed_text_too_long_returns_400(self, client: TestClient) -> None:
        """Test /embed with text exceeding MAX_TEXT_LENGTH returns 400."""
        long_text = "a" * 8001  # MAX_TEXT_LENGTH = 8000
        payload = {"texts": [long_text]}
        response = client.post("/embed", json=payload)

        assert response.status_code == 400
        assert "exceeds maximum length" in response.json()["detail"]

    def test_embed_invalid_prefix_type_returns_422(self, client: TestClient) -> None:
        """Test /embed with invalid prefix_type returns 422 validation error."""
        payload = {
            "texts": ["Hello"],
            "prefix_type": "invalid",
        }
        response = client.post("/embed", json=payload)

        assert response.status_code == 422

    def test_embed_invalid_batch_size_returns_422(self, client: TestClient) -> None:
        """Test /embed with invalid batch_size returns 422 validation error."""
        payload = {
            "texts": ["Hello"],
            "batch_size": 0,  # must be >= 1
        }
        response = client.post("/embed", json=payload)

        assert response.status_code == 422

    def test_embed_batch_size_too_large_returns_422(self, client: TestClient) -> None:
        """Test /embed with batch_size > 256 returns 422 validation error."""
        payload = {
            "texts": ["Hello"],
            "batch_size": 300,  # max is 256
        }
        response = client.post("/embed", json=payload)

        assert response.status_code == 422

    def test_embed_token_counts_are_positive(self, client: TestClient) -> None:
        """Test /embed returns positive token counts."""
        payload = {"texts": ["This is a test sentence with multiple words"]}
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert all(count > 0 for count in data["token_counts"])

    def test_embed_different_texts_produce_different_embeddings(
        self, client: TestClient
    ) -> None:
        """Test that different texts produce different embeddings."""
        payload = {
            "texts": [
                "The cat sat on the mat",
                "The dog ran in the park",
            ]
        }
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        emb1, emb2 = data["embeddings"]
        assert emb1 != emb2

    def test_embed_same_text_produces_same_embedding(self, client: TestClient) -> None:
        """Test that identical texts produce identical embeddings."""
        text = "Reproducibility test"
        payload = {"texts": [text, text]}
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        emb1, emb2 = data["embeddings"]
        assert emb1 == emb2

    def test_embed_prefix_changes_embedding(self, client: TestClient) -> None:
        """Test that prefix_type changes the embedding vector."""
        text = "What is artificial intelligence?"

        # Without prefix
        response1 = client.post("/embed", json={"texts": [text]})
        emb_no_prefix = response1.json()["embeddings"][0]

        # With query prefix
        response2 = client.post(
            "/embed", json={"texts": [text], "prefix_type": "query"}
        )
        emb_with_prefix = response2.json()["embeddings"][0]

        assert emb_no_prefix != emb_with_prefix

    def test_embed_response_structure(self, client: TestClient) -> None:
        """Test /embed response has correct structure."""
        payload = {"texts": ["Test"]}
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Check all required fields exist
        assert "embeddings" in data
        assert "token_counts" in data
        assert "model" in data
        assert "dimension" in data

        # Check types
        assert isinstance(data["embeddings"], list)
        assert isinstance(data["token_counts"], list)
        assert isinstance(data["model"], str)
        assert isinstance(data["dimension"], int)

    def test_embed_dimension_consistency(self, client: TestClient) -> None:
        """Test that all embeddings have the same dimension."""
        texts = ["Text " + str(i) for i in range(5)]
        payload = {"texts": texts}
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        dimensions = [len(emb) for emb in data["embeddings"]]
        assert len(set(dimensions)) == 1  # all same
        assert dimensions[0] == data["dimension"]
