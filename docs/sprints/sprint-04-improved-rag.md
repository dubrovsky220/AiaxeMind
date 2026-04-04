# Sprint 4 — Improved RAG (Retrieval Optimization)

## Goal

Enhance retrieval quality through **re-ranking**, **query optimization**, and **better chunking strategies**. This sprint makes answers more relevant and accurate without adding complex infrastructure like Elasticsearch.

**Post-MVP Focus:** Improve the foundation — better retrieval = better teaching quality.

## Link to description

- **Implementation Plan:** [Phase 2: Advanced Retrieval](../description.md#phase-2-advanced-retrieval)
- **Modules:** [Module 2: Indexing & Retrieval](../description.md#module-2-indexing--retrieval-engine)
- **Stack:** sentence-transformers for re-ranking, LangChain retrievers

## Scope (in)

### 1. Re-ranking (2-3 days)

**Cross-encoder re-ranking:**
- Use `sentence-transformers` cross-encoder (e.g., `BAAI/bge-reranker-base`)
- Retrieve top-10 candidates from Qdrant
- Re-rank to top-3 most relevant
- Measure improvement vs Sprint 1 baseline

**Implementation:**
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('BAAI/bge-reranker-base')
scores = reranker.predict([(query, doc) for doc in candidates])
top_docs = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:3]
```

### 2. Query Optimization (2-3 days)

**Query expansion:**
- Generate 2-3 query variations (synonyms, rephrasing)
- Simple approach: use LLM to rephrase query
- Retrieve with all variations, deduplicate results

**Query classification:**
- Detect query type: definition, how-to, example, debugging
- Adjust retrieval parameters based on type (e.g., more chunks for how-to)

**Fallback handling:**
- If retrieval score < threshold (e.g., 0.6), trigger web search (Tavily API) as fallback
- Or return "I don't have information about this in the course materials"

### 3. Improved Chunking (2-3 days)

**Semantic chunking:**
- Use `SemanticChunker` from LangChain (splits by semantic similarity)
- Compare with recursive chunking from Sprint 1
- Document which works better for educational content

**Chunk metadata enrichment:**
- Add section headers to chunks (e.g., "Chapter 3: Recursion")
- Add document summary to each chunk's metadata
- Improves context for LLM generation

**Optimal parameters:**
- Experiment with chunk_size: 256, 512, 1024
- Experiment with overlap: 32, 64, 128
- Document findings in `docs/retrieval-tuning.md`

### 4. Retrieval Evaluation (1-2 days)

**Create evaluation dataset:**
- 20-30 questions with known relevant chunks
- Manually label which chunks should be retrieved

**Metrics:**
- **Precision@3:** How many of top-3 are relevant?
- **Recall@10:** Are all relevant chunks in top-10?
- **MRR (Mean Reciprocal Rank):** Position of first relevant chunk

**Compare:**
- Baseline (Sprint 1): vector search only
- With re-ranking
- With query expansion
- With semantic chunking

### 5. Performance Optimization (1 day)

**Caching:**
- Cache embeddings for common queries
- Cache re-ranking results
- Use Redis or in-memory cache

**Batch processing:**
- Batch embedding generation during upload
- Batch re-ranking for multiple queries

## Out of scope

- Elasticsearch / BM25 hybrid search (too complex for incremental improvement)
- Parent-child chunking (defer to later)
- Multi-query retrieval with LLM (query expansion is simpler)
- Contextual retrieval (Anthropic-style) — defer to later

## Technical pointers

- **Re-ranking:** `BAAI/bge-reranker-base` is small and fast; `BAAI/bge-reranker-large` is more accurate but slower
- **Query expansion:** Simple LLM prompt: "Rephrase this question in 2 different ways: {query}"
- **Semantic chunking:** May not always be better than recursive; test on your data
- **Evaluation:** Manual labeling is tedious but necessary for credibility

## Readiness criteria

- [ ] Re-ranking is implemented and measurably improves relevance (Precision@3 increases by 10-20%)
- [ ] Query expansion works for at least 3 test cases
- [ ] Semantic chunking is tested and compared with recursive chunking
- [ ] Retrieval evaluation completed: 20-30 questions, metrics documented
- [ ] Performance optimization: caching reduces latency by 20-30%
- [ ] Findings documented in `docs/retrieval-tuning.md`

## Risks and dependencies

- **Evaluation effort:** Manual labeling is time-consuming
- **Diminishing returns:** Re-ranking may not dramatically improve results if base retrieval is already good
- **Model size:** Cross-encoder adds latency; measure and document

## Estimated effort

**1-1.5 weeks** (7-10 days):
- Days 1-3: Re-ranking implementation and testing
- Days 4-6: Query optimization and chunking experiments
- Days 7-8: Retrieval evaluation
- Days 9-10: Performance optimization and documentation

---

**Sprint label (GitHub):** `sprint:4`
