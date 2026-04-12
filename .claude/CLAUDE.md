# AGENTS.md

## Project Vision

**AiaxeMind** is a Socratic AI Mentor for online programming and Data Science schools. Instead of giving direct answers, it asks guiding questions to help students think independently. The system adapts its teaching approach based on student progress and generates personalized quizzes.

**Core Innovation:** Adaptive teaching that switches between Socratic questioning, detailed explanations, and step-by-step guidance based on real-time assessment of student understanding.

## Project Status

**Phase:** Pre-development / Planning  
**Methodology:** Agile Scrum (sprint length flexible; see sprint files)  
**Target:** MVP in 4-5 weeks (Sprints 1-3), full system in 9-12 weeks (Sprints 1-8)

## Key Documentation

- `docs/description.md` - Product vision, modules, tech stack, phased roadmap (primary source of scope)
- `docs/sprints/` - Per-sprint scope and readiness criteria (`README.md` + `sprint-01` … `sprint-08`)
- `docs/mvp-strategy.md` - **MVP strategy and recommendations** (read this first!)
- `docs/agile.md` - Git workflow, GitHub Issues, sprint planning from sprint files
- `github-issues` - Skill for working with GitHub Issues

**Important:** These docs are guidelines, not rigid specifications. Feel free to suggest better approaches.

**Task Management:** Work is tracked in **GitHub Issues**, created from the active **`docs/sprints/sprint-0N-*.md`** file. Implementation details live in issues and PRs unless you add focused ADRs.

**Project Context:** This is a **resume/portfolio project**. The goal is to demonstrate modern AI engineering skills, not build a production system. Prioritize working demos, clean code, and good documentation over perfect algorithms or scalability.

## Development Principles

### 1. Agile Mindset

- **Iterate quickly:** Working code > perfect architecture
- **Adapt freely:** If a technology doesn't fit, propose alternatives
- **MVP first:** Focus on core value, add features incrementally
- **Fail fast:** Test assumptions early, pivot when needed

### 2. Decision Making

When facing technical choices:

1. **Consult docs first:** Check `docs/description.md` and the current `docs/sprints/sprint-*.md`
2. **Evaluate tradeoffs:** Consider complexity, time, maintainability
3. **Propose alternatives:** If you see a better way, explain why
4. **Document decisions:** Update docs when making significant changes

If a change requires modifying the database schema or introducing a new major dependency (like a message broker), **STOP and ask for explicit user confirmation** before writing code.

### 3. Code Quality

- **Readable > clever:** Write code that's easy to understand
- **Test what matters:** Focus on business logic, not boilerplate
- **Type hints:** Use them for clarity, not ceremony
- **Comments:** Explain "why", not "what"

### 4. Working with AI Agents

**You are encouraged to:**

- Question architectural decisions in the docs
- Suggest simpler implementations
- Propose technology swaps if justified
- Refactor as you learn more about the domain

**You should:**

- Explain your reasoning when deviating from docs
- Update documentation after significant changes
- Keep changes focused (one task at a time)
- Write tests for critical paths

## Git Workflow

**All tasks are tracked as GitHub Issues.** See `docs/agile.md` for complete workflow.

### Branch Naming

```
<type>/#<issue-number>-<description>

Examples:
feat/#42-document-parsing
fix/#58-retrieval-bug
chore/#35-add-dependencies
```

### Commit Format

```
<type>(<scope>): [#<issue>] <description>

Examples:
feat(api): [#42] add source upload endpoint
fix(retrieval): [#58] correct similarity threshold
chore(docker): [#35] add qdrant service to compose
```

**Types:** feat, fix, chore, docs, test, refactor

### Pull Requests

- Title: `[#<issue>] Short description`
- Description: Use "Closes #<issue>" to link PR to issue
- Keep PRs focused and reviewable

### GitHub Issues Workflow

**Collaborative Planning Mode (MANDATORY):**

When starting a sprint, use this collaborative process. **DO NOT create issues without discussion.**

