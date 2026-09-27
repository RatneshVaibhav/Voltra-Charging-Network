# CHANGELOG

## Independent review resolved — definitions v1.3.1 (2026-09-27)
Every finding of `reviews/full-review-2026-09-27.md` is resolved; the map is `reviews/review-fixes-2026-09-27.md`.
KPI and every regression count are unchanged (FTCS 86.03% / 83.87%).
**Added**
- Validation (D8): `sessions.header_consistency` (FAIL), `sessions.numeric_parse` (missing energy FAIL, blank peak
  power WARN), content-based integrity checks, per-gate logging of counts and every WARN
- Metrics (D9): `driver_behaviour` retry measures (27.2% of retry visits move charger), `judgement_call` block,
  *drop port-less attempts (rejected, D2)* sensitivity row, baseline-quarter column, `open_outages_at_data_end.csv`
- Dependability (D10): chaos runs isolated under `data/*/chaos/<name>/`; swap rollback; API-key redaction; robust
  `Retry-After`; published folders 0755; `stale_data` = latest export withheld
- Tests: 9 → 30 (`tests/test_extract.py`, `tests/test_metrics.py`, more in the existing files)
- `reviews/full-review-2026-09-27.md`, `reviews/review-fixes-2026-09-27.md`
**Changed**
- `config/kpi_definitions.json` 1.1.0 → 1.3.1 (gate tolerances, baseline length, repair window, retry rules,
  open-outage rule, new sensitivity row); `requirements.txt` pins `pandas>=2.0,<4`
- `docs/decisions_log.md`: decision index; D8–D10; superseded figures marked in D1–D5; options tables for D2's
  judgement call, D6 and D7; corrections C11–C18
- README rewritten to be self-explanatory; `docs/demo_script.md` is a word-for-word 4½-minute script with Q&A;
  `docs/evidence.md`, `data_model.md`, `source_map.md`, `validation_contract.md`, `gate2_data_readiness.md` refreshed
- Port-less wording corrected: the charger is known; what is missing is the port binding and failure stage (C18)
**Removed:** empty `notebooks/` and `docs/diagrams/` placeholders (see D5)
**How to run:** `python run_pipeline.py --offline` · `pytest -q` (30 passed)

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
