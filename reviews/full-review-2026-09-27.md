# Full review (R0–R8) — 2026-09-27

**Verdict:** READY WITH FIXES

**Commands run:**
- `python -m pytest -q` → exit 0 (9 passed, 0.16 s)
- `python run_pipeline.py --offline` → exit 0, three times (9.4 s; outputs byte-identical each time)
- `--chaos missing_column` → exit 2 · `duplicate_rows` → exit 0 · `stale_data` → exit 2 · `api_outage` → exit 1 · `bad_checksum` → exit 2
- Scratch probes (outside the repo): numeric parse, header drift, swap rollback, key leak, and the claims behind "~4 pts", port switching, open outages and the repair effect

Environment: Python 3.12.3, **pandas 3.0.6** (`python -m pytest`). Reviewed tree: the final build before it was committed (Phases 2–7 in this history). All probes ran in a scratch directory outside the repo.

---

## R0 — Orientation

- **Problem:** the operator claims 99% uptime, but drivers fail on the first try about 1 in 7 times.
- **KPI:** FTCS, measured at visit grain (site, 5-min window, ≥ 1 kWh). Baseline is the last 3 months of data.
- **Sources:** R1 is 13 real HF CSVs (files). R2 is the real AFDC registry (REST). S1 is a simulated paginated status API. S2 is a simulated SQLite work-order table.
- **Decisions:** D1–D7. The key one is D2, which keeps 2,187 port-less DC attempts as failures.

Contradictions between these files:
- `config/kpi_definitions.json:4` says `approved_in: D1-D6`. The config also carries D7 (the 150 m clustering rule), so this should read D1–D7.
- `decisions_log.md` D3 still says "Site = normalised registry address (`street_address|city`)". D7 replaced that, and D3 has no note saying so.
- `decisions_log.md` D4 and D5 still quote pre-D7 numbers (see F11).
- Config `change_policy` requires "a dated entry in decisions_log.md and a version bump". v1.1.0 appears only in CHANGELOG, not in decisions_log.

## R1 — Smoke test: expected (CLAUDE.md §4) vs got (`metrics.json`, `sensitivity.csv`, `monthly_kpi.csv`, `validation_report.json`)

| Check | Expected | Got | OK? |
|---|---|---|---|
| Session rows · glued headers | 46,575 · 39 | 46,575 · 39 | ✅ |
| DC chargers · sites · attempts · unbound | 88 · 40 · 35,996 · 2,187 | 88 · 40 · 35,996 · 2,187 | ✅ |
| Visits | 29,036 | 29,036 | ✅ |
| FTCS quarter · 13 mo | 86.03 · 83.87 | 86.03 · 83.87 | ✅ |
| Attempt success 13 mo · quarter | 79.5 · 82.0 | 79.5 · 82.0 | ✅ |
| Troubled / failed, 13 mo · quarter | 10.4/5.8 · 9.3/4.7 | 10.4/5.8 · 9.3/4.7 | ✅ |
| Port-less share of failed attempts · port switch | 29.6 · 43.5 | 29.6 · 43.5 | ✅ (but see F3) |
| Sensitivity: >0 · ≥0.1 · site 2/10/15 · port 2 | 84.8 · 84.4 · 83.2/84.1/84.1 · 82.4 | same | ✅ |
| Monthly FTCS, Jan 24 → Jan 25 | 77.69 → 86.44 | 77.69 → 86.44 | ✅ |
| Lagging sites → projection | S40, S17, S01, S08, S28 → 87.01 | same (S28 margin 0.046 pt) | ✅ |
| Outages · fleet availability · silent · corr | 46 · 97.05 · 15 · 0.55 | 46 · 97.05 · 15 · 0.55 | ✅ |
| Illustrative: operator · federal · repair | 99.77 · 98.18 · 82.2→88.5 (n=25) | same | ✅ |
| S1 events · S2 work orders | 124,968 · 426 | 124,968 · 426 (event_ids unique) | ✅ |
| Validation summary | 16 / 13 / 1 | 16 / 13 / 1 (30 checks) | ✅ |
| `docs/evidence.md` table == generated `evidence_table.md` | identical | identical (`diff` empty) | ✅ |

