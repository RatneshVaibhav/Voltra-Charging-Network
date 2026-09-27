# Gate 2 — Data Readiness Review (Class 8)

Evidence comes from `logs/pipeline_2025-02-01.log`, `data/processed/run_date=2025-02-01/` and the chaos runs below.

## Pipeline run
- [x] Complete flow runs with one command — `python run_pipeline.py` (live) or `python run_pipeline.py --offline`
- [x] Same run can be safely repeated — rerun produced byte-identical `metrics.json`, `visits.csv`, `attempts.csv`
- [x] Raw inputs are preserved — `data/raw/run_date=<d>/{sessions,afdc,status_feed,work_orders}/`, replaced per run
- [x] Processed output is written only after all three validation gates pass (atomic partition swap)

## Validation
| Check | Status | Evidence |
|---|---|---|
| Required columns | PASS | `sessions.required_columns`; demo `--chaos missing_column` → exit 2, nothing published |
| Critical nulls / semantics | WARN | `session_error` never populated; 2,187 blank `port_id` kept as unbound attempts |
| Uniqueness | PASS | no conflicting `session_id`; demo `--chaos duplicate_rows` → 50 exact copies collapsed, logged |
| Freshness | PASS | lag 1.01 days vs reporting month (limit 2); demo `--chaos stale_data` → exit 2 |
| Retrieval completeness | PASS | R1 13/13 checksums · R2 4,593/4,593 · S1 124,968/124,968 · S2 426/426; demo `--chaos bad_checksum` → exit 2 |
| Cross-source mapping | PASS / WARN | 88/88 chargers resolved (86 port id, 2 name); 43 address strings → 40 sites |

## Reliability
| Capability | Status | Evidence |
|---|---|---|
| Bounded retries | PASS | S1 page 3 → HTTP 500 → retried; page 5 → HTTP 429 → waited `retry_after_seconds`; demo `--chaos api_outage` → 3 attempts then exit 1 |
| Useful failure messages | PASS | e.g. `GATE | pipeline stopped | retrieval/schema gate: sessions.required_columns -> missing=['energy_kwh'] | no processed output published` |
| Logging | PASS | stage-prefixed console + file log with counts for every repair/fallback |
| Idempotent rerun | PASS | same partition replaced atomically; no temp/backup directories left behind (tested) |
| Configuration outside core logic | PASS | env → `pipeline/config.py`; business rules → `config/kpi_definitions.json` v1.1.0 (echoed into `metrics.json`) |
| Tests | PASS | `pytest` — 9 tests (glued headers, duplicates, charger-level DC, unbound kept, site clustering, name fallback, visit boundaries, freshness, atomic publish) |

## Known limitations
- `session_error` is never populated → failure causes are unknown; failures are inferred from energy.
- Every monthly export is missing its last day (13 of 397 days).
- No driver identity → visits are reconstructed (5-minute site window).
- No real status/outage history → outages are inferred; S1/S2 are simulated and illustrative only.
- The KPI definition has no documented owner (UNKNOWN).

## Gate decision
**READY** for the next (product) phase, for decisions at **site** level — with the limitations above stated wherever
the numbers are shown. **NOT READY** for attributing failures to root causes or for AI-based prediction: the system
does not record a failure label or cause, and a model cannot learn a label the system cannot define.
