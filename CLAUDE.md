# CLAUDE.md — Voltra Charging Reliability (core context, loaded every session)

FDE course **Assignment 2** (Classes 4–8): messy client data → dependable pipeline → trustworthy business metrics.
Track C (own problem). Owner: **Lakshya**. **All 7 phases are built**; your job is to review, verify and explain.

## 1. Your role
- **Independent reviewer and verifier.** Run the pipeline and tests, reproduce numbers, find defects, judge the work
  against the rubric. Report findings; do not rewrite tracked files unless Lakshya explicitly asks.
- Commands: `/review-phase N`, `/verify-numbers`, `/integrity-audit`, `/grader-view` (in `.claude/skills/`), and the
  `fde-reviewer` subagent. Write reports to `reviews/`.
- **Token discipline (see `.claude/rules/agent-efficiency.md`):** never Read raw data files (CSVs, JSON dumps, DBs,
  `data/processed/*`) into context — run scripts and read their printed summaries. Prefer running
  `python run_pipeline.py --offline` and reading `metrics.json` / `validation_report.json` over re-deriving numbers.

## 2. Non-negotiable rules
1. Plan before modifying; small verifiable steps; show command output.
2. Locked decisions (§4) are not yours to change — report conflicts instead.
3. Never silently drop, fill, deduplicate or normalise data; every rule is written, counted, logged.
4. Never fabricate endpoints: AFDC is at `https://developer.nlr.gov` (`developer.nrel.gov` is dead).
5. Business definitions and gate tolerances live only in `config/kpi_definitions.json` (v1.3.1); env vars = infrastructure only.
6. The KPI uses real data only; simulated sources carry `data_origin="simulated"` and are labelled "illustrative".
7. After any change to extract/clean/transform, reproduce `docs/agent/reference_numbers.md`; explain any movement.
8. No ML, orchestration frameworks or UI polish. Never commit `.env`, keys, or course PDFs (`course/`).
9. Evidence language: "the data shows / is associated with / we cannot determine". No causal claims.

## 3. The project in one screen
- **Persona:** *Voltra Charging Network* (fictional). **Data:** real public sessions (R1) + real DOE registry (R2) +
  two simulated client systems (S1 status feed, S2 work orders).
- **Headline:** *"Our fast chargers report 99% uptime — so why do 1 in 7 drivers fail on their first try?"*
- **Results (run_date 2025-02-01):** FTCS **86.03%** baseline quarter (Nov 2024–Jan 2025), **83.87%** over 13 months;
  88 DC chargers at **40 sites**; 29,036 visits; 0 of 46,575 sessions carry an error code; **29.6%** of failed attempts
  have no port; operator uptime 99.77% (illustrative) vs inferred availability 97.05% vs FTCS 86.03%.
- **Judgement call (demo):** the 2,187 port-less attempts are kept; dropping them would read 90.33% (+4.30 pts) —
  recomputed every run in `metrics.json → judgement_call`.
- **Target:** FTCS 86.03% → ≥ 87% in 6 weeks by lifting 5 lagging sites (S40, S17, S01, S08, S28) to the median
  (projection 87.01%); record port + error code on every attempt so ≥ 90% can be targeted next quarter.
- **Decision supported:** which sites need crews now (plus S29 to verify: 2 chargers silent since 5–6 Jan 2025), and what
  the operator must start recording before it can fix the rest.

