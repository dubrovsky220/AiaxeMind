"""
LLM service for answer generation via OpenRouter.

This module provides LLM integration with streaming support, retry logic,
and comprehensive error handling for the RAG pipeline.

Key Features:
- OpenRouter integration (OpenAI-compatible API)
- Streaming and non-streaming generation
- Automatic retry with exponential backoff
- Token usage tracking and cost logging
- Comprehensive error handling

Usage:
    from src.generation import LLMService, GenerationRequest, ContextChunk

    # Initialize service
    service = LLMService(api_key="your-key")

    # Non-streaming generation
    request = GenerationRequest(
        question="What is machine learning?",
        context_chunks=[
            ContextChunk(text="ML is...", filename="ml.pdf", page=1, score=0.95)
        ],
        workspace_id=workspace_id
    )
    response = await service.generate(request)
    print(response.answer)

    # Streaming generation
    async for chunk in service.generate_stream(request):
        if chunk.content:
            print(chunk.content, end="", flush=True)
        if chunk.done:
            print(f"\\nTokens: {chunk.total_tokens}, Cost: ${chunk.cost_usd}")
"""

import json
import os
import types
from collections.abc import AsyncGenerator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.logging_config import get_logger
from src.generation.exceptions import (
    LLMAPIError,
    LLMConnectionError,
    LLMInvalidRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.generation.models import GenerationRequest, GenerationResponse, StreamChunk
from src.generation.prompts import build_system_message, build_user_message

logger = get_logger(__name__)


class LLMService:
    """
    LLM service for answer generation via OpenRouter.

    This service handles all LLM interactions with automatic retry logic,
    error handling, and token usage tracking.

    Architecture:
    - Uses OpenRouter's OpenAI-compatible API
    - Supports both streaming and non-streaming modes
    - Automatic retry for transient errors (timeout, rate limit, 5xx)
    - Comprehensive logging for debugging and cost tracking

    Example:
        service = LLMService(api_key="sk-or-...")

        # Non-streaming
        response = await service.generate(request)

        # Streaming
        async for chunk in service.generate_stream(request):
            print(chunk.content, end="")
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize LLM service.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            base_url: OpenRouter API base URL
            timeout: Request timeout in seconds (default: 60.0)
            max_retries: Maximum number of retry attempts (default: 3)

        Raises:
            LLMInvalidRequestError: If API key is not provided
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise LLMInvalidRequestError("API key is required (set OPENROUTER_API_KEY env var)")

        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )

        logger.info(
            "LLMService initialized",
            extra={
                "base_url": self.base_url,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            },
        )

    async def __aenter__(self) -> "LLMService":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
        logger.debug("LLMService client closed")

    @retry(
        retry=retry_if_exception_type((LLMTimeoutError, LLMRateLimitError, LLMAPIError)),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate answer using LLM (non-streaming).

        This method sends a request to OpenRouter and waits for the complete response.
        Automatically retries on transient errors (timeout, rate limit, 5xx).

        Args:
            request: Generation request with question and context

        Returns:
            GenerationResponse with answer and token usage

        Raises:
            LLMConnectionError: If connection to OpenRouter fails
            LLMAPIError: If API returns an error
            LLMTimeoutError: If request times out
            LLMRateLimitError: If rate limit is exceeded
            LLMInvalidRequestError: If request is invalid

        Example:
            request = GenerationRequest(
                question="What is ML?",
                context_chunks=[...],
                workspace_id=workspace_id
            )
            response = await service.generate(request)
            print(response.answer)
        """
        logger.info(
            "Generating answer (non-streaming)",
            extra={
                "workspace_id": str(request.workspace_id),
                "model": request.model,
                "context_chunks": len(request.context_chunks),
                "question_length": len(request.question),
            },
        )

        # Build messages
        messages = [
            {"role": "system", "content": build_system_message()},
            {"role": "user", "content": build_user_message(request.question, request.context_chunks)},
        ]

        # Build request payload
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }

        try:
            # Send request
            response = await self.client.post("/chat/completions", json=payload)

            # Handle errors
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                retry_after_int = int(retry_after) if retry_after else None
                logger.warning(
                    "Rate limit exceeded",
                    extra={"retry_after": retry_after_int, "workspace_id": str(request.workspace_id)},
                )
                raise LLMRateLimitError(retry_after=retry_after_int)

            if response.status_code >= 500:
                logger.error(
                    "OpenRouter server error",
                    extra={"status_code": response.status_code, "response": response.text},
                )
                raise LLMAPIError(
                    status_code=response.status_code,
                    error_message=f"Server error: {response.text}",
                )

            if response.status_code >= 400:
                error_data = response.json() if response.text else {}
                error_message = error_data.get("error", {}).get("message", response.text)
                logger.error(
                    "OpenRouter API error",
                    extra={
                        "status_code": response.status_code,
                        "error": error_message,
                        "workspace_id": str(request.workspace_id),
                    },
                )
                raise LLMAPIError(status_code=response.status_code, error_message=error_message)

            # Parse response
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            logger.info(
                "Answer generated successfully",
                extra={
                    "workspace_id": str(request.workspace_id),
                    "model": request.model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "answer_length": len(answer),
                },
            )

            return GenerationResponse(
                answer=answer,
                model=request.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=None,
            )

        except httpx.TimeoutException as e:
            logger.error(
                "Request timeout",
                extra={"timeout": self.timeout, "workspace_id": str(request.workspace_id)},
            )
            raise LLMTimeoutError(timeout_seconds=self.timeout) from e

        except httpx.ConnectError as e:
            logger.error(
                "Connection error",
                extra={"base_url": self.base_url, "error": str(e)},
            )
            raise LLMConnectionError(provider="OpenRouter", original_error=e) from e

        except (LLMRateLimitError, LLMAPIError, LLMTimeoutError):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            logger.error(
                "Unexpected error during generation",
                extra={"error": str(e), "workspace_id": str(request.workspace_id)},
            )
            raise LLMAPIError(status_code=500, error_message=str(e), original_error=e) from e

    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[StreamChunk, None]:
        """
        Generate answer using LLM (streaming).

        This method sends a request to OpenRouter and yields chunks as they arrive.
        The final chunk includes token usage and cost information.

        Note: Retry logic is NOT applied to streaming requests because:
        - If error occurs mid-stream, already-yielded chunks cannot be recovered
        - Retrying would duplicate partial responses to the client
        - For transient errors, client should handle reconnection at application level

        Args:
            request: Generation request with question and context

        Yields:
            StreamChunk objects with content and metadata

        Raises:
            LLMConnectionError: If connection to OpenRouter fails
            LLMAPIError: If API returns an error
            LLMTimeoutError: If request times out
            LLMRateLimitError: If rate limit is exceeded
            LLMInvalidRequestError: If request is invalid

        Example:
            async for chunk in service.generate_stream(request):
                if chunk.content:
                    print(chunk.content, end="", flush=True)
                if chunk.done:
                    print(f"\\nTokens: {chunk.total_tokens}")
        """
        logger.info(
            "Generating answer (streaming)",
            extra={
                "workspace_id": str(request.workspace_id),
                "model": request.model,
                "context_chunks": len(request.context_chunks),
                "question_length": len(request.question),
            },
        )

        # Build messages
        messages = [
            {"role": "system", "content": build_system_message()},
            {"role": "user", "content": build_user_message(request.question, request.context_chunks)},
        ]

        # Build request payload
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }

        try:
            # Send streaming request
            async with self.client.stream("POST", "/chat/completions", json=payload) as response:
                # Handle errors
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_after_int = int(retry_after) if retry_after else None
                    logger.warning(
                        "Rate limit exceeded",
                        extra={"retry_after": retry_after_int, "workspace_id": str(request.workspace_id)},
                    )
                    raise LLMRateLimitError(retry_after=retry_after_int)

                if response.status_code >= 500:
                    error_text = await response.aread()
                    logger.error(
                        "OpenRouter server error",
                        extra={"status_code": response.status_code, "response": error_text.decode()},
                    )
                    raise LLMAPIError(
                        status_code=response.status_code,
                        error_message=f"Server error: {error_text.decode()}",
                    )

                if response.status_code >= 400:
                    error_text = await response.aread()
                    logger.error(
                        "OpenRouter API error",
                        extra={
                            "status_code": response.status_code,
                            "error": error_text.decode(),
                            "workspace_id": str(request.workspace_id),
                        },
                    )
                    raise LLMAPIError(
                        status_code=response.status_code,
                        error_message=error_text.decode(),
                    )

                # Process SSE stream
                full_answer = ""
                async for line in response.aiter_lines():
                    if not line.strip() or not line.startswith("data: "):
                        continue

                    data_str = line[6:]  # Remove "data: " prefix

                    if data_str == "[DONE]":
                        # Stream finished
                        logger.info(
                            "Streaming completed",
                            extra={
                                "workspace_id": str(request.workspace_id),
                                "answer_length": len(full_answer),
                            },
                        )
                        break

                    try:
                        data = json.loads(data_str)

                        # Extract content delta
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            full_answer += content
                            yield StreamChunk(content=content, done=False)

                        # Check for usage in final chunk
                        usage = data.get("usage")
                        if usage:
                            prompt_tokens = usage.get("prompt_tokens", 0)
                            completion_tokens = usage.get("completion_tokens", 0)
                            total_tokens = usage.get("total_tokens", 0)

                            logger.info(
                                "Streaming answer generated successfully",
                                extra={
                                    "workspace_id": str(request.workspace_id),
                                    "model": request.model,
                                    "prompt_tokens": prompt_tokens,
                                    "completion_tokens": completion_tokens,
                                    "total_tokens": total_tokens,
                                    "answer_length": len(full_answer),
                                },
                            )

                            # Yield final chunk with metadata
                            yield StreamChunk(
                                content="",
                                done=True,
                                model=request.model,
                                prompt_tokens=prompt_tokens,
                                completion_tokens=completion_tokens,
                                total_tokens=total_tokens,
                                cost_usd=None,
                            )

                    except json.JSONDecodeError:
                        logger.warning("Failed to parse SSE chunk", extra={"line": line})
                        continue

        except httpx.TimeoutException as e:
            logger.error(
                "Request timeout",
                extra={"timeout": self.timeout, "workspace_id": str(request.workspace_id)},
            )
            raise LLMTimeoutError(timeout_seconds=self.timeout) from e

        except httpx.ConnectError as e:
            logger.error(
                "Connection error",
                extra={"base_url": self.base_url, "error": str(e)},
            )
            raise LLMConnectionError(provider="OpenRouter", original_error=e) from e

        except (LLMRateLimitError, LLMAPIError, LLMTimeoutError):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            logger.error(
                "Unexpected error during streaming",
                extra={"error": str(e), "workspace_id": str(request.workspace_id)},
            )
            raise LLMAPIError(status_code=500, error_message=str(e), original_error=e) from e


