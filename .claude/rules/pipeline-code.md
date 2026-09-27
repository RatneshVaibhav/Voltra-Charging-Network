---
paths:
  - "pipeline/**/*.py"
  - "run_pipeline.py"
  - "tests/**/*.py"
---
# Pipeline code rules (Class 8 conventions + lessons from the course reference repo)

**Structure.** `run_pipeline.py` orchestrates; `pipeline/` modules: `config`, `logging_utils`, `extract`, `validate`,
`clean`, `transform`, `metrics`, `save`. One responsibility per function; functions take inputs and return outputs.

**Config.** Env vars (see `config/.env.example`) control *where/how* it runs: URLs, `AFDC_API_KEY`, retries, timeouts,
page size, log level, mock-API autostart, seed. Business rules come only from `config/kpi_definitions.json`; echo its
`version` into every output. Never read thresholds/windows from env.

**Retrieval.** `requests` with explicit `timeout`. Retry only 429, 500, 502, 503, 504 and timeouts/connection errors;
bounded by `MAX_RETRIES`; exponential backoff; honour `Retry-After` header or `retry_after_seconds` body. Fail fast on other
4xx and on schema problems. Save every raw payload **before** parsing. Prove completeness and **raise** if incomplete.
AFDC base URL is `https://developer.nlr.gov/...` (never `developer.nrel.gov`).

**Validation gate.** Each check returns `{check, status: PASS|WARN|FAIL|UNKNOWN, detail, evidence_count}`. Any FAIL raises
`ValidationError` → exit code 2 and **no new processed output**. Missing required column = FAIL (never skip silently —
the course reference repo's `[c for c in cols if c in df.columns]` pattern is banned).

**Idempotency & publishing.** Raw → `data/raw/<source>/run_date=<d>/` (clear before writing). Processed → write the whole
partition to a temp dir in the same parent, then atomic rename/replace. Rerun with the same run date must yield identical
outputs (except run timestamps in logs/manifests).

**Joins.** Always report coverage (matched/total). Use `validate="many_to_one"` etc. in `pd.merge`. Aggregate one-to-many
tables before joining to visit/charger grain.

**Logging.** Format `%(asctime)s | %(levelname)s | %(message)s`; messages start with the stage, e.g.
`EXTRACT | source=R2 page=1 rows=4593 total=4593`. Log counts for every drop/repair/fallback, and whether output was published.

**Errors.** No bare/broad `except` that continues. Exit codes: 0 success, 2 validation stop, 1 unexpected.

**Tests (pytest).** Cover: glued-header repair, unbound attempts kept, DC classification per charger, site resolution chain,
visit grouping boundaries (gap exactly −2, 5, 5.01 min), idempotent rerun, validation FAIL path.
