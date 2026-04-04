# Project: **AiaxeMind** — Socratic AI Mentor for Online Schools

**Sprint execution:** Per-sprint scope, readiness criteria, and the link to GitHub Issues are documented in **[`docs/sprints/README.md`](sprints/README.md)** (eight sprint files, one per implementation phase below).

## Positioning

> AI mentor for online programming and Data Science schools. Uses the **Socratic teaching method** instead of direct answers — asks guiding questions to help students think independently. Automatically generates personalized quizzes based on analysis of student weaknesses. Reduces mentor workload by 60-70%, allowing them to focus on code reviews and complex cases.

---

## Overall Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Streamlit)                     │
│         Chat UI / Source Manager / Quizzes / Analytics          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / WebSocket (streaming)
┌──────────────────────────▼──────────────────────────────────────┐
│                     API Layer (FastAPI)                          │
│         REST endpoints + WebSocket + Auth (JWT)                  │
└───┬──────────┬───────────┬──────────────┬───────────────────────┘
    │          │           │              │
    ▼          ▼           ▼              ▼
┌────────┐┌────────┐┌───────────┐┌──────────────────┐
│Socratic││Ingest  ││Evaluation ││ Scheduled Jobs   │
│Teaching││Pipeline││ Pipeline  ││ (Celery Beat)    │
│ Engine ││        ││ (RAGAS)   ││ Quiz Generation  │
└───┬────┘└───┬────┘└───────────┘└──────────────────┘
    │         │
    ▼         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Storage Layer                               │
│  Qdrant (vectors) │ PostgreSQL (metadata) │ Redis (cache/queue)  │
│  MinIO/S3 (files/images) │ Elasticsearch (BM25)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Modules and Features

### Module 1: Data Ingestion & Processing Pipeline

**What it does:** Accepts educational materials in various formats, parses them, extracts text and images (diagrams, charts, formulas), splits into chunks, enriches with metadata.

**Features:**

