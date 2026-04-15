"""
Integration tests for LLMService with real OpenRouter API.

These tests require a valid OPENROUTER_API_KEY environment variable.
They are skipped if the API key is not set.

Usage:
    # Option 1: Set environment variable
    export OPENROUTER_API_KEY="sk-or-v1-..."

    # Option 2: Use .env file (recommended)
    echo "OPENROUTER_API_KEY=sk-or-v1-..." > .env

    # Run tests
    uv run pytest tests/integration/test_llm_service_integration.py -v
"""

import os
import uuid

import pytest
from dotenv import load_dotenv

from src.generation.exceptions import LLMInvalidRequestError
from src.generation.models import ContextChunk, GenerationRequest
from src.generation.service import LLMService

# Load environment variables from .env file
load_dotenv()

# Skip all tests if API key is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set (integration tests require real API key)",
)


@pytest.fixture
def api_key():
    """Fixture for OpenRouter API key."""
    return os.getenv("OPENROUTER_API_KEY")


@pytest.fixture
def workspace_id():
    """Fixture for workspace ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_context_chunks():
    """Fixture for sample context chunks."""
    return [
        ContextChunk(
            text="Machine learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed. It uses algorithms to identify patterns and make predictions.",
            filename="ml_intro.pdf",
            page=1,
            score=0.95,
        ),
        ContextChunk(
            text="Deep learning is a subset of machine learning that uses neural networks with multiple layers (deep neural networks) to learn hierarchical representations of data. It has achieved breakthrough results in image recognition, natural language processing, and speech recognition.",
            filename="ml_intro.pdf",
            page=2,
            score=0.88,
        ),
    ]


class TestLLMServiceIntegrationBasic:
    """Basic integration tests for LLMService."""

    @pytest.mark.asyncio
    async def test_generate_with_context(self, api_key, workspace_id, sample_context_chunks):
        """Test non-streaming generation with context."""
        async with LLMService(api_key=api_key) as service:
            request = GenerationRequest(
                question="What is machine learning?",
                context_chunks=sample_context_chunks,
                workspace_id=workspace_id,
                model="openai/gpt-4o-mini",
                temperature=0.1,
                max_tokens=200,
            )

            response = await service.generate(request)

            # Verify response structure
            assert response.answer
            assert len(response.answer) > 0
            assert response.model == "openai/gpt-4o-mini"
            assert response.prompt_tokens > 0
            assert response.completion_tokens > 0
            assert response.total_tokens > 0
            assert response.total_tokens == response.prompt_tokens + response.completion_tokens

            # Verify answer quality (should mention ML concepts)
            answer_lower = response.answer.lower()
            assert any(
                keyword in answer_lower
                for keyword in ["machine learning", "learn", "data", "algorithm", "pattern"]
            )

            # Verify citations (should include [1] or [2])
            assert "[1]" in response.answer or "[2]" in response.answer

    @pytest.mark.asyncio
    async def test_generate_without_context(self, api_key, workspace_id):
        """Test generation without context (general knowledge)."""
        async with LLMService(api_key=api_key) as service:
            request = GenerationRequest(
                question="What is the capital of France?",
                context_chunks=[],
                workspace_id=workspace_id,
                model="openai/gpt-4o-mini",
                temperature=0.1,
                max_tokens=100,
            )

            response = await service.generate(request)

            assert response.answer
            assert response.total_tokens > 0

            # Should mention lack of context or refuse to answer
            answer_lower = response.answer.lower()
            assert "context" in answer_lower or "no context" in answer_lower or "not" in answer_lower

    @pytest.mark.asyncio
    async def test_generate_stream_with_context(self, api_key, workspace_id, sample_context_chunks):
        """Test streaming generation with context."""
        async with LLMService(api_key=api_key) as service:
            request = GenerationRequest(
                question="What is deep learning?",
                context_chunks=sample_context_chunks,
                workspace_id=workspace_id,
                model="openai/gpt-4o-mini",
                temperature=0.1,
                max_tokens=200,
            )

            full_answer = ""
            chunk_count = 0
            final_chunk = None

            async for chunk in service.generate_stream(request):
                chunk_count += 1

                if chunk.content:
                    full_answer += chunk.content
                    assert chunk.done is False

                if chunk.done:
                    final_chunk = chunk
                    assert chunk.content == ""
                    assert chunk.model == "openai/gpt-4o-mini"
                    assert chunk.prompt_tokens > 0
                    assert chunk.completion_tokens > 0
                    assert chunk.total_tokens > 0

            # Verify streaming worked
            assert chunk_count > 1  # Should have multiple chunks
            assert len(full_answer) > 0
            assert final_chunk is not None
            assert final_chunk.done is True

            # Verify answer quality
            answer_lower = full_answer.lower()
            assert any(
                keyword in answer_lower
                for keyword in ["deep learning", "neural network", "layer", "learning"]
            )


class TestLLMServiceIntegrationEdgeCases:
    """Integration tests for edge cases."""

    @pytest.mark.asyncio
    async def test_very_short_question(self, api_key, workspace_id, sample_context_chunks):
        """Test with very short question."""
        async with LLMService(api_key=api_key) as service:
            request = GenerationRequest(
                question="ML?",
                context_chunks=sample_context_chunks,
                workspace_id=workspace_id,
                model="openai/gpt-4o-mini",
                max_tokens=100,
            )

            response = await service.generate(request)

            assert response.answer
            assert response.total_tokens > 0

    @pytest.mark.asyncio
    async def test_long_context(self, api_key, workspace_id):
        """Test with many context chunks."""
        # Create 10 context chunks
        chunks = [
            ContextChunk(
                text=f"This is context chunk number {i}. It contains information about machine learning topic {i}.",
                filename=f"doc_{i}.pdf",
                page=i,
                score=0.9 - (i * 0.05),
            )
            for i in range(10)
        ]

        async with LLMService(api_key=api_key) as service:
            request = GenerationRequest(
                question="Summarize the main topics.",
                context_chunks=chunks,
                workspace_id=workspace_id,
                model="openai/gpt-4o-mini",
                max_tokens=300,
            )

            response = await service.generate(request)

            assert response.answer
            assert response.total_tokens > 0
            # Should have higher token count due to long context
            assert response.prompt_tokens > 200

    @pytest.mark.asyncio
    async def test_high_temperature(self, api_key, workspace_id, sample_context_chunks):
        """Test with high temperature (more creative)."""
        async with LLMService(api_key=api_key) as service:
            request = GenerationRequest(
                question="What is machine learning?",
                context_chunks=sample_context_chunks,
                workspace_id=workspace_id,
                model="openai/gpt-4o-mini",
                temperature=1.5,
                max_tokens=200,
            )

            response = await service.generate(request)

            assert response.answer
            assert response.total_tokens > 0

    @pytest.mark.asyncio
    async def test_low_max_tokens(self, api_key, workspace_id, sample_context_chunks):
        """Test with very low max_tokens."""
        async with LLMService(api_key=api_key) as service:
            request = GenerationRequest(
                question="What is machine learning?",
                context_chunks=sample_context_chunks,
                workspace_id=workspace_id,
                model="openai/gpt-4o-mini",
                max_tokens=20,
            )

            response = await service.generate(request)

            assert response.answer
            # Should be truncated
            assert response.completion_tokens <= 20


class TestLLMServiceIntegrationErrorHandling:
    """Integration tests for error handling."""

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, workspace_id, sample_context_chunks):
        """Test with invalid API key."""
        async with LLMService(api_key="invalid-key-12345") as service:
            request = GenerationRequest(
                question="What is ML?",
                context_chunks=sample_context_chunks,
                workspace_id=workspace_id,
            )

            # Should raise API error (401 or 403)
            with pytest.raises(Exception):  # LLMAPIError or similar
                await service.generate(request)

    @pytest.mark.asyncio
    async def test_invalid_model(self, api_key, workspace_id, sample_context_chunks):
        """Test with non-existent model."""
        async with LLMService(api_key=api_key) as service:
            request = GenerationRequest(
                question="What is ML?",
                context_chunks=sample_context_chunks,
                workspace_id=workspace_id,
                model="invalid/model-name-12345",
            )

            # Should raise API error
            with pytest.raises(Exception):
                await service.generate(request)

    @pytest.mark.asyncio
    async def test_very_short_timeout(self, api_key, workspace_id, sample_context_chunks):
        """Test with very short timeout."""
        async with LLMService(api_key=api_key, timeout=0.001) as service:
            request = GenerationRequest(
                question="What is machine learning?",
                context_chunks=sample_context_chunks,
                workspace_id=workspace_id,
            )

            # Should timeout
            with pytest.raises(Exception):  # LLMTimeoutError
                await service.generate(request)


class TestLLMServiceIntegrationMultipleRequests:
    """Integration tests for multiple requests."""

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(self, api_key, workspace_id, sample_context_chunks):
        """Test multiple sequential requests with same service."""
        async with LLMService(api_key=api_key) as service:
            questions = [
                "What is machine learning?",
                "What is deep learning?",
                "How are they related?",
            ]

            responses = []
            for question in questions:
                request = GenerationRequest(
                    question=question,
                    context_chunks=sample_context_chunks,
                    workspace_id=workspace_id,
                    model="openai/gpt-4o-mini",
                    max_tokens=150,
                )

                response = await service.generate(request)
                responses.append(response)

            # Verify all requests succeeded
            assert len(responses) == 3
            for response in responses:
                assert response.answer
                assert response.total_tokens > 0

    @pytest.mark.asyncio
    async def test_streaming_then_non_streaming(self, api_key, workspace_id, sample_context_chunks):
        """Test mixing streaming and non-streaming requests."""
        async with LLMService(api_key=api_key) as service:
            # First: streaming request
            request1 = GenerationRequest(
                question="What is machine learning?",
                context_chunks=sample_context_chunks,
                workspace_id=workspace_id,
                model="openai/gpt-4o-mini",
                max_tokens=100,
            )

            full_answer = ""
            async for chunk in service.generate_stream(request1):
                if chunk.content:
                    full_answer += chunk.content

            assert len(full_answer) > 0

            # Second: non-streaming request
            request2 = GenerationRequest(
                question="What is deep learning?",
                context_chunks=sample_context_chunks,
                workspace_id=workspace_id,
                model="openai/gpt-4o-mini",
                max_tokens=100,
            )

            response = await service.generate(request2)
            assert response.answer
            assert response.total_tokens > 0
