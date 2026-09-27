# Review Checklist — how to review this project like the grader (and a senior FDE)

Use this for every review. A review is only useful if every finding is **specific, evidenced and tied to the rubric**.

---

## A. Severity scale

| Severity | Meaning | Examples |
|---|---|---|
| **BLOCKER** | Breaks a rubric requirement, corrupts the KPI, or the pipeline cannot run | Silent row drop that moves FTCS; simulated data in the KPI; `run_pipeline.py` crashes; retrieval not proven complete; secrets committed |
| **MAJOR** | Weakens defensibility or a graded pillar; a failure path is untested | Join without coverage report; claim in docs not reproduced by code; missing required README section; retry on non-transient error |
| **MINOR** | Clarity, naming, small inconsistencies that a grader might notice | Doc number differs by rounding; unclear log message; missing docstring on a key function |
| **NIT** | Style only | Formatting, wording |

Verdict per review: **READY** (no BLOCKER/MAJOR) · **READY WITH FIXES** (MAJORs with clear fixes) · **NOT READY** (any BLOCKER).

---

## B. Rubric → what the grader looks for (5 pillars × 20%)

### Pillar 1 — Source reasoning (Class 4)
- [ ] Starts from **business questions**, not datasets: question → information need → field → source → owner.
- [ ] Every source has: **owner, grain (one row = ?), format, freshness/update frequency, access method, trust level**.
- [ ] **System-of-record decision per critical fact**, with reasoning on ownership / freshness / replication / semantics
      (e.g., why the AFDC registry is *relevant but not authoritative* for availability).
- [ ] **Minimum required-fields list** (not "ingest everything").
- [ ] **Gaps named explicitly** and treated as product/instrumentation signals (blank `session_error`, port-less attempts,
      no driver ID, no OCPP logs, no cause codes, registry time-misalignment).
- [ ] Source map artefact exists in the repo (diagram or table).

### Pillar 2 — Retrieval (Class 5)
- [ ] **≥ 2 retrieval modes actually used in code** (here: files, REST API, SQL).
- [ ] **Completeness proven**, not assumed: checksums/sizes for files; `total_results`/`total_records` for APIs; row counts
      for SQL — and the run **fails** if incomplete.
- [ ] **Raw inputs preserved** unmodified before any transformation, partitioned per run.
- [ ] Pagination handled; **bounded retries** on 429/5xx/timeouts only; clear failure on anything else.
- [ ] Handles empty results, timeouts, invalid/malformed responses (e.g., glued headers) explicitly.

### Pillar 3 — Validation (Class 6)
- [ ] Data profiled (types, ranges, distributions, nulls, duplicates, categories, timestamps).
- [ ] **Validation contract**: business assumption → data expectation → executable check → severity → action.
- [ ] Checks cover **technical** (keys, chronology, ranges), **semantic** (what does blank `session_error` mean? what is
      "up"?), and **organisational** (who owns the KPI definition — stakeholder conflict in `client_brief.json`).
- [ ] Output is a **gate decision** (PASS/WARN/FAIL/UNKNOWN) with evidence, not just a cleaned dataframe.
- [ ] Assumptions and limitations **recorded, not silently fixed**. Every fix is counted and logged.

### Pillar 4 — Workflow + metrics (Class 7)
- [ ] Entities, events/states, interactions (driver retries/port switches), interventions (work orders), outcomes (visit result).
- [ ] Simple relational/event model with keys and grain documented; diagram in repo.
- [ ] One-to-many tables aggregated **before** joining to outcome grain (no row inflation).
- [ ] **3–5 metrics**, each with formula, grain, why it matters, and **link to the KPI**; at least one outcome, one
      interaction, one intervention metric.
- [ ] Each finding states **what it tells the business and what it does NOT prove**.

### Pillar 5 — Pipeline dependability (Class 8)
- [ ] One command runs the full flow from raw inputs to metric outputs.
- [ ] Stages isolated in small functions; config outside core logic; business rules versioned.
- [ ] Required-column, null, duplicate, freshness checks run **every** time; FAIL stops publication (exit 2).
- [ ] **Idempotent rerun** (same run date → same outputs, no duplication); atomic publish of the whole partition.
- [ ] Useful logs (stage, source, counts, page, attempt, published or not) and useful failure messages.
- [ ] Failure demos (chaos flags) actually produce the expected behaviour.

### Submission package
- [ ] README: problem, users/stakeholders, project KPI, source overview, setup/run, **decision the output supports**.
- [ ] Source map + workflow/data-model diagram in repo.
- [ ] Evidence table with 3–5 metrics + **Known / Unknown / Assumption / Limitation** section.
- [ ] Demo-ready: one clearly explained FDE judgement call (candidate: keeping port-less attempts as failures).

---

## C. Definition of Done per phase

**Phase 1 — Decisions & context layer** (documentation only — check internal consistency; do NOT rerun data work)
- `docs/decisions_log.md` has every decision with options, evidence, rationale; corrections logged.
- `config/kpi_definitions.json` agrees with `docs/decisions_log.md` and `CLAUDE.md` (thresholds, windows, site rules,
  KPI formula, baseline, target, freshness, lagging-site rule).
- No contradictions between `CLAUDE.md`, the decisions log, the config and `docs/agent/reference_numbers.md`.

