"""
Pydantic models for LLM generation requests and responses.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ContextChunk(BaseModel):
    """
    Single context chunk for RAG prompt.

    This model represents a retrieved document chunk that will be included
    in the LLM prompt as context for answer generation.

    Attributes:
        text: Full text content of the chunk
        filename: Source document filename
        page: Page number in source document (None if not available)
        score: Similarity score from retrieval (0.0 to 1.0)
    """

    text: str
    filename: str
    page: int | None = None
    score: float = Field(ge=0.0, le=1.0)


class GenerationRequest(BaseModel):
    """
    Request for LLM answer generation.

    Attributes:
        question: User's question
        context_chunks: Retrieved chunks to use as context
        workspace_id: Workspace ID for logging/tracking
        model: OpenRouter model ID (e.g., "openai/gpt-4o-mini")
        temperature: Sampling temperature (0.0-2.0, default 0.1 for factual answers)
        max_tokens: Maximum tokens in response (default 1000)
    """

    question: str = Field(min_length=1)
    context_chunks: list[ContextChunk] = Field(default_factory=list)
    workspace_id: UUID
    model: str = "openai/gpt-4o-mini"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, gt=0)


class GenerationResponse(BaseModel):
    """
    Response from LLM generation (non-streaming).

    Attributes:
        answer: Generated answer text
        model: Model used for generation
        prompt_tokens: Number of tokens in prompt
        completion_tokens: Number of tokens in completion
        total_tokens: Total tokens used
        cost_usd: Estimated cost in USD (None if not available)
    """

    answer: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float | None = None


class StreamChunk(BaseModel):
    """
    Single chunk from streaming generation.

    Attributes:
        content: Text content of this chunk (empty string for metadata-only chunks)
        done: Whether this is the final chunk
        model: Model used (only in final chunk)
        prompt_tokens: Prompt tokens (only in final chunk)
        completion_tokens: Completion tokens (only in final chunk)
        total_tokens: Total tokens (only in final chunk)
        cost_usd: Estimated cost in USD (only in final chunk, None if not available)
    """

    content: str = ""
    done: bool = False
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None