- Parsing PDF, DOCX, HTML/web pages, Markdown, YouTube (lecture transcripts)
- Image extraction from documents with text binding (especially important for ML/Math courses — charts, diagrams, formulas)
- Table extraction → conversion to Markdown/structured format
- Multiple chunking strategies: recursive, semantic, parent-child (small chunks for retrieval, large chunks for context)
- Automatic metadata extraction: title, author, date, topic, language
- LLM-generated summary for each document upon upload
- Deduplication (don't upload the same document twice)

**Technologies:**

```
- Unstructured.io — universal document parsing
- PyMuPDF (fitz) — image extraction from PDF
- BeautifulSoup + trafilatura — web scraping
- youtube-transcript-api — YouTube
- LangChain Text Splitters — chunking
- Celery + Redis — asynchronous processing (background processing of heavy documents)
- MinIO (S3-compatible) — storage of originals and images
- PostgreSQL — document and chunk metadata
```

**What it demonstrates in interviews:** Experience building ETL pipelines, working with unstructured data, asynchronous processing.

---

### Module 2: Indexing & Retrieval Engine

**What it does:** Converts chunks into vectors, provides quality search across educational materials.

**Features:**

- Embedding generation (batch processing with rate limiting)
- **Hybrid Search:** vector similarity (dense) + BM25 (sparse) with Reciprocal Rank Fusion
- **Re-ranking:** cross-encoder on top of top-N results
- **Multi-query retrieval:** LLM generates 3-5 query reformulations → combines results
- **Contextual retrieval:** LLM-generated context added to each chunk during indexing (idea from Anthropic)
- Metadata filtering: source, date, topic, collection
- Multi-index: each collection/workspace has its own index

**Technologies:**

```
- Qdrant — vector DB (with multi-tenancy support via collection/payload filtering)
- Elasticsearch — BM25 search
- OpenAI Embeddings / open-source (e5-large, BGE)
- Cohere Reranker API / cross-encoder from sentence-transformers
- LangChain Retrievers — orchestration
```

**What it demonstrates:** Deep understanding of retrieval, knowledge of modern approaches (hybrid search, reranking, contextual retrieval).

---

### Module 3: Socratic Teaching Engine (system core)

**What it does:** Intelligent processing of student questions through an agent graph with three teaching modes: Socratic (guiding questions), Explain (detailed explanations), Paper Tutor (step-by-step document reading).

**Graph Architecture (LangGraph):**

```
                    ┌──────────────┐
                    │ Query Input  │
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │Query Analyzer│ — classification: homework_help /
                    │  & Router    │   concept_question / paper_tutor / quiz
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌────────────┐┌──────────┐┌───────────┐
       │ Socratic   ││ Explain  ││Paper Tutor│
       │   Mode     ││  Mode    ││   Mode    │
       │(default)   ││          ││           │
       └─────┬──────┘└────┬─────┘└─────┬─────┘
             │            │            │
             ▼            ▼            ▼
       ┌─────────────────────────────────┐
       │   Ask Guiding Question          │
       │   (Socratic)                    │
       └──────────────┬──────────────────┘
                      ▼
       ┌─────────────────────────────────┐
       │ Evaluate Student Response       │
       └──────────────┬──────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼                         ▼
   ┌──────────┐            ┌───────────┐
   │Progress  │            │ Struggling│
   │  Good    │            │ (3+ tries)│
   └────┬─────┘            └─────┬─────┘
        │                        │
        ▼                        ▼
   [Continue              [Switch to
    Socratic]              Explain Mode]
        │                        │
        └────────────┬───────────┘
                     ▼
             ┌───────────────┐
             │Format Response│
             │+ Citations    │
             │+ Images       │
             └───────────────┘
```

**Features:**

- **Socratic Mode (default):** Asks guiding questions instead of direct answers, helping students think independently
- **Explain Mode:** Detailed explanations with analogies and examples when student is stuck (3+ failed attempts)
- **Paper Tutor Mode:** Step-by-step reading of research papers/documents with comprehension questions after each section
- **Adaptive switching:** Agent automatically detects when student is "stuck" and switches to Explain
- **Manual override:** Student can explicitly request "explain to me" or "give me a hint"
- **Citation generation:** Each statement is linked to a specific source [1], [2]...
- **Multi-modal response:** Text + relevant images from textbooks (diagrams, charts)
- **Streaming:** Token-by-token via WebSocket
- **Conversation memory:** Dialog context with summarization of old messages
- **Learning analytics:** Tracking topics where student experiences difficulties

**Technologies:**

```
- LangGraph — agent graph orchestration
- LangChain — tools, chains, prompts
- OpenAI GPT-4o / Claude API — LLM
- Tavily API — web search for finding additional educational materials
```

**What it demonstrates:** Agentic AI, graph orchestration, adaptive behavior, educational AI — the hottest topics in the industry.

---

### Module 4: Multi-Modal Features

**What it does:** Works not only with text but also with images from textbooks (especially important for ML/Math courses — charts, diagrams, formulas).

**Features:**

- During parsing: image extraction + binding to text chunk
- **Image captioning:** VLM (vision-language model) generates description for each image → description is indexed in vector DB
- Image search: student query → search by descriptions → return relevant images along with text
- Display images inline in response with source and page indication

**Technologies:**

```
- GPT-4o Vision / LLaVA — image description generation
- CLIP (optional) — direct image-text matching
- MinIO/S3 — image storage
```

---

### Module 5: Smart Resource Discovery

**What it does:** Upon request from instructor or advanced student, searches for additional educational materials in external sources (tutorials, documentation, educational articles), filters them, and suggests adding to workspace.

**Features:**

- User makes a **query** directly in chat (e.g., "Find additional materials on recursion")
- Agent recognizes "Discovery" intent and calls appropriate tools (Web Search with priority on educational resources)
- **LLM-Ranking:** Model reviews found materials, evaluates their quality and relevance for learning
- **Source priority:** Official documentation, verified textbooks, educational platforms (not random articles)
- **Interactive Suggestions:** List of relevant materials with brief description is displayed in chat
- **Human-in-the-loop:** User selects "Add materials 1 and 3" → system downloads and sends them to asynchronous Ingestion Pipeline

**Technologies:**

```
- Tavily API — web search with filtering
- LangGraph — tool call orchestration
- Custom ranking logic — educational resource priority
```

---

### Module 6: Personalized Quiz Generation & Spaced Repetition

**What it does:** Every night analyzes student chat history, identifies weak areas, and generates personalized quizzes for knowledge reinforcement with spaced repetition.

**Features:**

- **Nightly analysis (Celery Beat):** Every night at 2:00 AM analyzes student activity for the last 24 hours
- **Weakness detection:** Identifies topics where student:
  - Asked many questions
  - Received Explain mode (sign of difficulties)
  - Made 3+ attempts to understand a concept
- **Quiz generation:** LLM generates 5-10 questions to reinforce weak topics
- **Question types:** Multiple choice with practical code examples
- **Spaced repetition:** Repeated quizzes after 1 day, 3 days, 7 days (spaced repetition algorithm)
- **Delivery:** Pop-up window on student's next login
- **Progress tracking:** History of completed quizzes, statistics by topic

**Technologies:**

```
- Celery Beat — task scheduler
- LLM (GPT-4o-mini) — question generation
- PostgreSQL — quiz and result storage
- Spaced repetition algorithm — SM-2 or Leitner system
```

**What it demonstrates:** Understanding of educational psychology, automated personalization, scheduled ML pipelines.

---

### Module 7: Course Workspace Management & Sharing

**What it does:** Organization of educational materials, student access management, analytics for instructors.

**Features:**

- **Workspace roles:**
  - **Owner (instructor):** Creates workspace, uploads course materials, gets invite link, sees student analytics
  - **Member (student):** Read-only access to materials, can only chat, cannot edit workspace
- **Invite system:** Instructor creates workspace → gets invite link → shares with students
- **Source management:** List of uploaded documents, processing status, ability to delete (Owner only)
- **Conversation history:** Save dialogs, ability to return
- **User feedback:** 👍/👎 on responses → saved for analysis and improvement
- **Student analytics (for instructors):**
  - Which topics cause difficulties for students
  - Frequency of Explain mode usage
  - Quiz completion rate
  - Average quiz score
- **Auth:** JWT-based authentication, workspace access control

**Technologies:**

```
- PostgreSQL + SQLAlchemy/Alembic — relational data and migrations
- JWT (python-jose) — authentication
- Pydantic — data validation
```

---

### Module 8: Evaluation & Monitoring

**What it does:** Evaluates system response quality, monitors learning effectiveness.

**Features:**

- **Offline evaluation pipeline:**
  - Automatic test dataset generation (questions on uploaded materials)
  - RAGAS metrics: Faithfulness, Answer Relevancy, Context Precision, Context Recall
  - Configuration comparison (chunk size, retrieval strategy, prompt template) — A/B testing
  - Results are saved and visualized
- **Online monitoring:**
  - LLM tracing: each call with input/output/latency/cost
  - Retrieval quality: average similarity score, percentage of queries with low score
  - User feedback analytics: percentage of positive/negative ratings
  - Socratic vs Explain ratio: how often system switches to Explain
  - Alerting: notification if quality metrics drop
- **Dashboard:** Metrics and charts

**Technologies:**

```
- RAGAS — evaluation framework
- LangFuse (open-source) or LangSmith — LLM observability and tracing
- Prometheus + Grafana (or built-in dashboard in Streamlit)
```

**What it demonstrates:** Mature approach to ML — not just "it works," but measurable and monitored. This distinguishes junior from middle+.

---

### Module 9: API Layer

**What it does:** Provides clean REST API for all functionality.

```
POST   /api/v1/workspaces
GET    /api/v1/workspaces/{id}/sources

POST   /api/v1/workspaces/{id}/chat              # ask question
GET    /api/v1/workspaces/{id}/chat/stream       # streaming (SSE)
POST   /api/v1/workspaces/{id}/chat/mode         # switch mode (socratic/explain)

POST   /api/v1/workspaces/{id}/invite            # create invite link
GET    /api/v1/workspaces/join/{code}            # join workspace

POST   /api/v1/workspaces/{id}/paper-tutor/start # start Paper Tutor
GET    /api/v1/workspaces/{id}/paper-tutor/{session_id}/next

GET    /api/v1/users/me/quizzes/pending          # get pending quizzes
POST   /api/v1/quizzes/{id}/submit               # submit quiz answers

GET    /api/v1/workspaces/{id}/analytics/students # analytics for instructor

POST   /api/v1/eval/generate-dataset             # run RAGAS
```

**Technologies:**

```
- FastAPI — API framework
- WebSocket — streaming
- Pydantic v2 — schemas
- Swagger/OpenAPI — auto-documentation
```

---

### Module 10: Frontend

**What it does:** User interface for students and instructors.

**Pages:**

1. **Chat** — Main interface with mode indicator (Socratic/Explain/Paper Tutor), streaming responses, inline images, citations
2. **Sources** — Course material management (Owner only)
3. **Quizzes** — History of completed quizzes, progress by topic, pending quizzes
4. **Analytics** — Dashboard for instructors: student statistics, popular questions, problem topics
5. **Paper Tutor** — Special interface for step-by-step document reading

**Technologies:**

```
- Streamlit — fast and sufficient for demonstration
```

---

### Module 11: Infrastructure & DevOps

**Features:**

- **Docker Compose** — entire system starts with one command (`docker-compose up`)
- **Dockerfile** for each service (multi-stage builds)
- **CI/CD:** GitHub Actions — linting, tests, Docker image builds
- **Tests:** Unit tests (pytest), integration tests for API
- **Pre-commit hooks:** ruff, mypy
- **Environment management:** .env files, dev/prod config separation
- **Makefile** — convenient commands (`make test`, `make up`, `make eval`)
- **Documentation:** README with architectural diagram, setup instructions, solution descriptions

**Technologies:**

```
- Docker + Docker Compose
- GitHub Actions
- pytest
- ruff + mypy
- Make
```

---

## Complete Tech Stack


| Category             | Technologies                                         |
| -------------------- | ---------------------------------------------------- |
| **LLM**              | OpenAI GPT-4o, Claude (via LiteLLM for abstraction) |
| **Embeddings**       | OpenAI text-embedding-3-small / open-source BGE      |
| **Orchestration**    | LangChain + LangGraph                                |
| **Vector DB**        | Qdrant                                               |
| **Search**           | Elasticsearch (BM25)                                 |
| **Reranking**        | Cohere Reranker / cross-encoder                      |
| **Backend**          | FastAPI, Pydantic v2, SQLAlchemy, Alembic            |
| **Task Queue**       | Celery + Redis                                       |
| **Database**         | PostgreSQL                                           |
| **Cache**            | Redis                                                |
| **Object Storage**   | MinIO (S3-compatible)                                |
| **Document Parsing** | Unstructured.io, PyMuPDF                             |
| **Evaluation**       | RAGAS                                                |
| **Observability**    | LangFuse (open-source)                               |
| **Frontend**         | Streamlit                                            |
| **Infrastructure**   | Docker, Docker Compose, GitHub Actions               |
| **Testing**          | pytest, httpx (async tests)                          |


---

## Implementation Plan by Phases

### Phase 1: Core RAG

- Parse PDF/DOCX → chunks → embeddings → Qdrant
- Basic retrieval + LLM generation with citations
- FastAPI endpoint for questions
- Docker Compose (FastAPI + Qdrant + PostgreSQL)

### Phase 2: Advanced Retrieval

- Hybrid search (+ Elasticsearch)
- Re-ranking
- Multi-query retrieval
- Parent-child chunking

### Phase 3: Socratic Teaching Engine

- LangGraph graph with three modes (Socratic/Explain/Paper Tutor)
- Adaptive switching logic
- Grounding check
- Streaming via WebSocket
- Learning analytics tracking

### Phase 4: Multi-Modal

- Image extraction from PDF (diagrams, charts, formulas)
- Image captioning → indexing
- Images in responses

### Phase 5: Quiz Generation & Spaced Repetition

- Celery Beat task for nightly analysis
- Weakness detection algorithm
- Quiz generation with LLM
- Spaced repetition logic
- Quiz delivery UI

### Phase 6: Workspace Sharing & Analytics

- Invite system
- Role-based access control
- Student analytics dashboard for instructors

### Phase 7: Evaluation & Monitoring

- RAGAS pipeline
- LangFuse integration
- Feedback collection
- Metrics dashboard

### Phase 8: Polish

- Streamlit frontend
- Auth
- CI/CD
- Documentation, README, architectural diagrams

---

## What Makes This Project Stand Out


| Aspect                    | What It Demonstrates                               |
| ------------------------- | -------------------------------------------------- |
| Socratic Teaching Method  | Understanding of educational AI, not just Q&A     |
| Adaptive Mode Switching   | Intelligent behavior, context-aware decisions      |
| Personalized Quiz Gen     | Automated personalization, scheduled ML            |
| Spaced Repetition         | Knowledge of educational psychology                |
| Paper Tutor Mode          | Innovative feature for advanced students           |
| Hybrid Search + Reranking | Deep understanding of retrieval                    |
| Multi-modal               | Working beyond "just text"                         |
| Evaluation (RAGAS)        | Maturity — measuring quality, not guessing         |
| Observability (LangFuse)  | Understanding of production ML                     |
| Clean API + Auth          | Backend engineering skills                         |
| Docker Compose + CI/CD    | DevOps literacy                                    |
| Structured codebase       | Readable, maintainable code                        |


---