No regression mismatches.

## R2 — Validation gate review

Every WARN is real, counted, documented in `validation_contract.md`, and has an action. The UNKNOWN (`organisational.kpi_owner`) is correctly UNKNOWN rather than FAIL. No WARN needs to become a FAIL. `day_coverage` could be argued up, because the published reporting-month FTCS covers 30 of 31 January days, but it is documented, so WARN is defensible. `validate.py` does implement every row the contract lists.

The contract misses these defects:
- **2,549 blank `peak_power_kw` values**, coerced to NaN and never checked (F2).
- **Header consistency across files** is not checked (F1).
- `energy_without_power` compares with `== 0`, so it misses 166 DC rows that have energy > 0 and a *blank* peak power.

Weak checks:
- `model.visit_integrity`: half of the condition is tautological (`value_counts().sum() == len`).
- `model.no_simulated_fields_in_kpi_inputs`: only checks three column names (F15).
- `S1.dashboard_reproducible`: runs the same algorithm on the same events. It proves reproducibility, not correctness (acceptable as labelled).
- `source_*_blank`: the WARN carries `evidence_count=0` (the populated count), which reads oddly next to a WARN.

## R3 — Reliability demos

| Demo | Expected | Got | Key log line | OK? |
|---|---|---|---|---|
| missing_column | 2 | 2 | `GATE … sessions.required_columns -> missing=['energy_kwh'] … no processed output published` | ✅ |
| duplicate_rows | 0 | 0 | `CLEAN \| exact duplicate rows collapsed=50`; KPI unchanged; WARN 14 | ✅ (but see F6) |
| stale_data | 2 | 2 | `sessions.freshness … lag=121.01 days (allowed 2)`, **plus** `day_coverage … 0.065` | ✅ (noisy, F18) |
| api_outage | 1 | 1 | `S1 2024-01 page=1: status 503 after 3 attempts` (waits 0.2 s, 0.4 s) | ✅ |
| bad_checksum | 2 | 2 | `Se_01_2024.csv … sha1_ok=False` → `retrieval.R1 … verified=12` | ✅ |
| Idempotency | same md5 | run1 = run2 = run3 for metrics.json, visits.csv, attempts.csv, validation_report.json, evidence_table.md | one `run_date=` folder, no `.tmp`/`.old` | ✅ |
| Final clean run | exit 0 | exit 0 | the published partition is again the clean one | ✅ |

## R4 — Code review, stage by stage

The core logic matches `kpi_definitions.json`:

| Rule | Where | OK? |
|---|---|---|
| DC classified per charger | `transform.py:26-35` | ✅ |
| Unbound attempts kept | `build_attempts`, plus the `attempt_row_conservation` check | ✅ |
| Site chain: port_id → name match → FAIL | `transform.py:50-62`, `validate.py:156` | ✅ |
| 150 m single-linkage clustering | `transform.py:78-92` | ✅ |
| Visit sort order and previous-row gap, [−2, +5] inclusive | `transform.py:148-153` | ✅ |
| Baseline = last 3 months, anchored to the data | `metrics.py:18-19` | ✅ |
| Lagging-site rule compared on unrounded values (rounding happens afterwards) | `metrics.py:47-62` | ✅ |
| Retries only on 429/5xx/timeouts, bounded; `retry_after_seconds` honoured; 4xx not retried | `extract.py:25,48-80` | ✅ |
| Raw payloads saved before parsing | `extract.py:122,151,174,206` | ✅ |
| Whole partition swapped | `save.py` | ✅ (rollback gap, F7) |
| Exit codes 0/1/2 | `run_pipeline.py:151-164` | ✅ |
| One-to-many merge validated | `transform.py:137` (`validate="many_to_one"`) | ✅ |

Two merges have no `validate=` argument: `transform.py:105` and `run_pipeline.py:132`. Both are 1:1 at charger level, so the risk is low (NIT).

