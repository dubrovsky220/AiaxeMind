# AiaxeMind

Socratic AI Mentor for online programming and Data Science schools.

## Overview

AiaxeMind is an adaptive teaching system that uses Socratic questioning to help students think independently. Instead of giving direct answers, it guides students through problem-solving with personalized questions and generates quizzes based on their progress.

## Tech Stack

- **Backend:** FastAPI, Python 3.12
- **Database:** PostgreSQL, Qdrant (vector DB)
- **LLM:** OpenRouter (GPT-4o-mini)
- **Embeddings:** sentence-transformers (BAAI/bge-small-en-v1.5)
- **Document Processing:** PyMuPDF (PDF), python-docx (DOCX)
- **Package Manager:** uv

## Setup

### Prerequisites

- Python 3.12
- uv package manager
- Docker & Docker Compose

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd AiaxeMind
```

2. Copy environment variables:
```bash
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

3. Install dependencies:
```bash
uv sync
```

4. Start services (PostgreSQL, Qdrant):
```bash
docker compose up -d
```

5. Run database migrations:
```bash
uv run alembic upgrade head
```

6. Start the API server:
```bash
uv run uvicorn src.api.main:app --reload
```

## Project Structure

```
AiaxeMind/
├── src/
│   ├── api/              # FastAPI routes and schemas
│   ├── ingestion/        # Document parsing and chunking
│   ├── retrieval/        # Vector search
│   ├── generation/       # LLM integration
│   ├── models/           # SQLAlchemy models
│   └── core/             # Shared utilities
├── services/
│   └── embedding/        # Embedding microservice
├── tests/                # Unit and integration tests
├── alembic/              # Database migrations
└── docs/                 # Documentation
```

## Development

Run tests:
```bash
uv run pytest
```

Run linter:
```bash
uv run ruff check .
```

Run type checker:
```bash
uv run mypy src/
```
