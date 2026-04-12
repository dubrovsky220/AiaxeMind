---
name: github-issues
description: Create GitHub Issues from sprint files and fetch issues for work
compatibility: opencode
metadata:
  audience: developers
  workflow: github
---

## What I do

- Break down **`docs/sprints/sprint-*.md`** into GitHub Issues (or help you do it)
- Fetch issue details from GitHub for working on tasks
- Create properly formatted issues with labels and acceptance criteria
- Link issues to the sprint file and `sprint:N` label (N = 1…8)

## When to use me

**Create issues from a sprint file:**

- When starting a new sprint and need issues on GitHub
- Example: "Create issues from docs/sprints/sprint-01-core-rag.md"

**Fetch issue for work:**

- When you need full task details before starting work
- Example: "Get issue #42 details" or "Show me issue 42"

## How I work

### Creating issues from a sprint

When you ask to import or create issues from a sprint:

1. **Read the sprint file** (e.g. `docs/sprints/sprint-03-socratic-engine.md`) for **Goal**, **Scope**, **Readiness criteria**, **Out of scope**.
2. **Split** scope into a small set of issues (often 3–15) with clear, testable acceptance criteria — see [`docs/agile.md`](../../../docs/agile.md) for the issue template.
3. **Create GitHub Issues** with:
   - Title: `[Sprint N] Short description`
   - Labels: `sprint:N` (match the sprint file), `type:feat|fix|chore|...`, `priority:high|medium|low`
   - Body: Summary, sprint file reference, description, acceptance criteria (see agile.md)
4. **Report** created issue numbers and links.

### Fetching issue details

1. Run **`gh issue view <number>`** (and JSON if needed).
2. Show title, labels, body, and link to sprint file if mentioned.

## Prerequisites

- Git repository initialized
- GitHub CLI (`gh`) installed and authenticated
- GitHub remote configured and write access for issues

## Sprint file format

Sprint files live under **`docs/sprints/`**. Each includes sections such as **Goal**, **Link to description**, **Scope (in)**, **Out of scope**, **Readiness criteria**, **Sprint label**. Product context is in **`docs/description.md`**.

## GitHub Issue format

Follow **[`docs/agile.md`](../../../docs/agile.md)** — Issue template section.

## Example usage

**Create issues from a sprint:**

```
User: Create GitHub issues from docs/sprints/sprint-01-core-rag.md
User: Break sprint 2 into issues
```

**Fetch issue details:**

```
User: Get issue #42
User: Show me issue 42 details
```

## Error handling

- Git / `gh` not configured: guide through setup
- Sprint file missing: point to `docs/sprints/README.md`
- Issue not found: verify number
- API rate limits: wait and retry

## Best practices

1. One sprint file per phase; label issues **`sprint:N`** consistently with that file.
2. After creating issues, verify on GitHub.
3. Reference the sprint file path in the issue body for traceability.
4. Do not recreate a full monolithic task list in repo — **scope lives in the sprint file + Issues**.

## Limitations

- One-way: Issues are not synced back into markdown automatically
- Re-importing the same scope can duplicate issues — prefer creating missing issues manually or de-dupe on GitHub
