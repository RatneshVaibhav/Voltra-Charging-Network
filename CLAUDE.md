# CLAUDE.md — Voltra Charging Reliability (core context, loaded every session)

FDE course **Assignment 2** (Classes 4–8): take messy client data to a dependable pipeline that produces trustworthy
business metrics. Track C, own problem. **Deadline: 2026-09-27.** Owner: **Lakshya** (student FDE).
This file is the always-loaded core. Deeper context is layered — see **§9 Context map** — and must be read before reviews.

## 1. Your role and how work arrives
- Code and docs are written **phase by phase in a separate design session** (Claude.ai) and arrive as a full repo
  snapshot that Lakshya copies over this folder. Each phase is one commit + tag (`phase-N`). `CHANGELOG.md` lists what changed.
- **Your primary job: independent reviewer and verifier.** Run the code, reproduce the numbers, find defects, and judge the
  work against the course rubric. Report findings; **do not rewrite tracked files unless Lakshya explicitly asks.**
  Write review reports to `reviews/`. Use `/review-phase N` (full review), `/verify-numbers`, `/integrity-audit`,
  `/grader-view`; delegate deep reviews to the `fde-reviewer` subagent.
- If a fix is requested, keep it minimal, explain it, and tell Lakshya to bring the diff back to the design session
  (otherwise the next phase snapshot overwrites it).

## 2. Non-negotiable working rules
1. **Plan before modifying.** State files + intent first. Small, verifiable steps; run and show output.
2. **Locked decisions (§4) are not yours to change.** If code or data contradicts one, stop and report it.
3. **Never silently drop, fill, deduplicate or normalise data.** Every exclusion/fallback is a written rule, counted and logged.
4. **Never fabricate APIs/fields/endpoints.** `developer.nrel.gov` is dead — AFDC lives at `https://developer.nlr.gov`.
5. **Business definitions live in `config/kpi_definitions.json`**, never in env vars. Env = where/how it runs.
6. **The KPI uses real data only.** Simulated sources are labelled `data_origin="simulated"` and never feed the KPI.
7. Reproduce `docs/agent/reference_numbers.md` after any change to extract/clean/transform; explain any movement.
8. Scope: no ML, no Airflow/Spark/dbt, no UI polish. Never commit `.env`, API keys, or course PDFs (`course/`).
9. Say "we cannot determine…" when the data can't support a claim. Association ≠ causation.

## 3. The project in one screen
- **Persona:** *Voltra Charging Network* (fictional). **Data:** real public sessions + real DOE registry + 2 simulated client systems.
- **Headline:** *"Our fast chargers report 99% uptime — so why do 1 in 6 drivers fail on their first try?"*
- **Problem:** First-time charge success (FTCS) across **88 DC fast chargers at 43 sites** = **83.8%** (Jan 2024–Jan 2025),
  **86.0%** last quarter (Nov 2024–Jan 2025). 1 in 5 attempts delivered no usable energy; **0 of 46,575 sessions carry an
  error code**; **29.7%** of failed attempts died before a port was recorded. Failures are fleet-wide, not concentrated.
- **Target (6 weeks):** FTCS **86.0% → ≥87%** by lifting the 5 lagging sites to the network median, **and** close the
  diagnostic gap (every failed attempt gets a port + cause) so **≥90%** can be targeted next quarter.
- **Decision supported:** which sites need crews now, and what the operator must start recording before it can fix the rest.
- **Stakeholders:** VP Ops/NOC (owns "99% uptime"), Grants & Compliance (federal >97% rule), Customer Experience,
  field-service vendor, site hosts, CPMS vendor, drivers. No documented KPI owner.

## 4. Locked decisions (evidence: `docs/decisions_log.md`)
| ID | Decision |
|---|---|
| D1 | Headline/problem at **driver-visit grain**; recent-quarter baseline; amended target above |
| D2 | Failed attempt = **energy < 1.0 kWh**; blank-`port_id` attempts on DC chargers **kept as failures** ("unbound"); `>0 kWh` reported as sensitivity |
| D3 | Visit = consecutive attempts at the **same physical site**, gap `start − prev end` ∈ **[−2, +5] min**; visit succeeds if **any** attempt succeeds |
| D4 | Simulate only **S1 status feed (mock API)** + **S2 work orders (SQLite)**, anchored to real inferred outages; never feed the KPI |
| D5 | Fictional persona; site codes S01–S43 in outputs; Class-8-style layout |

Corrections made during research are logged (C1–C6) — keep them visible; they are evidence of FDE judgement.

## 5. KPI definitions (exact — mirrored in `config/kpi_definitions.json`)
1. **DC charger:** `charger_id` with ≥1 identified port whose max `peak_power_kw` > 20. Classify at charger level
   (failed attempts show peak 0).
2. **Attempt:** one session row on a DC charger, **including blank `port_id`** → `port_key = "UNBOUND@<charger_id>"`.
3. **Failed attempt:** `energy_kwh < 1.0`.
4. **Site:** charger → AFDC record via `port_id ∈ ev_network_ids.posts` → site = `UPPER(street_address)|UPPER(city)`;
   else fuzzy `evse_name`↔`station_name` (cutoff 0.85); else `UNRESOLVED|<charger_id>` (log). Result: 86 + 2 + 0 → 43 sites.
   `evse_name` text before "/" is the **owning organisation, not a site**. AFDC lists each charger as its own "station".
