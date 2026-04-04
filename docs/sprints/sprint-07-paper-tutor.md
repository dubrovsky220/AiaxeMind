# Sprint 7 — Paper Tutor & Advanced Teaching Modes

## Goal

Add **Paper Tutor mode** for step-by-step reading of research papers and technical documents, plus **enhanced Socratic features** like hint system and progress tracking.

**Post-MVP Focus:** Differentiate from basic chatbots — advanced teaching features for serious learners.

## Link to description

- **Implementation Plan:** [Phase 3: Socratic Teaching Engine](../description.md#phase-3-socratic-teaching-engine) (Paper Tutor mode)
- **Modules:** [Module 3: Socratic Teaching Engine](../description.md#module-3-socratic-teaching-engine-system-core)

## Scope (in)

### 1. Paper Tutor Mode (3-4 days)

**Section-by-section reading:**
- Parse document into logical sections (by headers, page breaks)
- Present one section at a time
- Ask comprehension questions after each section
- Track progress through document

**Comprehension checks:**
- Generate 1-2 questions per section
- Verify understanding before moving to next section
- Adaptive: if student struggles, provide summary before continuing

**API endpoints:**
- `POST /api/v1/paper-tutor/start` — start Paper Tutor session
- `GET /api/v1/paper-tutor/{session_id}/next` — get next section + questions
- `POST /api/v1/paper-tutor/{session_id}/answer` — submit answer, get feedback

### 2. Hint System (2 days)

**Progressive hints:**
- Level 1: Gentle nudge ("Think about what we learned in Chapter 2")
- Level 2: More specific ("Consider the base case in recursion")
- Level 3: Almost the answer ("What happens when n=0?")

**Hint budget:**
- Track hints used per question
- Limit to 3 hints per question
- Store hint usage in analytics

### 3. Progress Tracking (2-3 days)

**Student progress model:**
- Track topics covered, questions answered, hints used
- Simple mastery score: correct_answers / total_attempts per topic
- Visualize progress in UI

**Session history:**
- Store all sessions with metadata
- Allow student to resume previous sessions
- Show learning trajectory over time

### 4. Enhanced Socratic Features (2 days)

**Follow-up questions:**
- After correct answer, ask deeper question ("Why does that work?")
- Build on previous answers in conversation

**Mistake analysis:**
- Identify common misconceptions from wrong answers
- Provide targeted explanations

**Encouragement:**
- Positive reinforcement for progress
- Motivational messages when struggling

## Out of scope

- Automated quiz generation (Sprint 7)
- Spaced repetition (Sprint 7)
- Instructor analytics dashboard (Sprint 8)
- Multi-user workspace features (Sprint 8)

## Readiness criteria

- [ ] Paper Tutor mode works end-to-end for a sample research paper
- [ ] Comprehension questions are generated and evaluated
- [ ] Hint system provides 3 levels of progressive hints
- [ ] Progress tracking shows topics covered and mastery scores
- [ ] UI displays Paper Tutor interface and progress visualization
- [ ] Session history allows resuming previous sessions

## Estimated effort

**1.5 weeks** (10-12 days)

---

**Sprint label (GitHub):** `sprint:6`
