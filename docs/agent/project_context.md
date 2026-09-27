# Project Context — detailed reference
> Deep reference for coding agents and reviewers. Loaded on demand (not every session).
> **Authority order if anything conflicts:** `docs/decisions_log.md` → `config/kpi_definitions.json` → `CLAUDE.md` → this file.
> Regression numbers live in `docs/agent/reference_numbers.md`; review criteria in `docs/agent/review_checklist.md`;
> EV-charging domain knowledge in `docs/agent/domain_primer.md`.
> Section numbers are kept from the original Phase 1 file: §4 (locked decisions) and §11 (phase status) now live in
> `CLAUDE.md`; §8 (reference numbers) lives in `docs/agent/reference_numbers.md`. Current numbers there win.


---

## 1. The assignment (what is being graded)

**Course:** Forward Deployed Engineering (FDE) course, Scaler School of Technology × AIStudio. Assignment 2:
*"FDE Data Foundations — Classes 4–8 | From Client Data to a Dependable Pipeline."* Top submissions lead to interviews.
**Deadline: 2026-09-27 (today).**

**Objective (verbatim intent):** take a realistic operational problem from messy source data to a small, explainable,
dependable pipeline that produces trustworthy business metrics. *"The goal is not 'I analysed a dataset.' The goal is
'I built a trustworthy path from client systems to a business decision.'"*

**Track chosen:** C — own problem (EV fast-charging reliability), built on real public data + clearly-labelled
simulated client systems.

**Rubric — five pillars, 20% each**

| Pillar | Class | Evidence required |
|---|---|---|
| Source reasoning | 4 | Business questions → required information → source systems; source **ownership**, **grain**, important **gaps** |
| Retrieval | 5 | **≥2 retrieval modes** (SQL / API / files); **prove retrieval is complete**; **preserve raw inputs** |
| Validation | 6 | Profile data; meaningful quality issues; **business-oriented validation rules**; record assumptions/limitations **instead of silently fixing** |
| Workflow + metrics | 7 | Entities, events/states, interactions/interventions/outcomes; simple relational/event model; **3–5 metrics linked to the KPI** |
| Pipeline dependability | 8 | ingest → validate → transform/model → metric output; **logging/checks, rerun behaviour, failure handling** |

**Submission package (all required)**
1. Public GitHub repo with the complete project.
2. `README.md`: problem, users/stakeholders, project KPI, source overview, setup/run instructions, **decision the output supports**.
3. Source map + workflow/data-model diagram in the repo (simple is fine).
4. Code/notebooks showing retrieval, validation, modelling, joins/aggregations, metrics, **and one runnable
   pipeline/script that reproduces the final output from raw inputs**.
5. Final evidence table/dashboard with **3–5 metrics** + a **Known / Unknown / Assumption / Limitation** section.
6. A 3–5 minute demo using the repo, explaining **one important FDE judgement call**.

Graders explicitly do **not** grade project size or UI polish. They want explicit, defensible choices connected to the KPI.

---


---

## 2. Course methodology this project must visibly follow

- **Class 4 — "Where does the truth live?"** Start from the problem, not the dataset. Chain:
  *Problem → Questions → Information → Fields → Sources → Owner.* Relevant ≠ authoritative. A system of record is a
  business + system decision (ownership, freshness, replication, semantics) — *the newest value is not automatically the
  truth.* Minimum data > all data. **Missing data is a product signal** (some data problems are workflow/instrumentation
  problems). Outputs: data-source map, required-fields list, source-of-truth decisions with reasoning.
- **Class 5 — Retrieval.** State definitions before calculating. Preserve raw responses. Handle pagination, retry
  transient 429/500 with bounded backoff, fail clearly otherwise, **prove completeness** (e.g., received == `total_records`).
  "A successful HTTP 200 on one page does not prove the job succeeded." Observed vs **inferred** facts must be labelled.
