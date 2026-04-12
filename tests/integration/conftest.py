"""Pytest configuration for integration tests."""

import sys
from pathlib import Path

import pytest

# Add services/embedding to Python path for embedding service tests
embedding_service_path = Path(__file__).parent.parent.parent / "services" / "embedding"
if embedding_service_path.exists():
    sys.path.insert(0, str(embedding_service_path))


@pytest.fixture(scope="session")
def embedding_model():
    """Load embedding model once for all tests in the session."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("intfloat/multilingual-e5-small", device="cpu")
    return model
