import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

MODEL_NAME = os.getenv("MODEL_NAME", "BAAI/bge-small-en-v1.5")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Loading model: {MODEL_NAME}")
    app.state.model = SentenceTransformer(MODEL_NAME)
    print("Model loaded successfully")
    yield
    print("Shutting down embedding service")


app = FastAPI(title="Embedding Service", lifespan=lifespan)


class EmbeddingRequest(BaseModel):
    texts: List[str]


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int


@app.get("/health")
async def health() -> dict:
    if not hasattr(app.state, "model") or app.state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "healthy", "model": MODEL_NAME}


@app.post("/embed", response_model=EmbeddingResponse)
async def embed(request: EmbeddingRequest) -> EmbeddingResponse:
    if not hasattr(app.state, "model") or app.state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not request.texts:
        raise HTTPException(status_code=400, detail="No texts provided")

    try:
        embeddings = app.state.model.encode(request.texts, convert_to_numpy=True)
        embeddings_list = embeddings.tolist()

        return EmbeddingResponse(
            embeddings=embeddings_list, model=MODEL_NAME, dimension=len(embeddings_list[0])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")


@app.get("/")
async def root() -> dict:
    return {
        "service": "Embedding Service",
        "model": MODEL_NAME,
        "endpoints": {"health": "/health", "embed": "/embed"},
    }