- **Class 6 — Validation.** Business claim → assumptions → **validation contract** (assumption → data expectation →
  executable check → severity/action) → targeted checks → stakeholder clarification → **PASS / WARN / FAIL / UNKNOWN**
  → publish decision. Three validation types: technical, semantic, organisational (who owns the KPI definition?).
  Never encode ambiguous thresholds/mappings without ownership. Representation fixes (case/whitespace) are safe;
  semantic mappings need an owner.
- **Class 7 — Model the workflow.** Entities, events, states, actions; interaction → intervention → outcome; aggregate
  one-to-many tables *before* joining to the outcome grain; 3–5 metrics (at least one outcome, one interaction, one
  intervention metric); for every finding state *what it tells the business and what it does NOT prove*;
  "the smallest useful model that explains the workflow and supports the KPI."
- **Class 8 — Dependable pipeline.** extract → validate → clean → transform → save → log; config outside core logic;
  bounded retries; raw preservation; required-column / null / duplicate / freshness checks; useful failure messages;
  **idempotent output by logical run date** (same partition atomically replaced, never appended); one-command run;
  chaos/failure demos; Gate 2 data-readiness review. Exit codes in the reference: `0` success, `2` validation-gate stop,
  `1` unexpected failure.

**Course reference repos (patterns to reuse — do not copy blindly):**
- Class 5–7 pack: https://github.com/manangupta12/flasheats-classroom-pack
- Class 8 pipeline: https://github.com/manangupta12/flasheats-data-pipeline

**Known flaws in the Class 8 reference pipeline — do NOT reproduce them:**
1. `transform.py` selects Dispatch columns `assigned_driver_id` / `reassignment_count` that do not exist; a list
   comprehension drops them silently → reassignment data vanishes with no warning. **Rule for us: a requested column
   that is missing is a validation FAIL, never a silent skip.**
2. Only the CSV output is written atomically; `metrics.json` and `validation_report.json` are not. **Rule: write the
   whole run partition to a temp directory, then atomically swap it in.**
3. No cross-source key/coverage checks. **Rule: every join reports match coverage % and is gated.**
4. Raw pages from a previous run can linger in the raw partition. **Rule: clear/replace the raw partition per run.**

---


---

## 3. The project

**Client persona:** *Voltra Charging Network* — a **fictional** operator persona (continuity with Assignment 1).
The data underneath is **real public data** (see §6). We do **not** attribute results to any named real operator:
the dataset does not identify itself as a specific network, so naming one would overclaim.

**Headline:** *"Our fast chargers report 99% uptime — so why do 1 in 7 drivers fail on their first try?"*

**Business problem (SMART, approved):** First-time charge success across **88 DC fast chargers at 40 sites** was
**83.87%** over 13 months (Jan 2024–Jan 2025) and **86.03%** in the most recent quarter (Nov 2024–Jan 2025).
One in five attempts delivered no usable energy, yet **none of 46,575 sessions carried an error code**. **29.6%** of failed
attempts died before a port was even recorded. Failures are fleet-wide, not confined to a few chargers, so the cause
cannot be found from today's data.

**Target (6 weeks):** lift first-time charge success from **86.0% → ≥ 87%** by bringing the **5 lagging sites** to the
network median, **and** close the diagnostic gap (every failed attempt carries a port and a cause), so a **≥ 90%**
target can be set credibly next quarter (industry context: most US states sit in the 90–95% reliability range).

**This project builds:** a dependable monthly pipeline from Voltra's systems that measures first-time charge success
consistently, shows which sites/chargers drive failures, and flags where reported uptime and driver reality disagree.

**Decision the output supports:** *Which sites need crews now, and what must the operator start recording before it can
fix the rest?* (Secondary: can leadership keep using "uptime" as its reliability headline?)

