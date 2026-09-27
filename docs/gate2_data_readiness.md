# Gate 2 — Data Readiness Review (Class 8)

Evidence comes from `logs/pipeline_2025-02-01.log`, `data/processed/run_date=2025-02-01/` and the chaos runs below
(each writes its own `logs/pipeline_2025-02-01_chaos-<name>.log`, never the real run's files).

## Pipeline run
- [x] Complete flow runs with one command — `python run_pipeline.py` (live) or `python run_pipeline.py --offline`
- [x] Same run can be safely repeated — reruns produced byte-identical `metrics.json`, `visits.csv`, `attempts.csv`
- [x] Raw inputs are preserved — `data/raw/run_date=<d>/{sessions,afdc,status_feed,work_orders}/`, written before any
      parsing and replaced per run
- [x] Processed output is written only after all three validation gates pass (atomic partition swap; the previous
      partition is restored if the swap itself fails)
- [x] A failure demo can never change the published result — chaos runs write under `data/*/chaos/<name>/`; after all
      five demos the real partition and raw inputs are byte-identical

## Validation (33 checks: PASS 17 · WARN 15 · UNKNOWN 1)
| Check | Status | Evidence |
|---|---|---|
| Required columns | PASS | `sessions.required_columns`; demo `--chaos missing_column` → exit 2, nothing published |
| File layout | PASS | `sessions.header_consistency` — all 52 header rows identical; a reordered header FAILs (tested) |
| Critical nulls / semantics | WARN | `session_error` never populated; 2,187 blank `port_id` kept as unbound attempts; 2,549 blank `peak_power_kw` left missing; a missing `energy_kwh` would FAIL |
| Uniqueness | PASS | no conflicting `session_id` (a conflict FAILs, tested); demo `--chaos duplicate_rows` → 50 exact copies collapsed, logged |
| Freshness | PASS | lag 1.01 days vs reporting month (limit 2); demo `--chaos stale_data` (January export withheld) → lag 32 days, exit 2 |
| Retrieval completeness | PASS | R1 13/13 checksums · R2 4,593/4,593 · S1 124,968/124,968 · S2 426/426; demo `--chaos bad_checksum` → exit 2 |
| Cross-source mapping | PASS / WARN | 88/88 chargers resolved (86 port id, 2 name); 43 address strings → 40 sites; an unresolved charger FAILs (tested) |
| Integrity | PASS | every attempt is an R1 session in exactly one visit; KPI inputs hold only R1 + derived columns (tested with a leak) |

## Reliability
| Capability | Status | Evidence |
|---|---|---|
| Bounded retries | PASS | S1 page 3 → HTTP 500 → retried; page 5 → HTTP 429 → waited `retry_after_seconds`; demo `--chaos api_outage` → 3 attempts, "giving up", exit 1. Unit tests: 5xx backoff, 429 retry-after (seconds and HTTP date), wait cap, 4xx not retried, bounded |
| Useful failure messages | PASS | e.g. `GATE \| pipeline stopped \| retrieval/schema gate: sessions.required_columns -> missing=['energy_kwh'] \| no processed output published` |
| Logging | PASS | stage-prefixed console + file log; every gate logs `VALIDATE \| <gate> PASSED \| PASS=… WARN=…` and one line per WARN; counts for every repair |
| Secrets | PASS | API keys redacted from every log line and error message (tested); `.env` git-ignored |
| Idempotent rerun | PASS | same partition replaced atomically; no temp/backup directories left behind; rollback tested |
| Configuration outside core logic | PASS | env → `pipeline/config.py`; business rules and gate tolerances → `config/kpi_definitions.json` v1.3.1 (echoed into `metrics.json`) |
| Tests | PASS | `pytest` — 30 tests: cleaning, header drift, numeric parse, DC per charger, unbound kept, site clustering and name fallback, unresolved site, visit window, retry switching, judgement call, open outages, lagging rule (unrounded), baseline, freshness, duplicates, retries, redaction, atomic publish and rollback |

## Known limitations
- `session_error` is never populated → failure causes are unknown; failures are inferred from energy.
- Every monthly export is missing its last day (13 of 397 days).
- No driver identity → visits are reconstructed (5-minute site window).
- No real status/outage history → outages are inferred; S1/S2 are simulated and illustrative only.
- Two chargers at S29 have an inferred outage still open at the end of the data (outage or removal — verify on site).
- The KPI definition has no documented owner (UNKNOWN).

## Gate decision
**READY** for the next (product) phase, for decisions at **site** level — with the limitations above stated wherever
the numbers are shown. **NOT READY** for attributing failures to root causes or for AI-based prediction: the system
does not record a failure label or cause, and a model cannot learn a label the system cannot define.
