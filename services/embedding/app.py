import os
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

app = FastAPI(title="Embedding Service")

# Load model on startup
MODEL_NAME = os.getenv("MODEL_NAME", "BAAI/bge-small-en-v1.5")
model = None


@app.on_event("startup")
async def load_model() -> None:
    global model
    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print("Model loaded successfully")


class EmbeddingRequest(BaseModel):
    texts: List[str]


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int


@app.get("/health")
async def health() -> dict:
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "healthy", "model": MODEL_NAME}


@app.post("/embed", response_model=EmbeddingResponse)
async def embed(request: EmbeddingRequest) -> EmbeddingResponse:
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not request.texts:
        raise HTTPException(status_code=400, detail="No texts provided")

    try:
        embeddings = model.encode(request.texts, convert_to_numpy=True)
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