**Stakeholders (Class 4 ownership lens):**
| Stakeholder | Role | Owns / cares about |
|---|---|---|
| VP Operations / NOC | Outcome owner; runs the uptime dashboard | The "99% uptime" claim; status feed (S1) |
| Grants & Compliance | Reports to funders (NEVI-style rules) | Federal uptime definition (>97%), EV-ChART reporting |
| Customer Experience | Voice of the driver | First-try success, failed visits |
| Field-service vendor | Repairs chargers | Work orders (S2), SLAs |
| Site hosts (local power companies) | Host/own sites | Site performance, reputation |
| Charging-software platform (CPMS vendor) | System of record for sessions | Session exports, error fields |
| Drivers | End users | Getting a charge on the first try |

---


---

## 5. KPI and metric definitions (implement exactly)

All definitions live in versioned config `config/kpi_definitions.json` and must be echoed into every run's output.

1. **DC charger** — a `charger_id` that has at least one identified port whose max `peak_power_kw` > 20 kW across the
   data. DC classification is at **charger** level (not port), because failed attempts have `peak_power_kw = 0`.
2. **Attempt** — one session row on a DC charger (including rows with blank `port_id`).
3. **Failed attempt** — `energy_kwh < 1.0`. **Successful attempt** — `energy_kwh ≥ 1.0`.
4. **Unbound attempt** — blank `port_id` on a DC charger. Keep it; attribute to its charger and that charger's site;
   `port_key = "UNBOUND@<charger_id>"`. (99.9% of these are zero-energy failures.)
5. **Site resolution chain** (per charger): (a) any of the charger's `port_id`s matches an AFDC `ev_network_ids.posts`
   entry → site = normalised `street_address|city` of that AFDC record; (b) else fuzzy name match of `evse_name` vs AFDC
   `station_name` (difflib, cutoff 0.85) → that record's address; (c) else `UNRESOLVED|<charger_id>` (log + count).
   Current result: 86 chargers via (a), 2 via (b), 0 via (c) → 43 address strings → **40 sites** after 150 m clustering (D7).
   Note: AFDC lists *each charger as its own "station"*; the physical site is the **address cluster**, not the AFDC id.
   The text before "/" in `evse_name` is the **owning organisation**, *not* a site (e.g. `BRIGHTRIDGE EV / BR-JC LIBRARY`
   vs `BRIGHTRIDGE EV / BR-JONESBOROUGH`).
6. **Visit** — sort attempts by (`site`, `session_start`); a new visit starts unless the gap
   `session_start − previous session_end` at the same site is within **[−2, +5] minutes** (the −2 min tolerance absorbs
   small overlaps/clock skew). Evidence: fail-vs-success gap ratio is 13.8× in the first minute and drops below 1 after
   5 min; UC Davis (Gamage et al., 2024) validated 5 min with user IDs.
7. **Visit outcomes** — *First-time success*: first attempt succeeded. *Troubled success*: first failed, a later one
   succeeded. *Failed visit*: no attempt succeeded. *Attempts per visit*: mean attempts.
8. **Project KPI — First-Time Charge Success rate (FTCS)** = visits with first-time success ÷ all visits.
9. **Sensitivity lines (always reported, never headline):** FTCS at `>0 kWh`; FTCS with a 2-min and 10-min window.
10. **Baseline** for targets = most recent 3 complete months, not the full-period average (the trend is rising).

Candidate metric set (finalise in Phase 5): FTCS (outcome/KPI), failed-visit rate (outcome), troubled-success /
retry rate (driver interaction), unbound-attempt share (instrumentation gap), reported-uptime-vs-FTCS gap and repair
effect (intervention — *illustrative, uses simulated S1/S2*).

---


---

## 6. Data sources

### Real sources
**R1 — Charging session exports (files over HTTP)**
- Hugging Face dataset `shadenn/EV_Charging_demand`, folder `raw_charging_stations/`, files `Se_MM_YYYY.csv`
  (13 files, Jan 2024 → Jan 2025). License **CC-BY-4.0** (attribute in README).
- List files + checksums: `GET https://huggingface.co/api/datasets/shadenn/EV_Charging_demand/tree/main/raw_charging_stations`
  → each item has `path`, `size`, `oid` (git blob SHA-1).
