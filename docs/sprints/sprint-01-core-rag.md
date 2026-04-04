# Sprint 1 — Core RAG

## Goal

Deliver an end-to-end path: **ingest course text → chunk → embed → store in Qdrant → retrieve → answer with citations** behind a **FastAPI** surface, runnable via **Docker Compose** with the services this phase needs.

**MVP Focus:** This sprint establishes the foundation — a working RAG pipeline that can answer questions from uploaded documents with proper citations.

## Link to description

- **Implementation Plan:** [Phase 1: Core RAG](../description.md#phase-1-core-rag)
- **Modules:** Primarily [Module 1: Data Ingestion](../description.md#module-1-data-ingestion--processing-pipeline) (parse, chunk, metadata; defer advanced strategies to later sprints) and [Module 2: Indexing & Retrieval](../description.md#module-2-indexing--retrieval-engine) (basic vector retrieval only — no hybrid/rerank yet).
- **Stack hints:** See the tech table in [Complete Tech Stack](../description.md#complete-tech-stack) (Qdrant, PostgreSQL, FastAPI, embeddings, parsing libraries as needed for PDF/DOCX).

## Scope (in)

1. Parse **PDF and DOCX** into text; split into **chunks** with sensible defaults (e.g., RecursiveCharacterTextSplitter, chunk_size=512, overlap=64).
2. **Embeddings** for chunks; **upsert** vectors to **Qdrant** with enough payload for filtering and citations (e.g. source id, chunk id, text snippet, page number).
3. Persist **document/chunk metadata** in **PostgreSQL** (or SQLite for MVP simplicity) appropriate to this slice (minimal schema is fine; extend in later sprints).
4. **Retrieval:** similarity search over workspace/collection scope; pass retrieved context to the LLM.
5. **Generation:** LLM answers **with citations** tied to retrieved chunks/sources (e.g., [1], [2] format).
6. **FastAPI** endpoint(s):
   - `POST /api/v1/documents/upload` — upload and process document
   - `POST /api/v1/chat` — ask a question, get answer with citations
   - `GET /api/v1/documents` — list uploaded documents
7. **Docker Compose** includes at least **FastAPI + Qdrant + PostgreSQL** (or SQLite) and documented env vars; `docker compose up` runs the stack for local dev.
8. **Basic error handling** — graceful failures for unsupported files, embedding errors, LLM timeouts.

## Out of scope

- Elasticsearch / BM25, reranking, multi-query, parent-child chunking (Sprint 4).
- LangGraph teaching modes, WebSocket streaming (Sprint 2).
- Image extraction, captioning, MinIO (Sprint 5).
- Celery/Redis — synchronous MVP upload is acceptable.
- Full auth/workspace management (later sprints).

## Technical pointers

- **Chunking:** Start with `RecursiveCharacterTextSplitter` from LangChain; document chosen parameters.
- **Embeddings:** OpenAI `text-embedding-3-small` or open-source (e.g., `BAAI/bge-small-en-v1.5`); batch/rate-limit as needed.
- **Citations:** Store chunk metadata (source_id, page, chunk_index) in Qdrant payload; format as `[1] Source: filename.pdf, Page: 5`.
- **Database:** SQLite is acceptable for MVP; PostgreSQL if you want production-like setup.
- **LLM:** OpenAI GPT-4o-mini for cost efficiency, or GPT-4o for quality.

## Readiness criteria

- [ ] A sample PDF/DOCX can be ingested via API and queried; response includes traceable citations to stored chunks.
- [ ] Qdrant holds vectors with proper metadata; database holds document/chunk records.
- [ ] API is documented (OpenAPI/Swagger) and callable locally via curl/Postman.
- [ ] Compose file and README allow another dev to run the stack with `docker compose up`.
- [ ] Basic error handling works (upload invalid file → returns 400 with error message).

## Risks and dependencies

- **Cost/latency:** embedding + LLM calls — define env-based limits early (e.g., max 100 chunks per document for MVP).
- **Next sprint** depends on stable chunk IDs and retrieval contract for Socratic engine integration.

## Estimated effort

**1 week** (5-7 days) for someone learning the stack as they go.

---

**Sprint label (GitHub):** `sprint:1`