**Phase 2 — Source reasoning**
- `docs/source_map.md`: business questions → info → fields → sources → owner → grain → freshness → trust → gaps.
- Required-fields list (minimum per source) with justification.
- System-of-record table for: session outcome, energy delivered, port identity, site identity, charger availability,
  repair events, KPI definition — each with reasoning.
- Diagram of sources and how they connect (mermaid in `docs/source_map.md`; pipeline flow in `README.md` §6).
- Every number quoted matches `docs/agent/reference_numbers.md`.

**Phase 3 — Retrieval**
- R1: downloads 13 files; verifies size + git-blob SHA-1 against the HF tree API; preserves raw bytes; fails on mismatch.
- R2: AFDC call with `AFDC_API_KEY`; verifies `total_results`; saves raw JSON; handles 429 with backoff; never uses `developer.nrel.gov`.
- S1: generator (seeded) + mock API (pagination, month filter, deterministic 500/429); client proves completeness.
- S2: generator (seeded) writes SQLite; extraction via SQL; row counts checked.
- Raw partitions per run date; retrieval manifest (source, files/pages, counts, checksums, timestamps).
- `simulate/SIMULATION_SPEC.md` marks each rule **real anchor** vs **assumption**.

**Phase 4 — Validation**
- `docs/validation_contract.md` with assumption → expectation → check → severity → action for every defect in project_context §7.
- Executable checks returning PASS/WARN/FAIL/UNKNOWN with evidence; `validation_report.json` per run.
- Glued-header repair counted (39); blank `port_id` kept as unbound (2,187); anomalies flagged not reclassified.

**Phase 5 — Model & metrics**
- Tables: `sites`, `chargers`, `ports`, `attempts`, `visits` (+ `status_events`, `work_orders` illustrative).
- Keys/grain documented; diagram; joins report coverage; reference numbers reproduced exactly.
- 3–5 metrics with formula, grain, rationale, KPI link, and "does NOT prove" statements; sensitivity lines.

**Phase 6 — Pipeline hardening**
- `python run_pipeline.py --run-date …` end-to-end; exit codes 0/1/2; idempotent rerun proven; atomic partition swap.
- Chaos flags produce expected outcomes; `pytest` passes; Gate 2 readiness doc completed.

**Phase 7 — Evidence & story**
- Evidence table (3–5 metrics) generated by the pipeline, not typed by hand; K/U/A/L section; full README; demo script.

---

## D. Red flags to grep for in code

- `dropna(`, `drop_duplicates(`, `fillna(`, `.replace(`, boolean filtering that removes rows — **without a count + log line**.
- Filtering blank `port_id` rows, or classifying DC per port (loses unbound failures).
- Using `evse_name.split("/")[0]` as a site.
- `developer.nrel.gov` anywhere. Hard-coded API keys. Absolute local paths.
- `except Exception: pass` or broad excepts that continue silently.
- Retrying 4xx (except 429); unbounded `while True` retry loops; no timeout on `requests`.
- Selecting columns with `[c for c in cols if c in df.columns]` (silent column skip — the Class 8 reference bug).
- Env vars that change thresholds/windows (must come from `config/kpi_definitions.json`).
- Simulated columns (`data_origin == "simulated"`) flowing into FTCS or headline metrics.
- Non-atomic writes of outputs; appending to outputs on rerun; raw partitions not cleared.
- Merges without `validate=` / coverage reporting; many-to-one joins done before aggregation.
- Naive datetimes / timezone mixing. Numbers in docs that no code produces.
- Causal language ("X causes failures") without evidence; claims about named real operators.

---

## E. How to verify (commands)
```bash
git log --oneline --decorate -n 10         # what phase is this?
git diff phase-<N-1>..HEAD --stat          # what changed in this phase
python run_pipeline.py --offline               # (logical run date defaults to 2025-02-01)
pytest -q                                   # (when tests exist)
```
Compare outputs against `docs/agent/reference_numbers.md` (exact counts, ±0.1 pp rates).

---

## F. Review report template (write to `reviews/phase-<N>-review.md`)

```markdown
# Phase <N> review — <date>
**Verdict:** READY | READY WITH FIXES | NOT READY
**Scope reviewed:** <files / commits>   **Commands run:** <list with exit codes>

## Rubric impact
| Pillar | Status (strong / adequate / at risk) | Why |
|---|---|---|

## Definition-of-Done check (phase <N>)
| Item | Met? | Evidence |

## Reference numbers
| Quantity | Expected | Got | OK? |

## Findings
| ID | Severity | File:line | Finding | Why it matters (pillar) | Evidence | Suggested fix |

## Questions for the design session (do not decide these yourself)
-

## What is genuinely strong (keep it)
-
```

---

## G. Grader's questions — can the repo answer each in one click?
1. What business decision does this output support, and who makes it?
2. Where does the truth live for "did the driver get a charge?" — and why that source?
3. How do you know you retrieved *everything*?
4. What did you refuse to silently fix, and where is that recorded?
5. What is one row in each table? What joins could inflate rows?
6. How do the 3–5 metrics connect to the KPI?
7. What happens if the API fails, a column disappears, or the data is stale? Show me.
8. What can this data NOT tell you?
9. What was your most important judgement call, and what evidence supports it?
