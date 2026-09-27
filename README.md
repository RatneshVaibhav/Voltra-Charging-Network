# Voltra Charging Network — Charging Reliability Data Pipeline

> **"Our fast chargers report 99% uptime — so why do 1 in 7 drivers fail on their first try?"**

FDE Data Foundations Assignment (Classes 4–8), Track C. A dependable monthly pipeline that turns fragmented
charging-network data into a trustworthy measure of the reliability drivers actually experience.

## 1. The problem
The operator's dashboard reports ~99% uptime; customers say chargers don't work. Using 46,575 real charging sessions
(Jan 2024 – Jan 2025) from 88 DC fast chargers at 40 sites:

- **First-time charge success (FTCS) is 86.03%** in the baseline quarter (Nov 2024 – Jan 2025) — 1 in 7 drivers fail
  on their first try — and 83.87% over 13 months.
- **1 in 5 charge attempts delivers no usable energy**, yet **none of 46,575 sessions carries an error code**.
- **29.6% of failed attempts have no port recorded** — they died before the port was known, so no crew can be sent to them.
- Uptime cannot see these failures: the same fleet reads 99.77% (operator definition, illustrative), 98.18%
  (federal-style), 97.05% (availability inferred from real sessions) — and 86.03% for drivers.

**Decision the output supports:** *which sites need crews now, and what must the operator start recording before it
can fix the rest?* Answer (run 2025-02-01): send crews to **S40, S17, S01, S08, S28** (lifting them to the median
takes FTCS 86.03% → **87.01%**, the 6-week target), and require the charging software to record the **port and an
error code on every attempt** so a ≥ 90% target and root-cause work become possible next quarter.

## 2. Users and stakeholders
| Stakeholder | Uses the output for | Owns |
|---|---|---|
| VP Operations / NOC | Where to send crews; whether "uptime" can stay the headline | The 99% uptime claim, status feed |
| Field-service vendor | Prioritised site list | Work orders |
| Customer Experience | Driver-level KPI | Complaints, driver outcomes |
| Grants & Compliance | Federal-style uptime vs driver reality | Reporting to funders |
| CPMS (charging-software) vendor | Instrumentation asks (port, error code) | Session data |
| Site hosts | Site scorecard | Sites |

No KPI owner is documented — flagged as **UNKNOWN** by the validation gate; the definition needs sign-off.

## 3. Project KPI
**First-Time Charge Success rate (FTCS)** = driver visits whose first attempt delivered ≥ 1 kWh ÷ all visits.
A visit = consecutive attempts at the same physical site starting within 5 minutes of the previous one ending.
Baseline 86.03% → target ≥ 87% in 6 weeks; stretch ≥ 90% next quarter. Every rule is versioned in
`config/kpi_definitions.json` and justified in `docs/decisions_log.md` (peer-reviewed 1 kWh screen and 5-minute
window from UC Davis, validated on this data; sensitivity range 82.4–84.8%).