## R5 — Integrity audit

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Every row-removing call is counted and logged or justified | PASS | malformed rows (counted, gated) · header rows (counted) · exact dupes (WARN) · non-DC scope (logged, 10,579 rows) · `dropna` in `resolve_sites` (unresolved → FAIL) |
| 2 | No silent column skips | **PARTIAL** | The `if col in out.columns` guards at `clean.py:70,73` are safe because `required_columns` FAILs first. But a reordered header silently mis-maps columns (F1). |
| 3 | No simulated field reaches FTCS | PASS | Attempts are built from R1 only, and the check passes. The check itself is only name-based (F15). |
| 4 | Business thresholds come only from config, never env | PASS (env) / **PARTIAL** (config) | No env reads for business rules. Several thresholds are hard-coded in code (F16). |
| 5 | No secrets committed; `.gitignore` covers the right paths | PASS for the one existing commit | `git log -p --all` shows no key-like strings; `.env` untracked. `.gitignore` covers `.env`, `course/`, `data/raw`, `data/processed`, `logs`, `.scratch`. **The final build is not committed yet**, so its history can't be checked. Keys can leak into *logs* (F8). |
| 6 | No `developer.nrel.gov` except the guard | PASS | Only the guard at `extract.py:143-144`, plus docs and rules that mention it. |
| 7 | Completeness proven for all four sources, and the run fails when incomplete | PASS | `check_retrieval` → FAIL → gate; `bad_checksum` demo exits 2. Caveats: R1 is checked against the listing, not against an expected 13 files (`day_coverage` and freshness partly back this up). The S2 manifest lives in the same DB it certifies. |

## R6 — Docs consistency

- README, evidence, data_model, source_map and gate2 all match `metrics.json`.
- Every other doc-quoted number I checked is correct: 6,899 / 474 / 27,777 kWh buckets · 1,671 DC · 99.9% zero · 2 min median · 2 single-charger sites · 326 suppressed lifecycles · 69.2% worst site.
- Links: 32 `.md` files, and one dead reference (`docs/agent/review_checklist.md` → `docs/diagrams`, which exists only in the old repo).
- No causal claims. "caused" appears only in "does NOT prove" cells.
- No named operator in any claim. TVA, BrightRidge and EnergyRight are mentioned only as context or inference.
- Stale numbers exist, but only in `decisions_log.md` (F11).
- Illustrative labels are missing in two places (F13).

## R7 — Grader view

| Pillar | Score | Evidence | Single biggest gap |
|---|---|---|---|
| Source reasoning (Class 4) | **5** | `docs/source_map.md` (questions → fields → source → owner, grain, SoR table, 7 gaps, diagram) | Rejected sources (Open Charge Map) are only in `research_sources.md` |
| Retrieval (Class 5) | **4** | `extract.py` (3 modes, SHA-1 + size, `total_results`, pagination, bounded retry, raw first) | Retry paths have no unit tests; API key can leak into logs (F4, F8) |
| Validation (Class 6) | **4** | `validation_contract.md` + `validate.py`: 30 checks with PASS/WARN/FAIL/UNKNOWN and actions | Numeric coercion and header drift are unchecked (F1, F2) |
| Workflow + metrics (Class 7) | **4** | `data_model.md` (ER, grain, KPI tree, "does NOT prove"), sensitivity table | The port-switch metric is overstated (F3) |
| Pipeline dependability (Class 8) | **4** | one command, exit codes, atomic swap, proven idempotent, 5 chaos demos | Chaos runs overwrite the real partition, raw data and log; thin failure-path tests (F4, F6) |

**Submission package:** README ✅ (problem, stakeholders, KPI, sources, setup/run, decision) · source map + diagram ✅ · one-command pipeline ✅ · evidence table with 5 metrics ✅ · Known/Unknown/Assumption/Limitation ✅ · demo-able judgement call ✅. **Pending: the final build is not in git.** The README's `git clone` currently gives the Phase-1 repo (as far as the local clone shows).

