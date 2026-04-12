"""Integration tests for full document processing pipeline with embedding service.

Tests the complete flow: document parsing → chunking → embedding generation.
Includes performance measurements for latency analysis.
"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sentence_transformers import SentenceTransformer

from services.embedding.app import app
from src.ingestion.chunking.chunker import DocumentChunker
from src.ingestion.parsers.factory import ParserFactory

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "documents"


class TestEmbeddingPipeline:
    """Integration tests for document → chunks → embeddings pipeline."""

    @pytest.fixture
    def client(self, embedding_model: SentenceTransformer) -> TestClient:
        """Create FastAPI test client for embedding service."""
        app.state.model = embedding_model
        return TestClient(app)

    @pytest.fixture
    def parser_factory(self) -> ParserFactory:
        """Create parser factory."""
        return ParserFactory()

    @pytest.fixture
    def chunker(self) -> DocumentChunker:
        """Create document chunker with default settings."""
        return DocumentChunker(chunk_size=512, chunk_overlap=64)

    def test_pdf_to_embeddings_pipeline(
        self,
        client: TestClient,
        parser_factory: ParserFactory,
        chunker: DocumentChunker,
    ) -> None:
        """Test complete pipeline: PDF → parse → chunk → embed."""
        file_path = FIXTURES_DIR / "simple.pdf"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        # Step 1: Parse document
        parsed_doc = parser_factory.parse(file_path)
        assert parsed_doc.text is not None
        assert len(parsed_doc.text) > 0

        # Step 2: Chunk document
        chunks = chunker.chunk(parsed_doc)
        assert len(chunks) > 0

        # Step 3: Generate embeddings
        chunk_texts = [chunk.text for chunk in chunks]
        payload = {"texts": chunk_texts, "prefix_type": "passage"}
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data["embeddings"]) == len(chunks)
        assert all(len(emb) == data["dimension"] for emb in data["embeddings"])

    def test_docx_to_embeddings_pipeline(
        self,
        client: TestClient,
        parser_factory: ParserFactory,
        chunker: DocumentChunker,
    ) -> None:
        """Test complete pipeline: DOCX → parse → chunk → embed."""
        file_path = FIXTURES_DIR / "simple.docx"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        # Step 1: Parse document
        parsed_doc = parser_factory.parse(file_path)
        assert parsed_doc.text is not None

        # Step 2: Chunk document
        chunks = chunker.chunk(parsed_doc)
        assert len(chunks) > 0

        # Step 3: Generate embeddings
        chunk_texts = [chunk.text for chunk in chunks]
        payload = {"texts": chunk_texts, "prefix_type": "passage"}
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data["embeddings"]) == len(chunks)

    def test_multi_page_pdf_pipeline_with_metadata(
        self,
        client: TestClient,
        parser_factory: ParserFactory,
        chunker: DocumentChunker,
    ) -> None:
        """Test pipeline preserves chunk metadata (page, section)."""
        file_path = FIXTURES_DIR / "pdf1.pdf"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        # Parse and chunk
        parsed_doc = parser_factory.parse(file_path)
        chunks = chunker.chunk(parsed_doc)

        # Verify metadata is preserved
        assert all(chunk.page is not None for chunk in chunks)
        assert all(chunk.chunk_index >= 0 for chunk in chunks)

        # Generate embeddings (limit to first 50 chunks to avoid MAX_TEXTS_PER_REQUEST)
        test_chunks = chunks[:50]
        chunk_texts = [chunk.text for chunk in test_chunks]
        payload = {"texts": chunk_texts, "prefix_type": "passage"}
        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Verify we can map embeddings back to chunks
        assert len(data["embeddings"]) == len(test_chunks)
        for i, (embedding, chunk) in enumerate(zip(data["embeddings"], test_chunks)):
            assert len(embedding) == data["dimension"]
            assert chunk.chunk_index == i

    def test_pipeline_with_query_and_passage_embeddings(
        self,
        client: TestClient,
        parser_factory: ParserFactory,
        chunker: DocumentChunker,
    ) -> None:
        """Test generating both query and passage embeddings from same document."""
        file_path = FIXTURES_DIR / "simple.pdf"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        # Parse and chunk
        parsed_doc = parser_factory.parse(file_path)
        chunks = chunker.chunk(parsed_doc)
        chunk_texts = [chunk.text for chunk in chunks[:5]]  # Use first 5 chunks

        # Generate passage embeddings
        passage_response = client.post(
            "/embed", json={"texts": chunk_texts, "prefix_type": "passage"}
        )
        assert passage_response.status_code == 200
        passage_data = passage_response.json()

        # Generate query embeddings (simulating user questions)
        query_texts = ["What is this document about?", "Explain the main concept"]
        query_response = client.post(
            "/embed", json={"texts": query_texts, "prefix_type": "query"}
        )
        assert query_response.status_code == 200
        query_data = query_response.json()

        # Verify both have same dimension
        assert passage_data["dimension"] == query_data["dimension"]

    def test_pipeline_handles_large_document(
        self,
        client: TestClient,
        parser_factory: ParserFactory,
        chunker: DocumentChunker,
    ) -> None:
        """Test pipeline with larger multi-page document."""
        file_path = FIXTURES_DIR / "pdf1.pdf"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        # Parse and chunk
        parsed_doc = parser_factory.parse(file_path)
        chunks = chunker.chunk(parsed_doc)

        # Process in batches (simulate real usage)
        batch_size = 32
        all_embeddings = []

        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i : i + batch_size]
            chunk_texts = [chunk.text for chunk in batch_chunks]

            payload = {
                "texts": chunk_texts,
                "prefix_type": "passage",
                "batch_size": 16,
            }
            response = client.post("/embed", json=payload)

            assert response.status_code == 200
            data = response.json()
            all_embeddings.extend(data["embeddings"])

        assert len(all_embeddings) == len(chunks)

    def test_pipeline_chunk_size_affects_embedding_count(
        self,
        client: TestClient,
        parser_factory: ParserFactory,
    ) -> None:
        """Test that different chunk sizes produce different numbers of embeddings."""
        file_path = FIXTURES_DIR / "simple.pdf"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        parsed_doc = parser_factory.parse(file_path)

        # Small chunks
        small_chunker = DocumentChunker(chunk_size=256, chunk_overlap=32)
        small_chunks = small_chunker.chunk(parsed_doc)

        # Large chunks
        large_chunker = DocumentChunker(chunk_size=1024, chunk_overlap=128)
        large_chunks = large_chunker.chunk(parsed_doc)

        # Small chunks should produce more chunks
        assert len(small_chunks) >= len(large_chunks)

        # Both should successfully embed (limit to 50 chunks to avoid MAX_TEXTS_PER_REQUEST)
        for chunks in [small_chunks, large_chunks]:
            test_chunks = chunks[:50]
            chunk_texts = [chunk.text for chunk in test_chunks]
            response = client.post(
                "/embed", json={"texts": chunk_texts, "prefix_type": "passage"}
            )
            assert response.status_code == 200


class TestEmbeddingPerformance:
    """Performance tests for embedding service latency."""

    @pytest.fixture
    def client(self, embedding_model: SentenceTransformer) -> TestClient:
        """Create FastAPI test client."""
        app.state.model = embedding_model
        return TestClient(app)

    @pytest.fixture
    def parser_factory(self) -> ParserFactory:
        """Create parser factory."""
        return ParserFactory()

    @pytest.fixture
    def chunker(self) -> DocumentChunker:
        """Create document chunker."""
        return DocumentChunker(chunk_size=512, chunk_overlap=64)

    def test_measure_single_chunk_latency(self, client: TestClient) -> None:
        """Measure latency for embedding a single chunk."""
        text = "This is a test chunk of text for measuring embedding latency."
        payload = {"texts": [text]}

        start_time = time.perf_counter()
        response = client.post("/embed", json=payload)
        end_time = time.perf_counter()

        assert response.status_code == 200
        latency_ms = (end_time - start_time) * 1000

        # Log latency for visibility
        print(f"\nSingle chunk latency: {latency_ms:.2f}ms")

        # Sanity check: should complete in reasonable time
        assert latency_ms < 5000  # 5 seconds max

    def test_measure_batch_embedding_latency(self, client: TestClient) -> None:
        """Measure latency for embedding multiple chunks in batch."""
        texts = [f"Test chunk number {i} with some content." for i in range(32)]
        payload = {"texts": texts, "batch_size": 16}

        start_time = time.perf_counter()
        response = client.post("/embed", json=payload)
        end_time = time.perf_counter()

        assert response.status_code == 200
        latency_ms = (end_time - start_time) * 1000
        latency_per_text = latency_ms / len(texts)

        print("\nBatch embedding latency:")
        print(f"  Total: {latency_ms:.2f}ms")
        print(f"  Per text: {latency_per_text:.2f}ms")

        assert latency_ms < 10000  # 10 seconds max for 32 texts

    def test_measure_full_pipeline_latency(
        self,
        client: TestClient,
        parser_factory: ParserFactory,
        chunker: DocumentChunker,
    ) -> None:
        """Measure end-to-end latency: document → parse → chunk → embed."""
        file_path = FIXTURES_DIR / "simple.pdf"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        # Measure full pipeline
        start_time = time.perf_counter()

        # Parse
        parse_start = time.perf_counter()
        parsed_doc = parser_factory.parse(file_path)
        parse_time = (time.perf_counter() - parse_start) * 1000

        # Chunk
        chunk_start = time.perf_counter()
        chunks = chunker.chunk(parsed_doc)
        chunk_time = (time.perf_counter() - chunk_start) * 1000

        # Embed
        embed_start = time.perf_counter()
        chunk_texts = [chunk.text for chunk in chunks]
        response = client.post(
            "/embed", json={"texts": chunk_texts, "prefix_type": "passage"}
        )
        embed_time = (time.perf_counter() - embed_start) * 1000

        total_time = (time.perf_counter() - start_time) * 1000

        assert response.status_code == 200

        print("\nFull pipeline latency breakdown:")
        print(f"  Parse:  {parse_time:.2f}ms")
        print(f"  Chunk:  {chunk_time:.2f}ms")
        print(f"  Embed:  {embed_time:.2f}ms")
        print(f"  Total:  {total_time:.2f}ms")
        print(f"  Chunks: {len(chunks)}")

        # Sanity check
        assert total_time < 30000  # 30 seconds max

    def test_compare_batch_sizes(self, client: TestClient) -> None:
        """Compare latency for different batch sizes."""
        texts = [f"Test text {i}" for i in range(64)]
        batch_sizes = [8, 16, 32]
        results = {}

        for batch_size in batch_sizes:
            payload = {"texts": texts, "batch_size": batch_size}

            start_time = time.perf_counter()
            response = client.post("/embed", json=payload)
            end_time = time.perf_counter()

            assert response.status_code == 200
            latency_ms = (end_time - start_time) * 1000
            results[batch_size] = latency_ms

        print("\nBatch size comparison (64 texts):")
        for batch_size, latency in results.items():
            print(f"  Batch size {batch_size}: {latency:.2f}ms")

    def test_measure_token_counting_overhead(self, client: TestClient) -> None:
        """Measure if token counting adds significant overhead."""
        texts = ["Test text " * 50 for _ in range(10)]
        payload = {"texts": texts}

        # Multiple runs to get average
        latencies = []
        for _ in range(3):
            start_time = time.perf_counter()
            response = client.post("/embed", json=payload)
            end_time = time.perf_counter()
            assert response.status_code == 200
            latencies.append((end_time - start_time) * 1000)

        avg_latency = sum(latencies) / len(latencies)
        print(f"\nAverage latency (10 texts, 3 runs): {avg_latency:.2f}ms")

        # Verify token counts are returned
        data = response.json()
        assert all(count > 0 for count in data["token_counts"])