1. **User initiates:** "Let's plan Sprint N" or "Discuss tasks for Sprint N"

2. **Agent analyzes sprint file:** Read `docs/sprints/sprint-0N-*.md` and break down scope into 3-15 tasks

3. **Discuss EACH task individually:** For every task, agent MUST propose:
   - **Technologies and libraries** (with 2-3 alternatives and tradeoffs)
   - **Architecture approach** (module structure, design patterns)
   - **API endpoints** (if applicable, with request/response schemas)
   - **Database schemas** (if applicable, with table structure)
   - **Acceptance criteria** (specific, testable conditions)
   - **Estimated effort** (hours or days)
   - **Trade-offs and recommendations** (pros/cons of each approach)

4. **User decides:** Approves, modifies, or suggests alternatives for EACH task

5. **Agent creates issue:** Only after user approval, create GitHub Issue with all agreed details

**Example dialogue:**
```
User: "Let's plan Sprint 1"

Agent: "I've analyzed sprint-01-core-rag.md. The sprint has 7 main tasks. 
        Let's discuss each one.

        **Task 1: Document Parsing**
        
        Technology options:
        1. pdfplumber (PDF) + python-docx (DOCX)
           - Pros: Lightweight, simple API, good for text extraction
           - Cons: Limited table/image support
           
        2. unstructured.io
           - Pros: Universal parser, handles tables/images, production-ready
           - Cons: Heavier dependency, more complex setup
           
        3. PyMuPDF (fitz) + python-docx
           - Pros: Fast, good image extraction
           - Cons: More manual work for text extraction
        
        My recommendation: Start with pdfplumber + python-docx for MVP simplicity.
        Switch to unstructured.io in Sprint 5 if we need image extraction.
        
        Architecture:
        - Module: src/ingestion/parsers/
        - Classes: PDFParser, DOCXParser, BaseParser (interface)
        
        API endpoint:
        - POST /api/v1/documents/upload
        - Request: multipart/form-data with file
        - Response: {document_id, status, chunk_count}
        
        Acceptance criteria:
        - [ ] Can parse PDF and extract text
        - [ ] Can parse DOCX and extract text
        - [ ] Returns document metadata (title, page count)
        - [ ] Handles errors gracefully (invalid file, unsupported format)
        
        Estimated effort: 1-2 days
        
        What do you think? Any changes or preferences?"

User: "Let's use PyMuPDF instead, I want image extraction from the start"

Agent: "Good call! PyMuPDF gives us image extraction capability early.
        Updated approach:
        - PyMuPDF (fitz) for PDF (text + images)
        - python-docx for DOCX
        
        I'll add image extraction to acceptance criteria:
        - [ ] Extract images from PDF with metadata (page, position)
        
        This sets us up well for Sprint 5 (Multi-modal).
        
        Should I create the issue now, or discuss the next task first?"

User: "Create the issue"

Agent: [Creates issue via gh CLI with all agreed details]

Agent: "Issue #1 created. Ready to discuss Task 2: Chunking Strategy?"
```

