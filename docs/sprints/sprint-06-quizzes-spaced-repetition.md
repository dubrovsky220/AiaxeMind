# Sprint 6 — Personalized Quizzes & Spaced Repetition

## Goal

Implement **automated quiz generation** based on student performance and **spaced repetition** for long-term retention. This sprint adds the "personalization" layer that adapts to individual learning needs.

**Post-MVP Focus:** Demonstrate ML-driven personalization — a key differentiator for educational AI.

## Link to description

- **Implementation Plan:** [Phase 5: Quiz Generation & Spaced Repetition](../description.md#phase-5-quiz-generation--spaced-repetition)
- **Modules:** [Module 6: Personalized Quiz Generation & Spaced Repetition](../description.md#module-6-personalized-quiz-generation--spaced-repetition)
- **Stack:** Celery + Redis for scheduling, LLM for question generation

## Scope (in)

### 1. Weakness Detection (2-3 days)

**Analyze student activity:**
- Identify topics with low mastery scores
- Detect topics with many Explain mode switches
- Find topics with repeated questions

**Weakness scoring:**
- Simple algorithm: `weakness_score = (explain_count * 2 + failed_attempts) / total_attempts`
- Rank topics by weakness score
- Select top 3-5 topics for quiz generation

### 2. Quiz Generation (3-4 days)

**LLM-based generation:**
- Prompt: "Generate 5 multiple-choice questions on {topic} at {difficulty} level"
- Include context from course materials
- Validate questions (no duplicates, clear correct answer)

**Question types:**
- Multiple choice (4 options)
- True/False
- Short answer (optional)

**Difficulty adaptation:**
- Easy: Recall/definition questions
- Medium: Application questions
- Hard: Transfer/edge case questions

### 3. Spaced Repetition (2-3 days)

**SM-2 algorithm (simplified):**
- After quiz: calculate next review date based on performance
- Intervals: 1 day, 3 days, 7 days, 14 days, 30 days
- Adjust based on score: correct → longer interval, incorrect → shorter

**Scheduling:**
- Use Celery Beat for nightly quiz generation (2 AM)
- Check which students need quizzes
- Generate and store quizzes

### 4. Quiz Delivery & UI (2 days)

**API endpoints:**
- `GET /api/v1/quizzes/pending` — get pending quizzes
- `POST /api/v1/quizzes/{id}/submit` — submit answers
- `GET /api/v1/quizzes/history` — view past quizzes

**Streamlit UI:**
- Quiz notification on login
- Quiz interface with timer (optional)
- Results with explanations
- Progress tracking

## Out of scope

- Advanced spaced repetition (Leitner system, Anki algorithm)
- Adaptive difficulty during quiz (fixed difficulty per quiz)
- Collaborative quizzes or leaderboards

## Readiness criteria

- [ ] Weakness detection identifies struggling topics from session data
- [ ] Quiz generation creates 5 questions on a given topic
- [ ] Spaced repetition schedules next review dates
- [ ] Celery Beat runs nightly quiz generation
- [ ] UI displays pending quizzes and allows submission
- [ ] Quiz history shows past performance

## Estimated effort

**1.5 weeks** (10-12 days)

---

**Sprint label (GitHub):** `sprint:7`