- Download: `https://huggingface.co/datasets/shadenn/EV_Charging_demand/resolve/main/raw_charging_stations/<file>`
- **Completeness proof:** every file's byte size == API `size` AND `sha1(b"blob %d\0" % len(data) + data) == oid`.
  (Verified 13/13 on 2026-09-27.)
- Columns (EV-ChART Module 2–style): `provider_id, station_id, site_id, charger_id, evse_id, evse_name, port_id,
  connector_id, session_id, session_start, session_end, session_error, energy_kwh, peak_power_kw, payment_method,
  payment_other, eMI3 Port id`. Timestamps are UTC (`Z`). `station_id` and `site_id` are 100% blank.
- Grain: one row per session (attempt). Owner (persona): CPMS vendor / charging-software platform. Only provider: ChargePoint Network.

**R2 — AFDC station registry (REST API)**
- `GET https://developer.nlr.gov/api/alt-fuel-stations/v1.json?api_key=<KEY>&fuel_type=ELEC&state=TN,AL,KY,MS,GA,VA,NC&ev_network=ChargePoint%20Network&limit=all`
- `DEMO_KEY` works but is rate-limited to **10 requests/hour** (header `x-ratelimit-limit: 10`). Use `AFDC_API_KEY` env var (free key from developer.nlr.gov).
- Completeness: `len(fuel_stations) == total_results`. Regional pull on 2026-09-27: 4,593 stations.
- Fields used: `id, station_name, street_address, city, state, latitude, longitude, status_code, ev_network_ids{station,posts},
  ev_dc_fast_num, ev_level2_evse_num, date_last_confirmed, updated_at, open_date`.
- `ev_network_ids.posts` matches R1 `port_id` (not `charger_id`/`evse_id`). eMI3 ids differ in type (`USCPIE…` EVSE vs
  `USCPIL…` location) and do not join.
- **Temporal caveat:** registry is a *today* snapshot; sessions end Jan 2025. Registry `status_code = E` today says
  nothing about availability in 2024. Owner: US DOE (public registry) — **relevant, not authoritative** for availability.

### Simulated client systems (labelled `data_origin = "simulated"`; live in `data/simulated_client_systems/`)
**S1 — Charger status feed (mock REST API, `simulate/mock_status_api.py`, default `http://127.0.0.1:8001`)**
- OCPP 1.6-style `StatusNotification` events per port. Derived from real sessions: success → Preparing → Charging →
  Finishing → Available; failed attempt → Preparing → Available with `errorCode = NoError` (mirrors the real blank
  `session_error`); unbound attempts emit nothing; the **46 real inferred outage windows** → Faulted/Unavailable.
- Invented attributes only: fault code, and the split of outage windows into counted vs excluded categories
  (maintenance / utility), which reproduces the operator's "99%" under the NOC definition.
- API behaviour: paginated (`page`, `page_size`, `has_more`, `total_records`), `month=YYYY-MM` filter, one deterministic
  HTTP 500 and one HTTP 429 (FlashEats pattern). Endpoint for the operator dashboard claim (uptime summary).

**S2 — Maintenance work orders (SQLite CMMS, `data/simulated_client_systems/sim_cmms.db`)**
- One corrective work order per real inferred outage window (closed when the charger resumed real charging) + quarterly
  preventive maintenance per charger. Invented: detection lag, trigger, action, resolution code.
- Repair effect is measured on **real** sessions (FTCS before vs after closure).