**§7 grader questions, and the file that answers each:**
1. What decision, for whom → `README.md` §1–2; `docs/evidence.md` Recommendation.
2. Where the truth lives for "did the driver get a charge" → `docs/source_map.md` §3.
3. How retrieval is known to be complete → `validation_report.json` `retrieval.*`; `docs/validation_contract.md` (technical checks); `pipeline/extract.py`.
4. What was refused a silent fix → `docs/validation_contract.md` "Assumptions recorded…"; `decisions_log.md` D2/C2; the `sessions.blank_port_id` WARN.
5. One row per table; what could inflate rows → `docs/data_model.md` §2; `model.attempt_row_conservation`.
6. How the metrics connect to the KPI → `docs/data_model.md` §3 KPI tree.
7. API failure / missing column / stale data → README chaos line; `docs/gate2_data_readiness.md`; live chaos runs (all verified above).
8. What the data can NOT tell → `docs/evidence.md` Unknown/Limitations and the "Does NOT prove" column.
9. Most important judgement call and its evidence → `decisions_log.md` D2; `demo_script.md` 1:15. The "~4 pts" figure is not produced by code (F12).

## R8 — Demo readiness

- Every file and command in `docs/demo_script.md` exists and works.
- Timing is 30 + 45 + 90 + 60 + 45 s = **4.5 min** ✅.
- The judgement call is crisp and correct: 99.9% zero-energy, 2-min median, all on DC chargers. Independently reproduced: dropping the attempts gives **90.33%** for the quarter (+4.30) and 88.92% over 13 months (+5.05).
- Gap: at 2:45 the script says "point at … the three gates", but a clean run logs **nothing** when a gate passes, and the WARNs never reach the console (F10).
- Gap: at 1:15 the script says to open `validation_report.json`. That file is git-ignored, so it isn't on GitHub. Run the pipeline before recording.
- Gap: the 3:45 line "Uptime 99.8%" needs "(simulated)" (F13).

**Likely viva questions and short honest answers:**

1. *Why not drop blank-port rows?*
   All are on DC chargers, 99.9% delivered 0 kWh, and the median length is 2 min, so they are failed attempts. Dropping them would give 90.3% for the quarter, falsely "hitting" the stretch target with no repair.
2. *How do you know a visit is one driver?*
   We don't; there are no driver IDs. The rule is UC Davis's 5-min site window, which our own fail-vs-success gap curves support (they cross near 5 min). FTCS stays within 82.4–84.8% across every variant tested. Two drivers who arrive within 5 min can merge (stated limitation).
3. *Isn't 1 kWh arbitrary?*
   It comes from a peer-reviewed source. The distribution is bimodal: 93.6% of sub-1 kWh attempts are exactly 0. Thresholds between 0 and 1 kWh move FTCS by ≤ 0.9 pt.
4. *Is 99.77% real?*
   No. It comes from the simulated feed and shows how exclusions can produce "99%". The only real availability figure is the inferred 97.05%.
5. *How do you know you got all the data?*
   Git-blob SHA-1 + size per file, `total_results`, `total_records` per month, and the manifest row count. Demo: `bad_checksum`.
6. *S28 is only 0.05 pt past the threshold?*
   Yes. It is compared on unrounded values, has 75 visits, and is flagged as borderline in the evidence.
7. *Did operations cause the 77.7 → 86.4 rise?*
   Unknown. 42 of 88 chargers were commissioned mid-window, so part of the rise is a mix effect.
8. *What if a column is reordered?*
   A missing column FAILs today. A reordered header is not caught yet (F1). Fix it before the viva.
9. *Why sites by distance?*
   The registry has 3 spelling variants for the same sites. Within-site distances are ≤ 33 m and the next site is 17 km away, so any threshold in between gives 40 sites.
10. *Why no ML?*
    No failure label or cause is recorded, and a model can't learn a label the system can't define.
11. *43.5% switch port — really?*
    Be ready for this one (F3). Physically switching charger is 27–33%.

---

## Findings