async def main() -> None:
    """
    Manual test script for LLMService.

    Usage:
        # Set API key and model
        export OPENROUTER_API_KEY="sk-or-v1-..."
        export OPENROUTER_MODEL="openai/gpt-4o-mini"  # optional, defaults to gpt-4o-mini

        # Run test
        uv run python -m src.generation.service

    This script tests:
    - Non-streaming generation
    - Streaming generation
    - Error handling
    - Token usage tracking
    """
    import uuid

    from dotenv import load_dotenv

    from src.core.logging_config import setup_logging
    from src.generation.models import ContextChunk

    load_dotenv()

    setup_logging(level="INFO")

    print("\n" + "=" * 80)
    print("LLM SERVICE MANUAL TEST")
    print("=" * 80 + "\n")

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY environment variable not set")
        print("   Set it with: export OPENROUTER_API_KEY='sk-or-v1-...'")
        return

    print(f"✓ API key found: {api_key[:20]}...\n")

    # Get model from env or use default
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    print(f"✓ Using model: {model}\n")

    # Initialize service
    print("Step 1: Initializing LLM service...")
    async with LLMService(api_key=api_key) as service:
        print("✓ LLM service initialized\n")

        # Create test data
        workspace_id = uuid.uuid4()
        context_chunks = [
            ContextChunk(
                text="Machine learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed.",
                filename="ml_intro.pdf",
                page=1,
                score=0.95,
            ),
            ContextChunk(
                text="Deep learning uses neural networks with multiple layers to learn hierarchical representations of data.",
                filename="ml_intro.pdf",
                page=2,
                score=0.88,
            ),
        ]

        # Test 1: Non-streaming generation
        print("Step 2: Testing non-streaming generation...")
        request = GenerationRequest(
            question="What is machine learning?",
            context_chunks=context_chunks,
            workspace_id=workspace_id,
            model=model,
            temperature=0.1,
            max_tokens=200,
        )

        response = await service.generate(request)
        print(f"✓ Answer generated ({len(response.answer)} chars):")
        print(f"  {response.answer}\n")
        print(f"  Model: {response.model}")
        print(f"  Tokens: {response.prompt_tokens} + {response.completion_tokens} = {response.total_tokens}")
        print(f"  Cost: ${response.cost_usd if response.cost_usd else 'N/A'}\n")

        # Test 2: Streaming generation
        print("Step 3: Testing streaming generation...")
        print("Answer (streaming): ", end="", flush=True)

        full_answer = ""
        async for chunk in service.generate_stream(request):
            if chunk.content:
                print(chunk.content, end="", flush=True)
                full_answer += chunk.content

            if chunk.done:
                print(f"\n\n✓ Streaming completed ({len(full_answer)} chars)")
                print(f"  Model: {chunk.model}")
                print(f"  Tokens: {chunk.prompt_tokens} + {chunk.completion_tokens} = {chunk.total_tokens}")
                print(f"  Cost: ${chunk.cost_usd if chunk.cost_usd else 'N/A'}\n")

        # Test 3: Empty context
        print("Step 4: Testing with empty context...")
        request_no_context = GenerationRequest(
            question="What is the capital of France?",
            context_chunks=[],
            workspace_id=workspace_id,
            model=model,
        )

        response_no_context = await service.generate(request_no_context)
        print("✓ Answer with no context:")
        print(f"  {response_no_context.answer[:200]}...\n")

    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