## 4. Locked decisions (evidence: `docs/decisions_log.md`)
| ID | Decision |
|---|---|
| D1 | Headline/problem at driver-visit grain; baseline = last 3 monthly exports; headline "1 in 7" (amended) |
| D2 | Failed attempt = energy < 1.0 kWh; blank-`port_id` attempts on DC chargers kept as failures ("unbound") |
| D3 | Visit = attempts at the same physical site, gap to previous row's end ∈ [−2, +5] min; success if any attempt succeeds |
| D4 | Simulate only S1 (status feed API) + S2 (work orders SQLite), anchored to real inferred outages; never feed the KPI |
| D5 | Fictional persona; site codes S01–S40; Class-8-style layout |
| D6 | Freshness judged against the logical run date (reporting month); wall-clock age = WARN |
| D7 | Physical site = registry coordinates clustered within 150 m (fixes address spelling variants: 43 → 40) |
| D8 | Changed file layout and missing energy FAIL; integrity checked by content; gate tolerances in config |
| D9 | Retry switching measured by charger (27.2%); judgement call and open outages computed every run |
| D10 | Chaos demos isolated under `chaos/<name>/`; stale data = the latest export withheld |
Corrections C1–C18 are logged on purpose — they are evidence of judgement.

## 5. How to run
```bash
python -m simulate.build_client_systems      # (re)build S1/S2 deterministically (already committed)
python run_pipeline.py --offline             # full flow from the committed snapshot  (~10 s)
python run_pipeline.py                       # live: HF files + AFDC API (needs internet; AFDC_API_KEY or DEMO_KEY)
python run_pipeline.py --offline --chaos missing_column|duplicate_rows|stale_data|api_outage|bad_checksum
pytest -q                                    # 30 tests
```
Exit codes: `0` success · `2` validation gate stopped (nothing published) · `1` retrieval/unexpected failure.
Outputs: `data/processed/run_date=<d>/` (metrics.json, evidence_table.md, validation_report.json, site_scorecard.csv,
sensitivity.csv, sites/chargers/visits/attempts.csv …). Logs: `logs/pipeline_<d>.log`. Chaos runs write only under
`data/*/chaos/<name>/` and `logs/*_chaos-<name>.*`.

## 6. Code map
`run_pipeline.py` orchestrates → `pipeline/extract.py` (R1 files + checksums, R2 API, S1 paginated API with retries,
S2 SQL) → `pipeline/clean.py` (glued-header repair, types, exact duplicates) → `pipeline/validate.py` (3 gates,
PASS/WARN/FAIL/UNKNOWN) → `pipeline/transform.py` (DC per charger, site resolution + 150 m clustering, attempts,
visits) → `pipeline/inference.py` (inferred outages, silent chargers) → `pipeline/metrics.py` (KPI, evidence table,
sensitivity, scorecard, illustrative metrics) → `pipeline/save.py` (atomic partition swap).
Simulation: `simulate/build_client_systems.py`, `simulate/mock_status_api.py`, `simulate/SIMULATION_SPEC.md`.

## 7. Context map
| File | Purpose |
|---|---|
| `README.md` | Submission overview (problem, stakeholders, KPI, sources, run, decision, results) |
| `docs/source_map.md` · `docs/validation_contract.md` · `docs/data_model.md` | Phases 2 · 4 · 5 deliverables |
| `docs/gate2_data_readiness.md` · `docs/evidence.md` · `docs/demo_script.md` | Phases 6 · 7 deliverables |
| `docs/decisions_log.md` | D1–D10 with evidence, rejected options, corrections C1–C18 |
| `reviews/` | Independent reviews and `review-fixes-2026-09-27.md` (every finding → fix commit → verification) |
| `docs/agent/review_checklist.md` | Rubric checklists, per-phase Definition of Done, red flags, report template |
| `docs/agent/reference_numbers.md` | Regression targets (generated from pipeline output) |
| `docs/agent/project_context.md` · `docs/agent/domain_primer.md` | Deep context · EV-charging domain knowledge |
| `docs/research_sources.md` | Cited research |

## 8. Phase status
- [x] 1 Decisions & context · [x] 2 Source map · [x] 3 Retrieval · [x] 4 Validation · [x] 5 Model & metrics
- [x] 6 Pipeline hardening (one command, idempotent, chaos demos, tests, Gate 2) · [x] 7 Evidence, K/U/A/L, README, demo
- [x] Independent review (19 findings) resolved — D8–D10, 30 tests, definitions v1.3.1
