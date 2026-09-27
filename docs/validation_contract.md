# Validation Contract (Class 6) — executable in `pipeline/validate.py`

**Latest run (2025-02-01): 33 checks — PASS 17 · WARN 15 · UNKNOWN 1 · FAIL 0.**

Format: **business assumption → data expectation → executable check → severity → action**.
Severities: **FAIL** stops the run (exit 2, nothing published) · **WARN** = known issue handled by an explicit, counted
rule · **UNKNOWN** = the data cannot answer the question. The latest results for every run are in
`data/processed/run_date=<d>/validation_report.json` (or `logs/validation_<d>.json` when a gate stops the run).
Every gate logs its counts on pass (`VALIDATE | content gate PASSED | PASS=4 WARN=11`) and one line per WARN/UNKNOWN,
so the console shows what was accepted and why. Gate tolerances live in `config/kpi_definitions.json` →
`validation_tolerances` (D8), never in code or environment variables.

## Technical checks

| Business assumption | Data expectation | Check (`validate.py`) | Severity | Action | Latest result |
|---|---|---|---|---|---|
| We received every export exactly as published | 13 files; size and git-blob SHA-1 match the HF tree API | `retrieval.R1 session exports` | FAIL if any mismatch | Stop; re-download | PASS 13/13 |
| We received the whole registry | `len(fuel_stations) == total_results` | `retrieval.R2 AFDC registry` | FAIL | Stop | PASS 4,593/4,593 |
| We received the whole status feed | received == `total_records` for every month | `retrieval.S1 status feed` | FAIL | Stop | PASS 124,968 |
| We read the whole work-order table | rows == generation manifest | `retrieval.S2 work orders` | FAIL | Stop | PASS 426 |
| The export schema is what the pipeline expects | 9 required columns present | `sessions.required_columns` | FAIL | Stop — never skip a missing column silently | PASS |
| Every monthly file has the same layout | every header row identical to the first file's | `sessions.header_consistency` | FAIL | Stop — a reordered or renamed column is never re-mapped by guesswork; confirm the new layout with the CPMS vendor | PASS 52/52 identical |
| Files are well-formed | headers not glued onto data rows | `sessions.glued_headers` | WARN | Repair (newline), count, log | WARN 39 repaired |
| Rows have the right number of fields | 0 malformed | `sessions.malformed_rows` | FAIL > 0.1%, WARN > 0 | Stop / count | PASS 0 |
| Timestamps are usable | parseable UTC | `sessions.timestamps_parse` | FAIL > 0.1% | Stop | PASS 0 |
| Numbers are usable | `energy_kwh` always parses; peak power may be blank | `sessions.numeric_parse` | FAIL if any `energy_kwh` is missing (it would silently count as a failed attempt) · WARN for blank peak power | Stop / count; peak power left missing, never imputed — it is only used for DC classification (max per port) and the physics check | WARN 2,549 blank `peak_power_kw` (1,952 on port-less rows); 0 missing energy |
| One row = one session | no session_id with conflicting values | `sessions.session_id_unique` | FAIL | Stop — cannot choose silently | PASS |
| Exports are not duplicated | exact duplicate rows collapse | `sessions.exact_duplicates` | WARN | Keep one, count, log | none (demo: `--chaos duplicate_rows` → 50 collapsed) |
| Session physics make sense | energy > 0 implies peak power > 0 | `sessions.energy_without_power` | WARN | Flag; **not** reclassified (energy is the KPI input) | WARN 1,766 |
| Durations are plausible | ≥ 0 and ≤ 24 h | `sessions.duration_range` | WARN | Flag | WARN 89 > 24 h |
| A port serves one car at a time | no overlaps on a port | `sessions.port_overlaps` | WARN | Visit rule tolerates −2 min | WARN 23 |
| Every day is present | each month fully covered | `sessions.day_coverage` | WARN < 100%, FAIL < 90% | Report missing days; request re-export | WARN 13 days |
| Data is current for the reporting month | latest start within 2 days of the reporting month's end | `sessions.freshness` | FAIL | Stop (demo: `--chaos stale_data` withholds the January export → lag 32 days) | PASS lag 1.01 d |
| — | age vs today | `sessions.wall_clock_age` | WARN | Label as historical backfill | WARN 604 days |

## Semantic checks

| Business assumption | Data expectation | Check | Severity | Action | Latest result |
|---|---|---|---|---|---|
| A blank error field means success | `session_error` populated for failed sessions | `sessions.session_error_semantics` | WARN | **Rejected assumption**: failures inferred from energy < 1 kWh (D2) | WARN 0 of 46,575 populated |
| Rows without a port are bad data | — | `sessions.blank_port_id` | WARN | **Kept** as unbound failed attempts (99.9% are 0 kWh) — dropping would inflate FTCS by 4.30 pts to 90.33% (`metrics.json → judgement_call`) | WARN 2,187 kept |
| The export tells us the site | `site_id`/`station_id` populated | `sessions.source_site_id_blank`, `…station_id_blank` | WARN | Resolve sites from the registry instead | WARN (always blank) |
| Charger names identify sites | names stable, prefix = site | `sessions.evse_name_stability` | WARN | Names are not used as keys; prefix is an owner | WARN 12 blank, 19 renamed |
| Registry addresses identify sites | one spelling per site | `model.address_variants` | WARN | Cluster by coordinates (150 m) | WARN 43 → 40 |
| Registry status describes 2024 | snapshot date ≈ data period | `model.registry_temporal_alignment` | WARN | Use registry for identity/location only | WARN |
| Every DC charger has a site | 0 unresolved | `model.site_resolution` | FAIL | Stop | PASS (86 port id + 2 name) |
| An outage we cannot close is still worth a look | no inferred outage run still open when the data ends | `model.open_outages_at_data_end` | WARN | List for on-site verification; never counted as downtime (could be a decommissioning) | WARN 2 — S29 chargers 13664401, 13164881, no session for ~25 days |
| The operator's dashboard is computed from its own data | dashboard == recomputed NOC uptime | `S1.dashboard_reproducible` | WARN | Investigate the dashboard logic | PASS 99.77% = 99.77% |

## Integrity & organisational checks

| Assumption | Check | Severity | Latest result |
|---|---|---|---|
| Nothing is lost between sessions and attempts | `model.attempt_row_conservation` (DC rows == attempts) | FAIL | PASS 35,996 = 35,996 |
| Every attempt belongs to exactly one visit | `model.visit_integrity` — every attempt has a visit id, visit ids unique, attempt counts add up, outcomes from the defined set | FAIL | PASS 29,036 visits / 35,996 attempts |
| Simulated data is labelled | `S1.labelled_simulated`, `S2.labelled_simulated` | FAIL | PASS |
| Simulated data never reaches the KPI | `model.no_simulated_fields_in_kpi_inputs` — checked by content: KPI inputs are R1 columns plus an allowlist of derived columns, and every attempt is an R1 `session_id` | FAIL | PASS |
| Someone owns the KPI definition | `organisational.kpi_owner` | UNKNOWN | UNKNOWN — four stakeholders disagree; sign-off needed |

## Assumptions recorded instead of silently fixed

- A zero/near-zero-energy session is an **inferred** failed attempt; its cause is unknown.
- Visits are reconstructed without driver identity; two drivers arriving within 5 minutes at a busy site can merge.
- The failure rate is a **lower bound**: attempts that never created a session are invisible.
- Outage windows are **inferred** statistically; single-charger sites (2 sites) cannot be inferred.
- An inferred outage still open when the data ends is **listed for verification, not counted** — it cannot be told
  apart from a decommissioning.
