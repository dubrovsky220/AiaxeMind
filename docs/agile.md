# Agile & Git workflow

Reference for Scrum-style delivery, **GitHub Issues** as the system of record, and Git/GitHub practices for AiaxeMind.

---

## Documentation and planning hierarchy

| Layer | Source |
|--------|--------|
| Product vision, modules, tech stack, phased roadmap | [`description.md`](description.md) |
| **Per-sprint scope and readiness** (8 sprints = 8 phases) | [`sprints/README.md`](sprints/README.md) and [`sprints/sprint-NN-*.md`](sprints/) |
| **Executable work** | **GitHub Issues** (created from the current sprint file) |

Sprint **length is not fixed**: close a sprint when the **readiness criteria** in the corresponding `docs/sprints/sprint-*.md` are met (or explicitly moved to the next sprint).

---

## Agile structure

- **Sprint:** One increment aligned with a phase; tracked with label `sprint:N` where **N is 1–8** (see [`sprints/README.md`](sprints/README.md)).
- **Backlog:** GitHub Issues; scope for the active sprint comes from **`docs/sprints/sprint-0N-*.md`**.
- **Definition of Done:** Acceptance criteria in the issue met; tests and lint pass as required; PR merged; sprint file criteria updated or deferred intentionally.

---

## GitHub Issues workflow

All implementation work is tracked as **GitHub Issues**. Use labels:

- **Sprint labels:** `sprint:1` … `sprint:8` (match the sprint file for that phase).
- **Type labels:** `type:feat`, `type:fix`, `type:chore`, `type:docs`, `type:test`, `type:refactor`
- **Priority labels:** `priority:high`, `priority:medium`, `priority:low`

### Finding work

```bash
# Issues for sprint 3
gh issue list --label "sprint:3"

# Assigned to you
gh issue list --assignee @me

# One issue
gh issue view 42

gh issue list --search "retrieval"
```

---

## Sprint planning (from sprint files)

### Before the sprint

1. Open **[`docs/sprints/README.md`](sprints/README.md)** and the **`sprint-0N-*.md`** file for the phase you are starting.
2. Adjust **scope** or **readiness criteria** in that file if reality requires it (keep the file as the single narrative for “what this sprint means”).
3. **Create GitHub Issues** by breaking down **Scope** and **Readiness criteria** into deliverable chunks (often 3–15 issues per sprint).
4. Label each issue `sprint:N`, `type:*`, `priority:*`.
5. Assign owners as needed.

### During the sprint

1. Pick work from issues labeled your current `sprint:N`.
2. Branch from `main`, implement, open PR with **`Closes #issue`**.
3. Put **design notes** (API shape, schema snippets, prompts) in the **issue or PR**, unless you add a small ADR later.

### Closing the sprint

1. Verify every **Readiness criterion** in `sprint-0N-*.md` is satisfied or consciously deferred (if deferred, edit the **next** sprint file and/or create follow-up issues).
2. Close or re-label unfinished issues to the next sprint:
   ```bash
   gh issue edit 42 --remove-label "sprint:3" --add-label "sprint:4"
   ```

---

## Issue template

Use this shape when creating issues (adjust sections as needed):

```markdown
## Summary
One line: what to deliver.

## Sprint context
- Sprint file: `docs/sprints/sprint-0N-....md`
- Related phase: [name from description.md]

## Description
What to build and why.

## Acceptance criteria
- [ ] Criterion 1 (testable)
- [ ] Criterion 2

## Notes (optional)
Implementation hints, links to PRs, API sketches.
```

Title convention (recommended): `Short description`

---

## Git workflow

**Do not commit directly to `main`.** Use feature branches tied to an issue.

### Branch naming

Format: `<type>/#<issue-number>-<description>`

Types: `feat/`, `fix/`, `chore/`, `docs/`, `refactor/`, `test/`

Examples:

```bash
git checkout -b feat/#42-hybrid-retrieval
```

### Workflow steps

1. `gh issue view <N>` and assign yourself if needed: `gh issue edit <N> --add-assignee @me`
2. `git checkout main && git pull origin main`
3. `git checkout -b feat/#<issue>-short-description`
4. Small, logical commits
5. Push and open PR: `gh pr create --title "[#<issue>] Short description" --body "Closes #<issue>"`
6. Prefer **Squash and Merge**, then delete the branch

---

## Commit messages

Format: `<type>(<scope>): [#<issue>] <subject>`

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`

Optional scope: `api`, `db`, `retrieval`, `teaching`, `ingest`, `frontend`, `docker`

Examples:

```bash
feat(api): [#42] add hybrid retrieval endpoint
fix(retrieval): [#58] correct fusion weights
```

Rules: imperative mood; about 72 characters; no trailing period; always `#[issue]`.

---

## Pull requests

### Title

`[#<issue>] Short description`

### Description template

```markdown
## Task
Closes #<issue-number>

## Changes
- Change 1
- Change 2

## Deviations from Plan
[If any — explain why]

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests passing
- [ ] Manual testing performed
- [ ] Linting passing
```

Keep PRs reviewable (smaller is better).

---

## Quick reference

```bash
gh issue list --label "sprint:1"
gh issue view 42
git checkout main && git pull && git checkout -b feat/#42-short-name
git commit -m "feat(api): [#42] add endpoint"
git push origin feat/#42-short-name
gh pr create --title "[#42] Short description" --body "Closes #42"
```

### Pre-commit checks

Run before pushing when the repo provides them:

```bash
make lint
make test
```

(or `ruff`, `mypy`, `pytest` as documented in the project README)

---

## Additional instructions

- Prefer **amend** or **squash** for tiny fixups on unpushed work; avoid noisy commit spam.
- Link every PR to an issue with **`Closes #N`** when the issue should close on merge.
- Keep issue threads technical; use comments for blockers and decisions.

---

**Last updated:** April 2026
