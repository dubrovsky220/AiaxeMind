from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AiaxeMind API",
    description="Socratic AI Mentor for Programming Education",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    return {"service": "AiaxeMind API", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
