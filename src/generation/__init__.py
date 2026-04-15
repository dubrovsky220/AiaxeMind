"""
Generation module for LLM-based answer generation.

This module provides LLM integration via OpenRouter with streaming support
for the RAG (Retrieval-Augmented Generation) pipeline.

Key Components:
- LLMService: Main service for LLM interactions with retry logic
- GenerationRequest/Response: Pydantic models for requests and responses
- StreamChunk: Model for streaming response chunks
- ContextChunk: Model for retrieved context chunks
- Prompt templates: RAG-specific prompt formatting with citations

Usage:
    from src.generation import LLMService, GenerationRequest, ContextChunk

    # Initialize service
    async with LLMService() as service:
        # Create request
        request = GenerationRequest(
            question="What is machine learning?",
            context_chunks=[
                ContextChunk(text="ML is...", filename="ml.pdf", page=1, score=0.95)
            ],
            workspace_id=workspace_id
        )

        # Non-streaming
        response = await service.generate(request)
        print(response.answer)

        # Streaming
        async for chunk in service.generate_stream(request):
            if chunk.content:
                print(chunk.content, end="")
"""

from src.generation.exceptions import (
    LLMAPIError,
    LLMConnectionError,
    LLMError,
    LLMInvalidRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.generation.models import (
    ContextChunk,
    GenerationRequest,
    GenerationResponse,
    StreamChunk,
)
from src.generation.service import LLMService

__all__ = [
    # Service
    "LLMService",
    # Models
    "GenerationRequest",
    "GenerationResponse",
    "StreamChunk",
    "ContextChunk",
    # Exceptions
    "LLMError",
    "LLMConnectionError",
    "LLMAPIError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMInvalidRequestError",
]
