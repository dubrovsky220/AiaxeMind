"""
Unit tests for LLMService with mocked HTTP client.
"""

import uuid
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from src.generation.exceptions import (
    LLMAPIError,
    LLMConnectionError,
    LLMInvalidRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.generation.models import ContextChunk, GenerationRequest
from src.generation.service import LLMService


@pytest.fixture
def workspace_id():
    """Fixture for workspace ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_context_chunks():
    """Fixture for sample context chunks."""
    return [
        ContextChunk(
            text="Machine learning is a subset of AI.",
            filename="ml_intro.pdf",
            page=1,
            score=0.95,
        ),
        ContextChunk(
            text="Deep learning uses neural networks.",
            filename="ml_intro.pdf",
            page=2,
            score=0.88,
        ),
    ]


@pytest.fixture
def sample_request(workspace_id, sample_context_chunks):
    """Fixture for sample generation request."""
    return GenerationRequest(
        question="What is machine learning?",
        context_chunks=sample_context_chunks,
        workspace_id=workspace_id,
        model="openai/gpt-4o-mini",
        temperature=0.1,
        max_tokens=500,
    )


class TestLLMServiceInitialization:
    """Tests for LLMService initialization."""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        service = LLMService(api_key="test-key")

        assert service.api_key == "test-key"
        assert service.base_url == "https://openrouter.ai/api/v1"
        assert service.timeout == 60.0
        assert service.max_retries == 3

    def test_init_with_env_var(self, monkeypatch):
        """Test initialization with API key from environment."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")
        service = LLMService()

        assert service.api_key == "env-key"

    def test_init_without_api_key(self, monkeypatch):
        """Test initialization fails without API key."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        with pytest.raises(LLMInvalidRequestError) as exc_info:
            LLMService()

        assert "API key is required" in str(exc_info.value)

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        service = LLMService(
            api_key="test-key",
            base_url="https://custom.api",
            timeout=30.0,
            max_retries=5,
        )

        assert service.base_url == "https://custom.api"
        assert service.timeout == 30.0
        assert service.max_retries == 5

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with LLMService(api_key="test-key") as service:
            assert service.api_key == "test-key"
            assert service.client is not None

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        service = LLMService(api_key="test-key")
        await service.close()
        # Client should be closed (no exception)


class TestLLMServiceGenerate:
    """Tests for non-streaming generation."""

    @pytest.mark.asyncio
    async def test_generate_success(self, sample_request):
        """Test successful generation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Machine learning is a subset of AI that enables computers to learn from data."
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 50,
                "total_tokens": 200,
            },
        }

        service = LLMService(api_key="test-key")
        service.client.post = AsyncMock(return_value=mock_response)

        response = await service.generate(sample_request)

        assert "Machine learning" in response.answer
        assert response.model == "openai/gpt-4o-mini"
        assert response.prompt_tokens == 150
        assert response.completion_tokens == 50
        assert response.total_tokens == 200

        # Verify request payload
        call_args = service.client.post.call_args
        assert call_args[0][0] == "/chat/completions"
        payload = call_args[1]["json"]
        assert payload["model"] == "openai/gpt-4o-mini"
        assert payload["temperature"] == 0.1
        assert payload["max_tokens"] == 500
        assert payload["stream"] is False
        assert len(payload["messages"]) == 2

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_empty_context(self, workspace_id):
        """Test generation with empty context."""
        request = GenerationRequest(
            question="What is the capital of France?",
            context_chunks=[],
            workspace_id=workspace_id,
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Paris is the capital of France."}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        }

        service = LLMService(api_key="test-key")
        service.client.post = AsyncMock(return_value=mock_response)

        response = await service.generate(request)

        assert "Paris" in response.answer
        assert response.total_tokens == 70

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_rate_limit_error(self, sample_request):
        """Test rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        service = LLMService(api_key="test-key")
        service.client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMRateLimitError) as exc_info:
            await service.generate(sample_request)

        assert exc_info.value.retry_after == 60

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_server_error(self, sample_request):
        """Test server error (5xx) handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        service = LLMService(api_key="test-key")
        service.client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMAPIError) as exc_info:
            await service.generate(sample_request)

        assert exc_info.value.status_code == 500
        assert "Server error" in str(exc_info.value)

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_client_error(self, sample_request):
        """Test client error (4xx) handling."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = '{"error": {"message": "Invalid request"}}'
        mock_response.json.return_value = {"error": {"message": "Invalid request"}}

        service = LLMService(api_key="test-key")
        service.client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMAPIError) as exc_info:
            await service.generate(sample_request)

        assert exc_info.value.status_code == 400
        assert "Invalid request" in exc_info.value.error_message

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_timeout_error(self, sample_request):
        """Test timeout error handling."""
        service = LLMService(api_key="test-key", timeout=5.0)
        service.client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(LLMTimeoutError) as exc_info:
            await service.generate(sample_request)

        assert exc_info.value.timeout_seconds == 5.0

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, sample_request):
        """Test connection error handling."""
        service = LLMService(api_key="test-key")
        service.client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

        with pytest.raises(LLMConnectionError) as exc_info:
            await service.generate(sample_request)

        assert exc_info.value.provider == "OpenRouter"

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_retry_logic(self, sample_request):
        """Test retry logic for transient errors."""
        # First call fails with 500, second succeeds
        mock_response_error = Mock()
        mock_response_error.status_code = 500
        mock_response_error.text = "Server error"

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "choices": [{"message": {"content": "Success after retry"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
        }

        service = LLMService(api_key="test-key")
        service.client.post = AsyncMock(side_effect=[mock_response_error, mock_response_success])

        response = await service.generate(sample_request)

        assert "Success after retry" in response.answer
        assert service.client.post.call_count == 2

        await service.close()


class TestLLMServiceGenerateStream:
    """Tests for streaming generation."""

    @pytest.mark.asyncio
    async def test_generate_stream_success(self, sample_request):
        """Test successful streaming generation."""
        # Mock SSE stream
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Machine"}}]}',
            'data: {"choices": [{"delta": {"content": " learning"}}]}',
            'data: {"choices": [{"delta": {"content": " is"}}]}',
            'data: {"choices": [{"delta": {}}], "usage": {"prompt_tokens": 150, "completion_tokens": 50, "total_tokens": 200}}',
            "data: [DONE]",
        ]

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.headers = {}

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        service = LLMService(api_key="test-key")
        service.client.stream = Mock(return_value=mock_stream_context)

        chunks = []
        async for chunk in service.generate_stream(sample_request):
            chunks.append(chunk)

        # Verify chunks
        assert len(chunks) == 4
        assert chunks[0].content == "Machine"
        assert chunks[0].done is False
        assert chunks[1].content == " learning"
        assert chunks[2].content == " is"
        assert chunks[3].content == ""
        assert chunks[3].done is True
        assert chunks[3].total_tokens == 200

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_stream_rate_limit(self, sample_request):
        """Test rate limit error in streaming."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        service = LLMService(api_key="test-key")
        service.client.stream = Mock(return_value=mock_stream_context)

        with pytest.raises(LLMRateLimitError) as exc_info:
            async for _ in service.generate_stream(sample_request):
                pass

        assert exc_info.value.retry_after == 30

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_stream_server_error(self, sample_request):
        """Test server error in streaming."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.aread = AsyncMock(return_value=b"Service Unavailable")

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        service = LLMService(api_key="test-key")
        service.client.stream = Mock(return_value=mock_stream_context)

        with pytest.raises(LLMAPIError) as exc_info:
            async for _ in service.generate_stream(sample_request):
                pass

        assert exc_info.value.status_code == 503

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_stream_invalid_json(self, sample_request):
        """Test handling of invalid JSON in stream."""
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Valid"}}]}',
            "data: {invalid json}",
            'data: {"choices": [{"delta": {"content": " content"}}]}',
            "data: [DONE]",
        ]

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        service = LLMService(api_key="test-key")
        service.client.stream = Mock(return_value=mock_stream_context)

        chunks = []
        async for chunk in service.generate_stream(sample_request):
            chunks.append(chunk)

        # Should skip invalid JSON and continue
        assert len(chunks) == 2
        assert chunks[0].content == "Valid"
        assert chunks[1].content == " content"

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_stream_empty_lines(self, sample_request):
        """Test handling of empty lines in stream."""
        sse_lines = [
            "",
            'data: {"choices": [{"delta": {"content": "Content"}}]}',
            "",
            "data: [DONE]",
        ]

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        service = LLMService(api_key="test-key")
        service.client.stream = Mock(return_value=mock_stream_context)

        chunks = []
        async for chunk in service.generate_stream(sample_request):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].content == "Content"

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_stream_connection_error(self, sample_request):
        """Test connection error in streaming."""
        service = LLMService(api_key="test-key")
        service.client.stream = Mock(side_effect=httpx.ConnectError("Connection failed"))

        with pytest.raises(LLMConnectionError):
            async for _ in service.generate_stream(sample_request):
                pass

        await service.close()


class TestLLMServiceEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_generate_missing_usage_data(self, sample_request):
        """Test handling of missing usage data in response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Answer without usage data"}}],
            # No usage field
        }

        service = LLMService(api_key="test-key")
        service.client.post = AsyncMock(return_value=mock_response)

        response = await service.generate(sample_request)

        assert response.answer == "Answer without usage data"
        assert response.prompt_tokens == 0
        assert response.completion_tokens == 0
        assert response.total_tokens == 0

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_partial_usage_data(self, sample_request):
        """Test handling of partial usage data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Answer"}}],
            "usage": {
                "prompt_tokens": 100,
                # Missing completion_tokens and total_tokens
            },
        }

        service = LLMService(api_key="test-key")
        service.client.post = AsyncMock(return_value=mock_response)

        response = await service.generate(sample_request)

        assert response.prompt_tokens == 100
        assert response.completion_tokens == 0
        assert response.total_tokens == 0

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_unexpected_exception(self, sample_request):
        """Test handling of unexpected exceptions."""
        service = LLMService(api_key="test-key")
        service.client.post = AsyncMock(side_effect=ValueError("Unexpected error"))

        with pytest.raises(LLMAPIError) as exc_info:
            await service.generate(sample_request)

        assert "Unexpected error" in str(exc_info.value)

        await service.close()