5. **Visit:** sort by (site, start); new visit unless gap ∈ [−2, +5] min.
6. **FTCS (KPI)** = visits whose first attempt succeeded ÷ visits. Also: troubled success, failed-visit rate, attempts/visit.
7. **Always report sensitivity:** FTCS at >0 kWh; 2-min and 10-min windows. Failed-visit rate is definition-sensitive (5.0–7.6%).

## 6. Sources (details: `docs/agent/project_context.md` §6)
| ID | Source | Mode | Real? | Completeness proof |
|---|---|---|---|---|
| R1 | Session exports — HF `shadenn/EV_Charging_demand/raw_charging_stations/Se_MM_YYYY.csv` (13 files, CC-BY-4.0) | files over HTTP | real | size + git-blob SHA-1 vs HF tree API |
| R2 | AFDC station registry `developer.nlr.gov/api/alt-fuel-stations/v1.json` (key: `AFDC_API_KEY`) | REST API | real | `len(fuel_stations) == total_results` |
| S1 | Charger status feed (OCPP-style `StatusNotification`), `simulate/mock_status_api.py` @ :8001 | REST API | simulated | paginated `total_records`; deterministic 500 + 429 |
| S2 | Maintenance work orders `data/simulated_client_systems/sim_cmms.db` | SQL | simulated | row counts vs generator manifest |
| — | `data/simulated_client_systems/client_brief.json` — "99% uptime" claim + conflicting definitions | file | simulated | — |

## 7. Top traps (full list of 13: `docs/agent/project_context.md` §7)
- **Blank `port_id`: 2,187 rows (4.7%)** — all on DC chargers, 99.9% zero-energy. Dropping them inflates FTCS ~4 pts.
- **39 glued headers** (`…*2provider_id,station_id,…` mid-line) across 13 files — repair, count, log.
- **`session_error` is blank on all rows** — blank ≠ success.
- Registry is a **2026 snapshot**; sessions end Jan 2025 → temporal misalignment (limitation, not evidence).
- 42 of 88 DC chargers were commissioned mid-window → trend has a mix effect.
- Zero energy is an **inferred** failure; cause (charger/vehicle/driver/payment) is unknown. Failure rate is a lower bound.

## 8. Engineering conventions (full: `.claude/rules/pipeline-code.md`)
- Python ≥3.11; `pandas`, `requests`, `flask`, `pytest`. One command: `python run_pipeline.py --run-date YYYY-MM-DD`.
- Stages: extract → validate (PASS/WARN/FAIL/UNKNOWN gate) → clean → transform → metrics → save → log.
- Exit codes: `0` success · `2` validation gate stopped (nothing published) · `1` unexpected failure.
- Raw → `data/raw/<source>/run_date=<d>/` (replaced per run). Outputs → `data/processed/run_date=<d>/`, whole partition
  written to temp then swapped atomically. Retries only on 429/5xx/timeouts, bounded, honour Retry-After.
- Every join reports match coverage %. Aggregate one-to-many before joining. UTC everywhere.

## 9. Context map (read the relevant files before reviewing or implementing)
| File | What it gives you | When |
|---|---|---|
| `docs/agent/project_context.md` | Full assignment brief, rubric, course methodology (Classes 4–8), sources, 13 defects, conventions, glossary | Before any review |
| `docs/agent/review_checklist.md` | Rubric → checklists, **per-phase Definition of Done**, red flags, severity scale, report template | Every review |
| `docs/agent/reference_numbers.md` | 22 regression numbers + how to reproduce | After code changes |
| `docs/agent/domain_primer.md` | EV charging domain (OCPP lifecycle, failure modes, uptime rules) to judge correctness | When judging logic |
| `docs/decisions_log.md` | D1–D5 evidence, rejected options, corrections C1–C6 | Before questioning a decision |
| `docs/research_sources.md` | Cited research | When checking claims |
| `config/kpi_definitions.json` | Versioned business rules | When checking KPI code |
| `.claude/rules/*.md` | Auto-loaded rules for pipeline, simulation, docs | Automatic |
| `CHANGELOG.md` / `WORKFLOW.md` | What changed per phase / how phases are applied | Start of each review |

## 10. Phase status
- [x] Phase 1 — decisions, context layer, skeleton
- [ ] Phase 2 — source reasoning (source map, required fields, system-of-record decisions, gaps)
- [ ] Phase 3 — retrieval (R1 files + checksums, R2 API, S1 mock API, S2 SQLite, raw preservation)
- [ ] Phase 4 — profiling & validation (contract + executable gate)
- [ ] Phase 5 — model & metrics (site → charger → port → attempt → visit; 3–5 metrics; diagram)
- [ ] Phase 6 — pipeline hardening (one command, idempotency, chaos demos, tests, Gate 2)
- [ ] Phase 7 — evidence table, Known/Unknown/Assumption/Limitation, README, demo script
