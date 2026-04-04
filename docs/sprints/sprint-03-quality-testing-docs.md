# Sprint 3 — Quality, Testing & Documentation (MVP Completion)

## Goal

Transform the working prototype from Sprint 1-2 into a **production-quality MVP**: comprehensive testing, evaluation metrics, documentation, CI/CD, and a polished UI. After this sprint, the project is **resume-ready** and **demo-ready**.

**MVP Focus:** This sprint ensures the project demonstrates professional software engineering practices — not just "it works" but "it's well-built."

## Link to description

- **Implementation Plan:** [Phase 7: Evaluation & Monitoring](../description.md#phase-7-evaluation--monitoring) + [Phase 8: Polish](../description.md#phase-8-polish)
- **Modules:** [Module 8: Evaluation & Monitoring](../description.md#module-8-evaluation--monitoring), [Module 10: Frontend](../description.md#module-10-frontend), [Module 11: Infrastructure & DevOps](../description.md#module-11-infrastructure--devops)

## Scope (in)

### 1. Testing (3-4 days)

**Unit tests:**
- Core functions: chunking, embedding, retrieval, citation formatting
- LangGraph nodes: Socratic response, Explain response, mode switching
- Target: 60-70% coverage on core logic (not 100% everywhere)

**Integration tests:**
- End-to-end: upload document → query → get answer with citations
- Mode switching: verify Socratic → Explain transition
- Grounding: test with out-of-scope questions

**Test framework:**
- `pytest` for unit/integration tests
- `httpx` for async API testing
- Mock LLM responses for deterministic tests (use `pytest-mock` or similar)

### 2. Evaluation & Metrics (2-3 days)

**Manual evaluation:**
- Create test dataset: 10-15 questions across different topics
- Evaluate responses manually: relevance, grounding, citation accuracy
- Document results in `docs/evaluation/manual-test-results.md`

**Basic RAGAS metrics (simplified):**
- **Faithfulness:** Are answers grounded in retrieved context? (manual or LLM-as-judge)
- **Answer Relevancy:** Do answers address the question? (manual scoring)
- **Citation Accuracy:** Do citations point to correct sources? (automated check)
- Target: Faithfulness >= 0.8, Relevancy >= 0.75

**Analytics dashboard (basic):**
- Simple Streamlit page showing:
  - Total sessions, questions asked
  - Socratic vs Explain mode usage ratio
  - Average response time
  - Most queried topics (keyword-based)

### 3. Documentation (2-3 days)

**README.md:**
- Project overview with value proposition
- Architecture diagram (draw.io or mermaid)
- Setup instructions (`docker compose up`)
- API documentation (link to Swagger)
- Example usage (curl commands or screenshots)
- Technology stack table

**docs/architecture.md:**
- System architecture with component diagram
- Data flow: upload → indexing → retrieval → generation
- LangGraph state machine diagram
- Database schema

**docs/examples.md:**
- 3-5 example dialogues (Socratic mode, Explain mode, mode switching)
- Screenshots of UI
- Sample API requests/responses

**API documentation:**
- Ensure FastAPI auto-generates Swagger docs
- Add descriptions to all endpoints
- Include example requests/responses

**Code documentation:**
- Docstrings for all public functions
- Inline comments for complex logic
- Type hints throughout

### 4. Frontend (Streamlit) (2-3 days)

**Pages:**
- **Chat:** Main interface with streaming responses, mode indicator, citations
- **Documents:** Upload and manage documents, view processing status
- **Analytics:** Basic dashboard (sessions, mode usage, topics)

**Features:**
- Display current mode (Socratic/Explain) with visual indicator
- Show citations as expandable sections
- Manual mode override button ("Explain this to me")
- Conversation history sidebar
- Simple, clean UI (no need for fancy design)

### 5. CI/CD & DevOps (1-2 days)

**GitHub Actions:**
- Lint: `ruff` or `flake8`
- Type check: `mypy`
- Tests: `pytest` with coverage report
- Docker build: verify image builds successfully
- Run on: push to main, pull requests

**Pre-commit hooks (optional but recommended):**
- `ruff` for linting
- `mypy` for type checking
- Auto-format with `black` or `ruff format`

**Environment management:**
- `.env.example` with all required variables
- Document environment variables in README
- Separate dev/prod configs if needed

**Makefile:**
```makefile
.PHONY: test lint up down

test:
	pytest tests/ -v --cov=src

lint:
	ruff check src/ tests/
	mypy src/

up:
	docker compose up -d

down:
	docker compose down

install:
	pip install -r requirements.txt
```

### 6. Code Quality & Refactoring (1-2 days)

- Remove dead code and TODOs
- Consistent error handling across endpoints
- Logging: structured logging with levels (INFO, ERROR)
- Configuration: centralize in `config.py` or similar
- Code formatting: run `black` or `ruff format` on entire codebase

## Out of scope

- Advanced RAGAS metrics (context precision/recall) — manual evaluation is enough
- LangFuse integration — defer to later sprints
- Full production deployment (k8s, monitoring) — Docker Compose is sufficient
- Advanced analytics (student progress tracking, quiz generation)

## Technical pointers

- **Testing:** Mock LLM calls to avoid API costs during tests
- **RAGAS:** For MVP, manual evaluation is acceptable; automated RAGAS can come later
- **Documentation:** Use mermaid diagrams in markdown for architecture
- **CI/CD:** Start simple; can enhance later

## Readiness criteria

- [ ] Test suite runs and passes (60-70% coverage on core logic)
- [ ] Manual evaluation completed: 10-15 test questions, results documented
- [ ] README is complete: setup instructions work for a new developer
- [ ] Architecture documentation exists with diagrams
- [ ] Streamlit UI works: chat, document upload, basic analytics
- [ ] CI/CD pipeline runs on GitHub Actions (lint, test, build)
- [ ] `.env.example` and Makefile exist
- [ ] Code is formatted and linted (no warnings)

## Deliverables (for resume)

After this sprint, you have:
- ✅ Working Socratic AI mentor (core value)
- ✅ Comprehensive tests (demonstrates engineering rigor)
- ✅ Evaluation metrics (demonstrates ML maturity)
- ✅ Professional documentation (README, architecture, examples)
- ✅ Clean UI (Streamlit)
- ✅ CI/CD pipeline (demonstrates DevOps knowledge)

**This is a complete, resume-ready MVP.**

## Risks and dependencies

- **Time management:** This sprint has many tasks; prioritize testing and documentation over polish
- **Evaluation:** Manual evaluation is time-consuming but necessary for credibility
- **Documentation:** Don't over-document; focus on what a hiring manager wants to see

## Estimated effort

**1.5-2 weeks** (10-14 days):
- Days 1-4: Testing (unit + integration)
- Days 5-7: Evaluation + basic metrics
- Days 8-10: Documentation (README, architecture, examples)
- Days 11-12: Streamlit UI
- Days 13-14: CI/CD, code cleanup, final polish

---

**Sprint label (GitHub):** `sprint:3`

**After this sprint: MVP is COMPLETE and ready to show employers.**
