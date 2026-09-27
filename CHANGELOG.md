# CHANGELOG

## Final build — Phases 2–7 + review corrections (2026-09-27)
**Added**
- Pipeline: `run_pipeline.py`; `pipeline/{config,logging_utils,extract,clean,validate,transform,inference,metrics,save}.py`
- Simulation: `simulate/build_client_systems.py`, `simulate/mock_status_api.py`, `simulate/SIMULATION_SPEC.md`;
  generated `data/simulated_client_systems/{status_events.json.gz, sim_cmms.db, simulation_manifest.json}`
- Real source snapshot: `data/source_snapshot/` (13 session CSVs + HF checksums, trimmed AFDC registry)
- Docs: `source_map.md` (Phase 2), `validation_contract.md` (4), `data_model.md` (5), `gate2_data_readiness.md` (6),
  `evidence.md` + `demo_script.md` (7)
- Tests: `tests/` (9 tests) + `pytest.ini`; `scripts/refresh_source_snapshot.py`; `AGENTS.md`;
  `.claude/rules/agent-efficiency.md`
**Changed**
- `config/kpi_definitions.json` → v1.1.0 (operators, tie-break, gap semantics, sensitivity list, 150 m site clustering,
  lagging-site rule, freshness, completeness, outage inference)
- `docs/decisions_log.md`: D1 amended (headline "1 in 7"), D3 amended (2-min label, gap spec), new D6 (run date &
  freshness), D7 (distance-based sites); corrections C7–C10
- `CLAUDE.md`, `README.md`, `WORKFLOW.md`, `docs/agent/*`, `.claude/skills/review-phase`, `verify-numbers`,
  `.claude/agents/fde-reviewer.md` updated to the final state and token-efficient reviews
**How to run:** `python run_pipeline.py --offline` · `pytest -q`

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
