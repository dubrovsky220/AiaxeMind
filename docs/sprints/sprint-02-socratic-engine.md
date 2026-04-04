# Sprint 2 — Socratic Teaching Engine

## Goal

Implement the **core teaching agent**: **LangGraph** with **Socratic** and **Explain** modes; **adaptive switching**; **streaming** responses; **conversation memory**. This sprint delivers the main value proposition — an AI that teaches through questioning, not direct answers.

**MVP Focus:** This is the heart of the project — what makes it unique. After this sprint, you have a working Socratic AI mentor.

## Link to description

- **Implementation Plan:** [Phase 3: Socratic Teaching Engine](../description.md#phase-3-socratic-teaching-engine)
- **Modules:** [Module 3: Socratic Teaching Engine](../description.md#module-3-socratic-teaching-engine-system-core)
- **Stack:** LangGraph, LangChain, LLM API; SSE (Server-Sent Events) for streaming.

## Scope (in)

1. **Two teaching modes:**
   - **Socratic mode (default):** Ask guiding questions to help student think independently
   - **Explain mode (fallback):** Provide detailed explanations when student is stuck

2. **Adaptive switching logic:**
   - Track student struggle signals (failed attempts, "I don't know", repeated questions)
   - Switch to Explain mode after 2-3 failed attempts
   - Return to Socratic mode after successful explanation
   - Manual override: student can request "explain" or "hint"

3. **LangGraph implementation:**
   - State machine with nodes: `analyze_question` → `socratic_response` / `explain_response` → `check_understanding`
   - State tracking: current_mode, attempt_count, question_history, skill_context
   - Simple routing logic (no complex multi-agent coordination yet)

4. **Grounding checks:**
   - LLM judges if response is grounded in retrieved context
   - Fallback to "I don't have information about that in the course materials" if not grounded

5. **Streaming responses:**
   - SSE (Server-Sent Events) for token-by-token delivery
   - Endpoint: `GET /api/v1/chat/stream`

6. **Conversation memory:**
   - Store last 10 messages in session state
   - Simple windowing (no summarization yet)
   - Persist conversation history to database

7. **Basic analytics tracking:**
   - Log: session_id, mode_used, attempt_count, topic (keyword-based)
   - Store in PostgreSQL for later analysis
   - Minimal schema: `sessions`, `interactions`, `mode_switches`

8. **Prompt engineering:**
   - Craft effective Socratic prompts (ask questions, don't give answers)
   - Craft effective Explain prompts (detailed, with examples)
   - Document prompts in code or separate files

## Out of scope

- Paper Tutor mode (defer to Sprint 6)
- Complex query routing (homework vs concept vs quiz) — simple classification is enough
- Multi-query retrieval (Sprint 4)
- WebSocket (SSE is simpler for MVP)
- Advanced memory (summarization, long-term memory)
- Skill taxonomy and mastery tracking (simplified to attempt counter)

## Technical pointers

- **LangGraph:** Start with simple state machine; avoid over-engineering
- **Socratic prompts:** Study examples from MetaMind or similar projects
- **Switching logic:** Simple rule-based (if attempt_count >= 3: switch to Explain)
- **Grounding:** Use LLM to judge: "Is this answer supported by the context? Yes/No"
- **SSE:** FastAPI supports SSE via `StreamingResponse`

## Readiness criteria

- [ ] Socratic mode asks guiding questions (test on 3-5 sample questions from different topics)
- [ ] Explain mode provides detailed explanations with examples
- [ ] Adaptive switching works: after 2-3 failed attempts, mode switches to Explain
- [ ] Manual override works: student can type "explain this" or "give me a hint"
- [ ] Grounding check prevents hallucinations (test with out-of-scope questions)
- [ ] Streaming works in a simple test client (curl or Streamlit)
- [ ] Conversation history is stored and used for context
- [ ] Analytics table has data: session_id, mode, attempt_count, timestamp

## Risks and dependencies

- **Prompt quality:** Socratic prompts are hard to get right — iterate based on testing
- **LangGraph learning curve:** Budget 2-3 days for learning if unfamiliar
- **Grounding accuracy:** LLM-based grounding is not perfect; document limitations
- **Next sprint** depends on working conversation flow for testing and evaluation

## Estimated effort

**1.5-2 weeks** (10-14 days):
- Days 1-3: Learn LangGraph, design state machine
- Days 4-6: Implement Socratic mode with prompts
- Days 7-9: Implement Explain mode and switching logic
- Days 10-12: Add streaming, grounding, memory
- Days 13-14: Testing, prompt refinement, analytics

## Example interaction (for testing)

**Socratic mode:**
```
Student: "How does recursion work?"
AI: "Great question! Let's explore this together. What happens when a function calls itself?"
Student: "It runs again?"
AI: "Exactly! Now, what do you think we need to prevent it from running forever?"
Student: "I don't know"
AI: "Think about loops — how do we stop a loop from running infinitely?"
Student: "A condition?"
AI: "Perfect! That's called a base case in recursion. Can you think of an example?"
```

**Explain mode (after 3 failed attempts):**
```
AI: "I see this concept is challenging. Let me explain step by step.

Recursion is when a function calls itself. It has two key parts:
1. Base case: The condition that stops the recursion
2. Recursive case: The function calling itself with modified parameters

Here's a simple example with factorial:
[code example with detailed explanation]

Does this make sense? Try explaining it back to me in your own words."
```

---

**Sprint label (GitHub):** `sprint:2`