## 4. Sources
| ID | Source | Real? | Retrieval mode | Completeness proof |
|---|---|---|---|---|
| R1 | Charging-session exports — Hugging Face [`shadenn/EV_Charging_demand`](https://huggingface.co/datasets/shadenn/EV_Charging_demand) (CC-BY-4.0), 13 monthly CSVs | Real | Files over HTTP | size + git-blob SHA-1 vs the HF tree API (13/13) |
| R2 | US DOE AFDC station registry API (`developer.nlr.gov`) | Real | REST API | `len(fuel_stations) == total_results` (4,593) |
| S1 | Charger status feed (OCPP-style) | **Simulated**, anchored to real sessions + inferred outages | Paginated REST API (mock, injected 500/429) | received == `total_records` per month (124,968) |
| S2 | Maintenance work orders | **Simulated**, anchored to real inferred outages | SQL (SQLite) | rows == manifest (426) |

Full source map, system-of-record decisions and gaps: [`docs/source_map.md`](docs/source_map.md).
Simulation rules (each marked *real anchor* or *assumption*): [`simulate/SIMULATION_SPEC.md`](simulate/SIMULATION_SPEC.md).

## 5. Setup and run
```bash
git clone https://github.com/RatneshVaibhav/Voltra-Charging-Network.git && cd Voltra-Charging-Network
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/.env.example .env            # optional: set AFDC_API_KEY (DEMO_KEY works, 10 requests/hour)

python run_pipeline.py --offline       # full flow from the committed source snapshot (~15 s)
python run_pipeline.py                 # same flow from the live sources (internet required)
pytest -q                              # 9 tests
```
One command runs **extract → validate → clean → validate → transform → validate → metrics → save**. Exit codes:
`0` success · `2` a validation gate stopped the run (nothing published) · `1` retrieval/unexpected failure.
Outputs land in `data/processed/run_date=<d>/` (replaced atomically on rerun); logs in `logs/pipeline_<d>.log`.

Failure demos: `python run_pipeline.py --offline --chaos missing_column | duplicate_rows | stale_data | api_outage | bad_checksum`
(→ exit 2 · WARN + dedupe · exit 2 · exit 1 after bounded retries · exit 2).

The simulated systems are committed; to rebuild them deterministically: `python -m simulate.build_client_systems`.

## 6. Results
Evidence table (5 metrics), sensitivity, crew list and the **Known / Unknown / Assumption / Limitation** section:
[`docs/evidence.md`](docs/evidence.md).

| Metric | Baseline quarter | 13 months | Basis |
|---|---|---|---|
| FTCS (KPI) | **86.03%** | 83.87% | Real |
| Failed-visit rate | 4.7% | 5.8% | Real (definition-sensitive: 4.9–11.3%) |
| Troubled success (retries) | 9.3% | 10.4% | Real |
| Port-less share of failed attempts | 29.6% | — | Real |
| Operator uptime · federal-style · inferred availability | 99.77% · 98.18% · 97.05% | — | Illustrative (simulated) / inferred |

## 7. Where each rubric pillar is evidenced
| Pillar | Evidence |
|---|---|
| Source reasoning (Class 4) | `docs/source_map.md` — questions → fields → sources → owners, grain, SoR decisions, 7 gaps |
| Retrieval (Class 5) | `pipeline/extract.py` — 3 modes (files, REST, SQL), retries, raw preservation, completeness proofs |
| Validation (Class 6) | `docs/validation_contract.md` + `pipeline/validate.py` — 30 checks, PASS/WARN/FAIL/UNKNOWN gates |
| Workflow + metrics (Class 7) | `docs/data_model.md` + `pipeline/transform.py`, `metrics.py` — site → charger → attempt → visit; 5 metrics |
| Pipeline dependability (Class 8) | `run_pipeline.py`, `pipeline/save.py`, `tests/`, `docs/gate2_data_readiness.md` — one command, idempotent, chaos demos |

Decisions, rejected options and self-corrections (C1–C10): [`docs/decisions_log.md`](docs/decisions_log.md).
Demo script: [`docs/demo_script.md`](docs/demo_script.md).

## 8. Repository layout
```
run_pipeline.py            one-command pipeline
pipeline/                  config · logging · extract · clean · validate · transform · inference · metrics · save
simulate/                  S1/S2 generator, mock status API, SIMULATION_SPEC.md
config/                    kpi_definitions.json (business rules, versioned) · .env.example (infrastructure)
data/source_snapshot/      committed real inputs (R1 CSVs + HF checksums, trimmed R2 registry) for offline runs
data/simulated_client_systems/  S1 events, S2 SQLite, client_brief.json (all labelled simulated)
docs/                      source map · validation contract · data model · Gate 2 · evidence · demo · decisions · research
tests/                     pytest suite
CLAUDE.md, .claude/, docs/agent/   context and review tooling for coding agents
```

## 9. Data provenance and honesty notes
- R1 is a public third-party excerpt (CC-BY-4.0) of ChargePoint session data from Tennessee and neighbouring states;
  site names suggest a regional public-power fast-charging programme, but the dataset does not say so, so results
  are **not** attributed to any named operator. **Voltra Charging Network is a fictional persona.**
- S1/S2 are simulated stand-ins for systems every operator has but none publishes; they never feed the KPI.
- The data ends January 2025 (a historical backfill); every monthly export is missing its last day (13 of 397 days).