**Key principles:**
- **Always discuss before creating issues**
- **Propose multiple alternatives** (not just one option)
- **Explain tradeoffs** (pros/cons, complexity, time)
- **Wait for user approval** before creating issues
- **One task at a time** (don't rush through all tasks)

**GitHub Issues Skill:**

Use the `github-issues` skill to fetch issue details or batch-create issues from a finalized plan.

Examples:
```
Get issue #42 details
Show me issue 58
```

## Core Architecture Concepts

### High-Level Flow

```
User uploads documents → Parse & chunk → Embed & index
Student asks question → Retrieve context → LLM generates response
System analyzes struggles → Generate personalized quizzes
```

### Key Components (Flexible)

1. **Document Processing:** Parse various formats, chunk intelligently
2. **Retrieval:** Find relevant content (vector search + keyword search)
3. **Teaching Engine:** Adaptive responses based on student progress
4. **Quiz Generation:** Automated personalization based on weak areas
5. **Workspace Management:** Multi-user with role-based access

### Technology Suggestions (Not Requirements)

The docs suggest specific technologies, but you can propose alternatives:

- **Backend:** FastAPI is suggested, but Flask/Django are fine if you prefer
- **Vector DB:** Qdrant is mentioned, but Pinecone/Weaviate/Chroma work too
- **LLM Framework:** LangChain/LangGraph suggested, but direct API calls are okay
- **Frontend:** Streamlit for speed, but React/Vue if you want more control
- **Database:** PostgreSQL suggested, but any relational DB works

**When to swap:** If you have good reasons (simpler, faster, better fit), propose it.

## Task Execution Guide

### Starting a Task

1. **Find your task in GitHub Issues:**
   ```bash
   gh issue list --label "sprint:1"
   gh issue view 42
   ```

2. **Review context:**
   - Acceptance criteria on the issue
   - The matching **`docs/sprints/sprint-0N-*.md`** for sprint-level scope and readiness criteria
   - `docs/description.md` for product constraints and stack hints

3. Ask questions if requirements are unclear

### During Implementation

- Focus on acceptance criteria from the GitHub Issue
- Write tests as you go (not at the end)
- Commit frequently with clear messages: `feat(scope): [#42] description`
- Update docs if you change architecture
- Add comments to issue for progress updates

### Completing a Task

- Verify all acceptance criteria met (check off items in issue)
- Run tests and linting
- Update relevant documentation
- Create PR with "Closes #<issue>" in description
- PR merge will automatically close the issue

## Common Scenarios

### "The docs suggest X, but Y is simpler"

**Do this:**

```
I see docs/description.md / the sprint file suggests X for [feature].
However, Y would be simpler because [reasons].
Tradeoffs: [list pros/cons]
Recommendation: Use Y for MVP, can switch to X later if needed.
Proceeding with Y unless you object.
```

### "This task is too large"

**Do this:**

```
Issue #42 has [N] subtasks and seems too large for one PR.
Suggest splitting into:
- Subset 1: [description]
- Subset 2: [description]
This allows faster iteration and easier review.
We can create separate issues for each subset.
```

### "Requirements are unclear"

**Do this:**

```
Issue #42 acceptance criteria says [quote].
This is ambiguous because [reason].
Clarifying questions:
1. [Question 1]
2. [Question 2]
Proposed interpretation: [your understanding]
```

Add your questions as a comment on the GitHub Issue for visibility.

## Testing Philosophy

- **Unit tests:** For complex business logic
- **Integration tests:** For critical user flows
- **Manual testing:** For UI/UX
- **Don't over-test:** Focus on what breaks often

**Coverage target:** 60-70% for core logic (not 100% everywhere)

## Documentation Updates

Update docs when you:

- Change architecture significantly
- Add/remove major features
- Swap technologies
- Learn something important about the domain

**Keep docs in sync with reality, not aspirations.**

## Anti-Patterns to Avoid

❌ **Over-engineering:** Don't build for scale you don't need yet  
❌ **Premature optimization:** Make it work, then make it fast  
❌ **Analysis paralysis:** Choose something and iterate  
❌ **Silent changes:** Document when you deviate from plan  
❌ **Big bang PRs:** Keep changes small and focused
❌ **Library Hallucinations**: Always verify library methods and imports against their latest documentation before using them, especially for fast-moving tools like LangChain and LangGraph. Use content7 MCP to get up-to-date, version-specific documentation and code examples.

## Success Metrics

You're doing well if:

- ✅ Code works and meets acceptance criteria
- ✅ Tests cover critical paths
- ✅ Documentation reflects reality
- ✅ Changes are explained and justified
- ✅ You're making steady progress

## Questions?

When in doubt:

1. Check `docs/` for guidance
2. Look at existing code for patterns
3. Ask clarifying questions
4. Propose a solution with reasoning

**Remember:** This is an Agile project. Adapt, iterate, improve. The docs are a starting point, not a prison.
---

## Sprint Planning Best Practices

### Before Starting a Sprint

1. **Read the sprint file thoroughly:** Understand scope, out-of-scope, and readiness criteria
2. **Check `docs/mvp-strategy.md`:** Understand simplifications and MVP focus
3. **Review previous sprint outcomes:** Learn from what worked/didn't work

### During Sprint Planning Discussion

**For each task, discuss in this order:**

1. **Technology choices:**
   - Present 2-3 alternatives with clear pros/cons
   - Consider: complexity, learning curve, time to implement, maintainability
   - Recommend one option with reasoning
   - Example: "For embeddings, I recommend OpenAI text-embedding-3-small (simple, fast) over open-source BGE (requires more setup). We can switch later if cost becomes an issue."

2. **Architecture approach:**
   - Propose module structure
   - Identify design patterns (if applicable)
   - Consider: separation of concerns, testability, extensibility
   - Example: "I suggest a Parser interface with PDFParser and DOCXParser implementations. This makes it easy to add new formats later."

3. **API design (if applicable):**
   - Propose endpoint path and HTTP method
   - Define request/response schemas
   - Consider: RESTful conventions, error handling, validation
   - Example: "POST /api/v1/documents/upload with multipart/form-data. Returns {document_id, status, chunk_count} or 400 with error details."

4. **Database schema (if applicable):**
   - Propose table structure with columns and types
   - Identify relationships and indexes
   - Consider: normalization, query patterns, future extensibility
   - Example: "documents table: id (uuid), filename (text), upload_date (timestamp), status (enum). Index on status for filtering."

5. **Acceptance criteria:**
   - Make them specific and testable
   - Include both happy path and error cases
   - Consider: functionality, error handling, performance
   - Example: "[ ] Can parse PDF with 100+ pages in <30 seconds [ ] Returns 400 for invalid file types [ ] Extracts metadata (title, author, page count)"

6. **Effort estimation:**
   - Break down into sub-tasks if helpful
   - Account for learning time if new technology
   - Be realistic: include testing, debugging, documentation time
   - Example: "2-3 days: 1 day learning PyMuPDF, 1 day implementation, 0.5 day testing"

### What Makes a Good Discussion

**Good:**
- "For chunking, I see three approaches: recursive (simple), semantic (better quality), or parent-child (best context). For MVP, I recommend recursive with chunk_size=512, overlap=64. We can upgrade to semantic in Sprint 4 if needed. Thoughts?"

**Bad:**
- "I'll use recursive chunking." (No alternatives, no reasoning)

**Good:**
- "For the database, we could use PostgreSQL (production-like) or SQLite (simpler for MVP). PostgreSQL requires Docker setup but gives us better tooling. SQLite is one file, zero config. For MVP, I lean toward SQLite unless you want production parity. What do you prefer?"

**Bad:**
- "I'll use PostgreSQL." (No discussion of tradeoffs)

### Handling Disagreements

If user suggests a different approach:
1. Acknowledge their suggestion
2. Ask clarifying questions if needed
3. Discuss tradeoffs of their approach vs yours
4. Defer to user's preference (it's their project)
5. Document the decision and reasoning

Example:
```
User: "Let's use Pinecone instead of Qdrant"
Agent: "Pinecone is a solid choice. Key differences:
        - Pinecone: Managed service, easier setup, but costs money and requires API key
        - Qdrant: Self-hosted, free, full control, but requires Docker
        
        For a pet project, Qdrant might be better (shows you can deploy infrastructure).
        But if you want to focus on application logic and skip DevOps, Pinecone works.
        
        Which aspect do you want to emphasize in your resume?"
```

### After Planning is Complete

1. **Summarize decisions:** List all tasks with chosen technologies
2. **Confirm before creating issues:** "Ready to create 7 issues for Sprint 1?"
3. **Create issues one by one:** Use `gh issue create` with full details
4. **Update sprint tracking:** Mark sprint as "In Progress" in `docs/sprints/README.md`


**Last Updated:** April 2, 2026  
**Status:** Pre-development



Let's build something great! 🚀
