# CHANGELOG

Each entry lists what a phase snapshot changed, how to run it, and anything to delete manually.

---

## Phase 1.1 — Claude Code context layer (2026-09-27)
**Why:** Claude Code's documentation recommends keeping `CLAUDE.md` under ~200 lines (longer files reduce adherence) and
using rules, skills and subagents for the rest. The single 381-line `CLAUDE.md` from Phase 1 was split into layers.

**Added**
- `.claude/rules/data-integrity.md` (always loaded) · `pipeline-code.md` · `simulation.md` · `docs-and-evidence.md`
  (path-scoped — load only when matching files are touched)
- `.claude/agents/fde-reviewer.md` — read-and-run reviewer subagent (grader + senior-engineer perspective)
- `.claude/skills/review-phase` · `verify-numbers` · `integrity-audit` · `grader-view` — review commands
- `.claude/settings.json` — pre-approves read-only git/test commands; denies `git push` and reading `.env`
- `docs/agent/project_context.md` (full detail moved from old CLAUDE.md) · `review_checklist.md` (rubric checklists,
  per-phase Definition of Done, red flags, severity, report template) · `reference_numbers.md` (regression targets +
  reproduction recipe) · `domain_primer.md` (EV-charging domain knowledge)
- `WORKFLOW.md` (how to apply phases, review, commit) · `CHANGELOG.md` · `reviews/README.md`

**Changed**
- `CLAUDE.md` rewritten as a 108-line core with a context map.
- `.gitignore` adds `.scratch/`, `CLAUDE.local.md`, `.claude/settings.local.json`.

**Removed:** `reviews/.gitkeep` (replaced by `reviews/README.md`) — `git rm reviews/.gitkeep` if it exists locally.

**How to run:** nothing to run yet. Suggested checks: `/verify-numbers` (independent check of Phase 1 research numbers)
and `/review-phase 1`.

---

## Phase 1 — Decisions & skeleton (2026-09-27)
**Added:** `CLAUDE.md`, `README.md` (stub), `docs/decisions_log.md` (D1–D5 + corrections C1–C6),
`docs/research_sources.md`, `config/kpi_definitions.json`, `config/.env.example`,
`data/simulated_client_systems/client_brief.json`, `requirements.txt`, `.gitignore`, folder skeleton.
**How to run:** nothing to run.