| ID | Severity | File:line / command | Finding | Why it matters (pillar) | Evidence | Fix |
|---|---|---|---|---|---|---|
| F1 | **MAJOR** | `pipeline/clean.py:40-44` | Only the first header is used. Later header rows are counted and skipped but never compared with it, so a file whose columns are reordered is parsed with the wrong column names, silently. | A silent schema-drift path that could swap `energy_kwh` (the KPI input) with another column while every gate passes. Validation / dependability. | Scratch test: file B with energy/peak swapped in its header → parsed as energy=60, peak=30, malformed=0, no warning. Real data: all 52 header occurrences are identical, so **today's KPI is safe**. | Compare each header with the first; count mismatches → FAIL in `check_raw_sessions` (or map columns by name per file). Add a test. |
| F2 | **MAJOR** | `clean.py:71,84` · `validate.py:78-149` | `to_numeric(errors="coerce")` output is counted (`unparseable_numbers=2549` in `run_manifest.json`) but never validated, logged or documented. All 2,549 are blank `peak_power_kw` (1,952 unbound rows, 597 bound). | NaN energy evaluates as `NaN >= 1 → False`, i.e. a silent failed attempt. Energy has 0 NaN today, so the KPI is unaffected, but nothing would stop a bad export. An undocumented data-quality issue (5.5% of rows). Validation. | Probe: energy_kwh unparseable = 0; peak_power_kw = 2,549, all `''`. 166 DC rows with energy > 0 and blank peak also escape `energy_without_power`. | Add `sessions.numbers_parse`: energy NaN → FAIL (over a tolerance), peak blank → WARN with count. Add a contract row and a limitation line. |
| F3 | **MAJOR** | `metrics.py:149`, `transform.py:160` | "43.5% of retry visits switch port" is overstated. (a) Every DC charger has exactly one port id (88/88), so an `UNBOUND@C → C` retry, where the driver stayed on the same charger, counts as a switch. (b) The denominator is all multi-attempt visits, 23.9% of which succeeded on the first try. | A "Known (from real data)" claim, repeated in the evidence table, the KPI tree and D3, overstated by up to ~16 pts. Workflow + metrics. | Charger switch = 32.9% of multi-attempt visits; 27.2% of visits whose first attempt failed. `port_key` switch among first-failed visits = 40.5%. | Define as `charger_id.nunique() > 1` among visits with `first_attempt_success == False`, and relabel in docs. D3's argument (port-level grouping splits retries) still holds as stated. |
| F4 | **MAJOR** | `tests/` | The 9 tests cover the happy path and freshness. Untested: the retry path (5xx → OK, 429 honours `retry_after`, 404 not retried, bounded), conflicting duplicate → FAIL, unresolved site → FAIL, lagging-site rule and baseline months, malformed rows. | Leaves failure paths untested. They are demonstrated only by manual chaos runs. Dependability / retrieval. | `pytest -q` → 9 tests; none import `http_get_with_retry`. | About 6 small tests with a fake `requests.Session`. |
| F5 | MINOR (high business value) | `inference.py:37-42` | Right-censored outages are never recorded, because a window closes only on the charger's next success. Also, `excluded_outside_commissioned_life` is always 0 by construction. | S29 chargers `13664401` and `13164881` have **no sessions after 5–6 Jan 2025**, while site-mates logged 74 and 77 successes (k needed: 31 and 45). That is the freshest "needs a crew/check now" signal in the reporting month, and the output never mentions it. Could be decommissioning. Workflow / decision. | Probe output above. | Emit "open at data end" runs as a WARN list (excluded from availability) and add them to the crew/verification list. |
| F6 | MINOR | `run_pipeline.py:146,153`; `logging_utils.py:12` | Chaos runs share the real run's paths. `--chaos duplicate_rows` publishes over `run_date=2025-02-01`. Failed chaos runs overwrite `data/raw/run_date=…` (bad_checksum leaves a corrupted CSV there) and `logs/pipeline_2025-02-01.log`, which gate2 cites as evidence. A stale `logs/validation_2025-02-01.json` survives later successful runs. | Breaks raw ↔ processed lineage after a demo, and a grader may open chaos output. Dependability. | metrics.json md5 changed from `81867…` to `8068…` (WARN 14) after the duplicate_rows demo. `validation_2025-02-01.json` is still present after 2 clean runs. | Write chaos runs to `run_date=<d>__chaos=<name>` (or skip publishing), timestamp log names, and delete the stale validation file on success. |
| F7 | MINOR | `save.py:38-42` | If the second rename fails, the `except` block deletes tmp but never restores the backup, so no published partition remains. | The atomic-publish claim holds for half-writes but not for rollback. Dependability. | Probe with a monkey-patched rename: dir = `['.old_run_date=2025-02-01']`, target missing. | In `except`: `if backup and backup.exists() and not target.exists(): backup.rename(target)`. |
| F8 | MINOR | `extract.py:56-59` | On a connection error the `requests` exception text includes the full URL with `?api_key=…`. It is written to the log file and printed to the console. | Logs are git-ignored, so nothing is committed, but a live demo recording or a pasted log would expose a real key. Retrieval / security. | Probe with a fake key: found in both the log line and the RetrievalError message. | Redact `api_key=[^&\s]+`, or send the key as the `X-Api-Key` header. |
| F9 | MINOR | `clean.py:66-68`, `requirements.txt` | `dtype == object` is False for pandas ≥ 3 text columns (`str`), so whitespace stripping is skipped. Requirements say `pandas>=2.0`, unpinned; this venv has 3.0.6. | Latent: no padded cells today (checked), but a `" "` port_id would stop being treated as unbound. Dependability. | Probe: dtype `str`, `== object` → False. | Use `select_dtypes(["object", "string"])` or `is_string_dtype`, and pin `pandas>=2.0,<4`. |
| F10 | MINOR | `validate.py:189-192` | Gates log nothing when they pass, and the 13 WARNs never reach the console or the log file. | Demo 2:45 says "point at … the three gates"; nothing is shown. Useful logging (Class 8). | `grep -c 'VALIDATE\|GATE'` on a clean run → 0. | Log one line per gate, e.g. `VALIDATE \| gate=content PASS=9 WARN=11 [names]`. |
| F11 | MINOR | `docs/decisions_log.md` D1 (12,19,23), D2 (58), D3 (85,91), D4 (118-121), D5 (137-138) | Stale numbers not marked as superseded: "1 in 6" / 83.8% in the D1 decision line; 29.7%; 42.3%; "83.2% / 7.6%" (the table says 7.5%); "35 sites / 80 chargers, 44 windows, 14 silent, corr 0.59"; "S01–S43"; `notebooks/`. | A grader cross-checking D4 against evidence.md sees 44/14/0.59 vs 46/15/0.55. Now: 38 multi-charger sites / 86 chargers, 46, 15, 0.55. | grep output. | Add "(superseded by D7: now …)" notes; keep the history visible. |
| F12 | MINOR | `validation_contract.md:125`, D2, `demo_script.md` | The judgement call's "~4 pts" is not produced by any code. | CLAUDE.md red flag: a number in docs that no code produces, on the most important judgement call. | Independent reproduction: quarter 86.03 → 90.33 (+4.30); 13 mo 83.87 → 88.92 (+5.05). | Add a "drop unbound (rejected)" sensitivity row, and say "would show 90.3%, the stretch target, with no repair". |
| F13 | MINOR | `README.md:16-17`; `demo_script.md` 3:45 | 98.18% "federal-style" is not labelled illustrative in the README. The demo's spoken line "Uptime 99.8% vs driver success 86%" has no simulated label. | CLAUDE.md R6 requires illustrative metrics to be labelled everywhere. | Read. | Add "(both from the simulated status feed)". |
| F14 | NIT | `metrics.py:92-109`; evidence row 5 | The "repair effect: median FTCS 82.2 → 88.5" figure is charger-level first-attempt success, not FTCS, and has no control for the fleet-wide trend (about +0.7 pt/month). | Labelling honesty. I checked the before-window is not contaminated by the outage itself (only 3 first attempts fall inside outages). | Probe. | Rename it "charger first-attempt success"; add "no control group" to "does NOT prove". |
| F15 | NIT | `validate.py:170,173` | `visit_integrity` is half-tautological; `no_simulated_fields` only checks three column names. | Checks look stronger than they are. | Read. | Assert attempt `session_id`s ⊆ R1 ids and columns ⊆ an allowlist. |
| F16 | NIT | `validate.py:61,83,147,185`; `metrics.py:92,132`; `build_client_systems.py:64` | Hard-coded thresholds: 0.1%, 45 d, 0.05 pt, 30 d / n ≥ 20, 14 d. The simulator repeats the −2/+5 visit window instead of reading it from config. | Makes the "every rule in config" claim only partly true. | grep output. | Move them to config (or document them as technical constants). |
| F17 | NIT | `extract.py:66-76` | A `Retry-After` value in HTTP-date form makes `float()` raise ValueError, which exits via "unexpected error". A server-supplied wait has no cap. The last attempt logs a `wait=` it never performs. | Robustness and log accuracy. | Read; api_outage log shows `wait=0.8s` on attempt 3/3. | Parse the value defensively, cap it with `min(wait, 60)`, and don't log a wait on the final attempt. |
| F18 | NIT | `run_pipeline.py:99-101` | The `stale_data` demo also fails `day_coverage` (0.065), because the 120-day shift creates a partial first month. | The demo message shows two failures. | chaos output. | Shift by whole months, or explain it in the demo. |
| F19 | NIT | `save.py:224` | `mkdtemp` creates the published partition with mode 0700 (`drwx------`). | Other users or services can't read the output. | `ls -la`. | `chmod 0o755` after the rename. |

