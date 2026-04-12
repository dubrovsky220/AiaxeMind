"""
Embedding Service — FastAPI microservice for text embedding generation.

Provides HTTP endpoints to encode text into dense vector embeddings using
the SentenceTransformers library. Supports E5-style models with query/passage
prefixes for asymmetric semantic search.

Endpoints:
    GET  /health — Health check with model status
    POST /embed   — Encode texts into embeddings
    GET  /        — Service metadata and API info
"""


import os
from contextlib import asynccontextmanager
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from logging_config import get_logger, setup_logging

# Load .env file if it exists (no-op in Docker where env vars are injected directly)
load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = os.getenv("MODEL_NAME", "intfloat/multilingual-e5-small")
DEVICE = os.getenv("DEVICE", "cpu")
DEFAULT_BATCH_SIZE = int(os.getenv("DEFAULT_BATCH_SIZE", "32"))
MAX_TEXTS_PER_REQUEST = 100
MAX_TEXT_LENGTH = 8_000  # characters — prevents OOM on very long inputs

# Setup logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the embedding service lifecycle: load model on startup, cleanup on shutdown.

    The SentenceTransformer model is loaded once at startup and stored in
    ``app.state.model`` for reuse across requests.
    """
    logger.info("Starting embedding service", extra={"model": MODEL_NAME, "device": DEVICE})
    try:
        app.state.model = SentenceTransformer(MODEL_NAME, device=DEVICE)
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error("Failed to load model", extra={"error": str(e)})
        raise
    yield
    logger.info("Shutting down embedding service")


app = FastAPI(
    title="Embedding Service",
    description="A microservice for generating text embeddings using SentenceTransformers.",
    version="1.0.0",
    lifespan=lifespan,
)


class EmbeddingRequest(BaseModel):
    """Request body for the ``/embed`` endpoint.

    Attributes:
        texts: List of text strings to encode.
        prefix_type: Optional E5-style prefix ("query" or "passage") prepended
            to each text. Used for asymmetric semantic search.
        batch_size: Optional batch size for encoding. Falls back to
            ``DEFAULT_BATCH_SIZE`` if not specified.
    """

    texts: list[str] = Field(
        ...,
        examples=[["What is machine learning?", "It is a subset of AI."]],
    )
    prefix_type: Optional[Literal["query", "passage"]] = Field(
        default=None,
        description='Prefix type for E5 models ("query" or "passage").',
    )
    batch_size: Optional[int] = Field(
        default=None,
        ge=1,
        le=256,
        description="Batch size for encoding (1-256). Uses default if not specified.",
    )


class EmbeddingResponse(BaseModel):
    """Response body for the ``/embed`` endpoint.

    Attributes:
        embeddings: List of embedding vectors, one per input text.
        token_counts: Approximate token count per input text.
        model: Name of the model used for encoding.
        dimension: Dimensionality of each embedding vector.
    """

    embeddings: list[list[float]]
    token_counts: list[int]
    model: str
    dimension: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_model(app: FastAPI):
    """Return the loaded model from app state, or raise HTTP 503."""
    model = getattr(app.state, "model", None)
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return model


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    """Check whether the embedding model is loaded and ready.

    Returns:
        A dictionary with the service status, model name, and device.

    Raises:
        HTTPException: 503 if the model is not loaded.
    """
    _get_model(app)  # validates model availability
    logger.debug("Health check passed")
    return {"status": "healthy", "model": MODEL_NAME, "device": DEVICE}


@app.post(
    "/embed",
    response_model=EmbeddingResponse,
    summary="Generate embeddings for texts",
    description="Encode a list of text strings into dense vector embeddings.",
)
async def embed(request: EmbeddingRequest) -> EmbeddingResponse:
    """Encode texts into dense vector embeddings.

    Args:
        request: The embedding request containing texts and optional settings.

    Returns:
        EmbeddingResponse with embeddings, token counts, and model metadata.

    Raises:
        HTTPException: 503 if the model is not loaded.
        HTTPException: 400 if no texts are provided or the limit is exceeded.
        HTTPException: 500 if encoding fails.
    """
    model = _get_model(app)

    if not request.texts:
        raise HTTPException(status_code=400, detail="No texts provided")

    if len(request.texts) > MAX_TEXTS_PER_REQUEST:
        logger.warning(
            "Embed request rejected: too many texts",
            extra={"count": len(request.texts)},
        )
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_TEXTS_PER_REQUEST} texts allowed per request",
        )

    # Validate text length to prevent OOM
    for i, text in enumerate(request.texts):
        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Text at index {i} exceeds maximum length "
                    f"of {MAX_TEXT_LENGTH} characters"
                ),
            )

    try:
        # Apply prefix if specified
        texts_to_encode = request.texts
        if request.prefix_type:
            prefix = f"{request.prefix_type}: "
            texts_to_encode = [f"{prefix}{text}" for text in request.texts]
            logger.debug(
                "Applied prefix to texts",
                extra={"prefix_type": request.prefix_type, "count": len(request.texts)},
            )

        # Determine batch size
        batch_size = request.batch_size or DEFAULT_BATCH_SIZE

        logger.info(
            "Encoding texts",
            extra={
                "count": len(request.texts),
                "batch_size": batch_size,
                "prefix_type": request.prefix_type,
            },
        )

        # Encode texts
        embeddings = model.encode(
            texts_to_encode,
            batch_size=batch_size,
            convert_to_numpy=True,
        )
        embeddings_list = embeddings.tolist()

        # Calculate token counts (approximate using model's tokenizer)
        tokenizer = model.tokenizer
        token_counts = [
            len(tokenizer.encode(text)) if tokenizer else 0
            for text in texts_to_encode
        ]

        logger.info(
            "Encoding completed",
            extra={
                "count": len(embeddings_list),
                "dimension": len(embeddings_list[0]),
                "total_tokens": sum(token_counts),
            },
        )

        return EmbeddingResponse(
            embeddings=embeddings_list,
            token_counts=token_counts,
            model=MODEL_NAME,
            dimension=len(embeddings_list[0]),
        )
    except HTTPException:
        raise  # re-raise validation errors
    except Exception as e:
        logger.error(
            "Embedding failed",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")


@app.get("/")
async def root() -> dict:
    """Return service metadata and available endpoint info.

    Returns:
        A dictionary with service name, model config, and endpoint paths.
    """
    return {
        "service": "Embedding Service",
        "model": MODEL_NAME,
        "device": DEVICE,
        "default_batch_size": DEFAULT_BATCH_SIZE,
        "endpoints": {
            "health": "/health",
            "embed": "/embed",
            "docs": "/docs",
        },
    }