**Client brief** `data/simulated_client_systems/client_brief.json`: leadership claim ("99% uptime") and conflicting
stakeholder definitions of uptime/reliability; no documented KPI owner (mirrors FlashEats' metric-definitions file).

**Real-data outage inference (the anchor for S1/S2):** at multi-charger sites (38 sites, 86 chargers), a charger's
share *p* of the site's successful sessions is computed; a run of *k* consecutive successful site sessions on other
chargers is flagged when (1−p)^k < 0.001 (p ≥ 0.1), bounded to the charger's commissioned life (first→last session).
Result: 46 windows, fleet availability 97.05%, 15 "silent" chargers (≥99% available but first-attempt success < 80%),
corr(availability, FTCS) = 0.55. Single-charger sites (2) cannot be inferred. This is **inferred, not observed**.

---


---

## 7. Known data defects and traps (handle explicitly — count + log each)

| # | Defect (real data) | Count | Required handling |
|---|---|---|---|
| 1 | Header row glued onto a data row mid-file (no newline) — `...*2provider_id,station_id,...` | 39 across 13 files | Repair by inserting newline before glued header; drop header rows; count per file |
| 2 | `session_error` never populated | 0 of 46,575 | Blank ≠ success. Semantic finding; do not infer "no error" |
| 3 | Blank `port_id` | 2,187 (4.7%) — all on DC chargers, 99.9% zero-energy | **Keep as unbound failed attempts** (D2). Dropping them inflates FTCS ~4 pts |
| 4 | `energy_kwh > 0` but `peak_power_kw = 0` (physically inconsistent) | 1,766 all / 1,671 DC | WARN; do not reclassify |
| 5 | Sessions > 24 h | 89 all / 4 DC | WARN |
| 6 | Overlapping sessions on the same port | 23 (DC) | WARN; visit logic tolerates −2 min |
| 7 | `evse_name` prefix is organisation, not site | 39 orgs vs 40 sites | Site via registry resolution + 150 m clustering (§5, D7) |
| 8 | AFDC lists each charger as a separate "station" | 86 records → 43 address strings → 40 sites | Cluster by coordinates (D7) |
| 9 | No shared join key between R1 and R2 except `port_id ↔ posts` | 86/88 DC chargers via port, 2 via name | Report coverage %; gate |
| 10 | Registry is a 2026 snapshot vs 2024 sessions | — | Temporal misalignment → limitation |
| 11 | Network growth: 42 of 88 DC chargers commissioned during the window; 3 stopped reporting | — | Mix effect on trends; report per-charger life |
| 12 | Near-zero energy is an *inferred* failure: cause could be charger, vehicle, driver, or payment | — | Attribution unknown → Known/Unknown section |
| 13 | Failed attempts before session creation are invisible | — | Failure rate is a **lower bound** |
| 14 | Every monthly export ends at 23:59 UTC on the second-to-last day | 13 of 397 days missing | WARN `sessions.day_coverage`; limitation; re-export request |
| 15 | Blank `evse_name`; chargers renamed mid-period (incl. owner prefix) | 12 rows; 19 chargers | WARN; names never used as keys |
| 16 | Export `site_id` / `station_id` always blank | 100% | Renamed `source_site_id` / `source_station_id`; sites resolved from the registry |

---


---

## 9. Simulation integrity rules (non-negotiable)

1. Generators are committed, seeded (`SIM_SEED=42`), deterministic; outputs reproducible byte-for-byte.
2. Every simulated record carries `data_origin = "simulated"`; files live only under `data/simulated_client_systems/`.
3. `simulate/SIMULATION_SPEC.md` lists every rule and parameter and marks it **real anchor** or **assumption**.
4. The KPI and all headline metrics are computed **only from real data**. Metrics that touch simulated fields are
   labelled **"illustrative (simulated input)"** in the evidence table.
5. The pipeline validates simulated sources exactly like client data — it never trusts them.

---


---

## 10. Engineering conventions

- Python ≥ 3.11; dependencies: `pandas`, `requests`, `flask`, `pytest` (no heavy frameworks).
- Structure (Class 8 style): `run_pipeline.py` (one command) → `pipeline/{config, logging_utils, extract, validate,
  clean, transform, metrics, save}.py`.
- **Config split:** *where/how it runs* → environment variables (`config/.env.example`: URLs, API key, retries, page
  size, log level, mock-API autostart). *What the business means* → `config/kpi_definitions.json` (thresholds,
  windows, site rules), versioned and echoed into outputs. Never let an env var silently redefine the KPI.
- **Run partitioning:** `--run-date YYYY-MM-DD` (logical date) and `--month YYYY-MM` scope. Raw inputs →
  `data/raw/<source>/run_date=<d>/` (cleared per run). Outputs → `data/processed/run_date=<d>/` written to a temp dir and
  swapped atomically (all files, not just CSV).
- **Validation gate before publish:** each check returns PASS/WARN/FAIL/UNKNOWN with evidence; any FAIL stops the run
  with exit code 2 and publishes nothing new. Unexpected errors → exit 1. Success → 0.
- **Retries:** only on transient conditions (HTTP 429/5xx, timeouts), bounded (`MAX_RETRIES`), exponential backoff,
  honour `Retry-After` / `retry_after_seconds`. Never retry schema/business failures.
- **Logging:** `timestamp | level | stage | message` with counts, source, page, attempt, and whether output was published.
- **Joins:** always report match coverage; aggregate one-to-many before joining to visit/charger grain.
- **Chaos demos** (Class 8 style) via `--chaos {missing_column, duplicate_rows, stale_data, api_outage, bad_checksum}`.
- Tests: `pytest` for visit construction, site resolution, validation rules, and idempotent rerun.
- Timezone: keep UTC throughout.

---


---

## 12. Out of scope / do not

- No ML / delay-prediction / forecasting models. No Airflow, Spark, Kafka, dbt, cloud warehouses.
- No dashboards beyond a simple evidence table (optional static chart is fine).
- Do not commit course PDFs or instructor material (keep them in git-ignored `course/`).
- Do not commit API keys or `.env`.
- Do not name a real operator as the client or attribute performance to named utilities.
- Do not change D1–D5, thresholds, or windows without an approved entry in `docs/decisions_log.md`.

---


---

## 13. Glossary

- **Charger / EVSE / port / connector:** a charger (EVSE) has one or more ports; a port delivers energy to one EV at a
  time; a port may have multiple connector types. Reliability is tracked per port/charger; driver experience per visit.
- **CPMS:** charge-point management system (operator back office; source of session data). **CMMS:** maintenance
  management system (work orders). **NOC:** network operations centre.
- **OCPP:** Open Charge Point Protocol (charger ↔ back office messages, e.g. `StatusNotification`, `StartTransaction`).
- **NEVI / 23 CFR 680.116:** US federal rule; a port is "up" only if online **and successfully dispenses electricity**;
  >97% annual uptime required; excludes utility outages, vehicle-caused failures, scheduled maintenance, vandalism,
  natural disasters, and hours outside operation.
- **EV-ChART:** federal data-reporting format (Module 2 sessions incl. `session_error`; Module 3 uptime; Module 4 outages).
- **AFDC:** Alternative Fuels Data Center station registry (US DOE).
- **FTCS:** first-time charge success. **Troubled success:** succeeded after ≥1 failed attempt. **Unbound attempt:**
  session with no port id. **Silent charger:** ≥99% (inferred) available but first-attempt success < 80%.
- **Point error (UC Davis):** failure while the charger is online — invisible to time-based uptime.

---


---

## 14. Key research sources (full list in `docs/research_sources.md`)

- Gamage, Jenn, Tal (2024), *Novel Methodology to Measure the Reliability of Public DC Fast Charging Stations*, TRR,
  CC-BY-4.0 — 1 kWh screen, 5-min visit window, first-time/troubled/persistent categories.
- ChargeX Consortium (INL/ANL/NREL) — customer-focused KPIs; OCPP interim KPI calculator
  (github.com/chargex-consortium/OCPP-2.0.1-Interim-KPI-Calculator).
- kwwhat (open-source OCPP analytics) — 0.1 kWh success rule; visit models; first-attempt/troubled/failed metrics.
- 23 CFR 680.116 (NEVI uptime); EV-ChART data guidance (driveelectric.gov).
- J.D. Power 2026 EVX Public Charging Study (12% failed visits); Paren Q1/Q2 2026 reliability reports (93.8% national index).
- Rempel et al. (2022/2023) Bay Area DCFC field study (72.5% functional vs 95–98% reported uptime).