## Top 5 improvements, ranked by rubric impact per hour

1. **Commit and push the final build, then smoke-test a fresh clone** (`git clone … && pip install -r requirements.txt && python run_pipeline.py --offline && pytest -q`). About 15 min. Without it, the grader clones Phase 1.
2. **Close the two silent paths and make the gates visible:** the header-consistency FAIL (F1), `sessions.numbers_parse` (F2), and one log line per gate (F10). About 45 min. Validation and dependability, and it fixes demo step 2:45.
3. **Make the judgement call code-produced** by adding the "drop unbound (rejected)" sensitivity row (F12), and mark the stale decisions-log numbers as superseded (F11). About 30 min. Strongest demo moment.
4. **Fix the port-switch metric** (F3) and update evidence.md, data_model.md and D3. About 30 min. Workflow and metrics honesty.
5. **Add failure-path tests** (F4), with F6 (chaos runs to a separate partition) and F7 (rollback) as quick wins alongside. About 1–1.5 h. Dependability.

## Questions for the owner

- Has the final build been pushed to GitHub? The local clone shows only the Phase-1 commit.
- S29's two chargers go dark on 5–6 Jan 2025 (F5). Should open-at-data-end runs be surfaced for crews or verification? Decommissioning can be checked against the registry.
- The locked decision D3 relies on "port switching" as a rationale. Are you OK restating the behavioural figure as a charger switch (27–33%) while keeping D3 unchanged?
- The review runs created git-ignored artefacts (`data/processed/run_date=2025-02-01/`, `data/raw/run_date=2025-02-01/`, `logs/`, `__pycache__`, `.pytest_cache`). Keep or clean?

## What is strong (keep it)

- **Every regression target reproduces exactly.** Outputs are byte-identical across reruns; all 5 chaos demos give the documented exit codes.
- **Completeness proofs are real, not asserted:** git-blob SHA-1 + size per file, `total_results`, per-month `total_records`, a manifest row count, and a gate that stops the run.
- **The D2 judgement call is correct and well evidenced**, and it becomes a finding (29.6% of failures can't be located).
- **Visit-rule rigour:** a fully specified sort, previous-row gap semantics, a sensitivity table with the rejected alternative shown, and "does NOT prove" on every finding.
- **Clean separation of concerns:** env settings vs versioned business config; simulated data labelled at source and gated; illustrative metrics mostly labelled; honest provenance (fictional persona, no named operator).
- **Corrections log C1–C10** is exactly the kind of judgement evidence graders reward.
