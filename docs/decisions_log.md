# Decisions Log

Every consequential choice in this project, with the options considered, the evidence, and the consequence.
Format per entry: **Decision · Options considered · Evidence · Rationale · Consequences · Status**.
Changing a locked decision requires a new dated entry here — never an unlogged code change.

---

## D1 — Problem statement and headline
**Date:** 2026-09-27 · **Status:** Locked (amended same day after D2/D3 evidence — see C3, C4)

**Decision.** Headline: *"Our fast chargers report 99% uptime — so why do 1 in 6 drivers fail on their first try?"*
Business problem stated at **driver-visit grain** with a recent-quarter baseline.

**Options considered.**
| Option | Headline | Verdict |
|---|---|---|
| A | "…why does 1 in 5 charging attempts deliver no energy?" | True (attempt success 79.5%) but at *attempt* grain while the KPI is at *visit* grain → mixed-grain inconsistency |
| **B** | **"…why do 1 in 6 drivers fail on their first try?"** | **Chosen.** Same grain as the KPI (FTCS 83.8% ⇒ 16.2% first-try failure ≈ 1 in 6) |
| C | Keep Assignment 1's "a third of drivers can't charge" | Rejected. National 2026 failure rate is 12% (J.D. Power); only the worst site approaches it (69.2%) |

**Evidence.** J.D. Power 2026 EVX: non-charging visits at an all-time low of 12%. Paren Q2 2026: national reliability
index 93.8%, laggard states ~78%. Our data: FTCS 83.8% (13 months), 86.0% (recent quarter), worst site 69.2%.

**Amended target (after C3/C4).** Lift FTCS **86.0% → ≥ 87% in 6 weeks** by bringing the 5 lagging sites to the network
median, **and** close the diagnostic gap (every failed attempt carries a port and a cause) so a ≥ 90% target can be set
credibly next quarter. The original "≥ 89% by repairing the 5 worst ports" target was withdrawn (C4).

**Amendment 2026-09-27 (after independent review).** Headline changed from "1 in 6" to **"1 in 7"**: the headline
must use the same period as the baseline and target (baseline-quarter FTCS 86.03% ⇒ 14.0% ≈ 1 in 7). The 13-month
figure (83.87%) stays as context. Supporting attempt-grain evidence is labelled as such ("1 in 5 attempts").

**Consequences.** The "99% uptime" is the *client's claim* to be tested (FlashEats "56%" pattern), not our finding.
All numbers depend on D2/D3 definitions. 6-week window kept for continuity with Assignment 1.

---

## D2 — What counts as a failed attempt
**Date:** 2026-09-27 · **Status:** Locked

**Decision.** Failed attempt = `energy_kwh < 1.0`. Attempts with blank `port_id` on DC chargers ("unbound") are **kept**
as failed attempts attributed to their charger's site. FTCS at `> 0 kWh` is always reported as a sensitivity line.

**Options considered.**
| Threshold | Source | FTCS (13 mo) |
|---|---|---|
| > 0 kWh | EV-ChART: unsuccessful session = no energy dispensed (energy reported as "none") | 84.8% |
| ≥ 0.1 kWh | kwwhat (open-source OCPP analytics): meaningful transfer > 0.1 kWh | 84.4% |
| ≥ 0.5 kWh | Initial ad-hoc choice (no source) | — (superseded) |
| **≥ 1.0 kWh** | **UC Davis, Gamage et al. 2024 (peer-reviewed, TRR): events > 1 kWh are successful; 1 kWh ≈ 3–4 miles** | **83.9%** |

**Evidence.** DC energy distribution is bimodal: 6,899 attempts at exactly 0 kWh; only 474 in (0, 1); 27,777 above 5 kWh.
93.6% of sub-1 kWh attempts are exactly zero → every threshold option lands within 0.9 pts.
Blank-port rows: 2,187 (4.7% of all sessions), **all on DC chargers, 99.9% zero-energy**, median 2 min.

**Rationale.** Most defensible published source; represents "meaningful charge" from the driver's view; low sensitivity.
Unbound attempts are failed fast-charge attempts that died before the port was recorded — dropping them as "bad keys"
would remove 29.7% of all failures and inflate FTCS by ~4 pts.

**Consequences.** DC classification must be at **charger** level (failed attempts have peak power 0). Zero energy is an
*inferred* failure — cause (charger / vehicle / driver / payment) is unknown. Rows with energy > 0 but peak power 0
(1,671 DC) are flagged WARN, not reclassified.

---

## D3 — What counts as a driver visit
**Date:** 2026-09-27 · **Status:** Locked

**Decision.** A visit = consecutive attempts at the **same physical site**, where each attempt starts within **[−2, +5]
minutes** of the previous attempt's end. Site = normalised registry address (`street_address|city`) via the resolution
chain port_id→AFDC posts, else name match, else unresolved. Visit succeeds if **any** attempt succeeds.

**Options considered.**
| Rule | Source | FTCS | Failed visits |
|---|---|---|---|
| Same port, 2 min | kwwhat rule for unauthenticated drivers | 82.4% | 11.3% |
| Same site, 2 min | — | 83.2% | 7.5% |
| **Same site, 5 min** | **UC Davis (validated with user IDs); our gap analysis** | **83.9%** | **5.8%** |
| Same site, 10 min | — | 84.1% | 5.1% |
| Same site, 15 min | Initial ad-hoc choice | 84.1% | 4.9% |

**Evidence.** Fail-vs-success gap ratio (gap to the next attempt at the same site, after a failed vs a successful
attempt): 13.8× in (0,1] min, 5.3× (1,2], 2.1× (2,3], 1.3× (3,5], **0.6× (5,7.5]**, 0.4× (7.5,10], ≤0.2× beyond.
After a success the next session is almost always a new driver; excess short gaps after failures are retries. The curves
cross at ~5 min — independently matching UC Davis. 42.3% of multi-attempt visits switch port, so port-level grouping
splits real retries into fake failed visits.

**Rationale.** Empirically supported on our own data *and* in peer-reviewed work; site-level captures port switching.
We have no driver IDs, so this is the UC Davis "Variation 2" approximation.

**Amendment 2026-09-27.** (1) The 2-minute row was mislabelled: 83.2% / 7.6% was *site*-level; true port-level is
82.4% / 11.3% (C8). (2) Ordering and gap are now fully specified: sort by (site, start, end, session_id); the gap is
measured to the **previous row's** end at the same site (a visit-max-end rule would wrongly split retries made while
another driver was still charging). (3) Tested refinement "a successful attempt closes the visit" moved FTCS by only
0.1 pt, so the rule stands. Figures below use the corrected 40 sites (D7).

**Consequences.** FTCS robust (82.4–84.8% across rules); *failed-visit rate* is definition-sensitive (4.9–11.3%) → always
report its sensitivity. Two different drivers arriving within 5 min at a busy site can be merged (known limitation).

**Amendment 2026-09-27 (D9).** The "switch port" figure above (42.3%; 43.5% after D7) is the share of multi-attempt visits
whose attempts span more than one port key — exactly the visits port-level grouping would cut in two, so it remains the
reason port-level grouping is rejected. It is *not* the share of drivers who moved: every DC charger exposes one port id,
and a port-less `UNBOUND@C` attempt followed by charger C is the same place. **27.2% of retry visits move to another
charger.**

---

## D4 — Simulated client systems
**Date:** 2026-09-27 · **Status:** Locked

**Decision.** Simulate only what no public source records, anchor every simulated event to a real signal, never let
simulated data touch the KPI. Two sources:
- **S1 Charger status feed** (mock REST API; OCPP 1.6-style StatusNotifications) derived from real sessions + real
  inferred outage windows. Invented: fault codes; counted-vs-excluded outage categories (reproduces the NOC's "99%").
- **S2 Maintenance work orders** (SQLite) — one corrective order per real inferred outage window + quarterly PM.
  Invented: detection lag, trigger, action, resolution code. Repair effect measured on real sessions.
- **No simulated support tickets** — driver interactions are real (retries, port switches).
- `client_brief.json` holds the leadership claim and conflicting stakeholder definitions.

**Options considered.** (a) Fully synthetic pack like FlashEats — rejected (weaker than real data). (b) Real-only —
rejected (no public status or maintenance data; cannot test the uptime claim or model interventions).
(c) **Hybrid, anchored** — chosen.

**Evidence (anchor).** Statistical outage inference on real sessions at 35 multi-charger sites (80 chargers): run of *k*
consecutive site successes on other chargers flagged when (1−p)^k < 0.001, bounded to commissioned life → **44 windows**,
fleet availability **97.05%**, **14 silent chargers** (≥99% available, first-attempt success < 80%), corr(availability,
FTCS) = 0.59. A first, naive idle-gap heuristic (≥6 h silent while siblings charge) was **rejected**: it implied 75%
availability because idle ≠ down at low-utilisation sites.

**Integrity rules.** Seeded deterministic generators; `data_origin = "simulated"` on every record; `SIMULATION_SPEC.md`
marks real-anchor vs assumption; simulated-input metrics labelled "illustrative"; pipeline validates simulated sources.

**Consequences.** Three retrieval modes: files (R1), REST API (R2 real + S1 simulated), SQL (S2). The finding that
silent chargers receive no corrective work orders follows from real inference + the *assumed* alarm-driven dispatch
process — must be verified against a real CMMS (listed as an assumption).

---

## D5 — Client name and repository layout
**Date:** 2026-09-27 · **Status:** Locked

**Decision.** Fictional persona **"Voltra Charging Network"** with an explicit Data Provenance section; site codes
S01–S43 in outputs with a lookup to public addresses; Class-8-style layout (`run_pipeline.py`, `pipeline/`, `simulate/`,
`data/`, `docs/`, `notebooks/`, `tests/`).

**Options considered.** Name the real network — rejected: the dataset does not identify itself as any specific network
(site names suggest TVA Fast Charge Network partners, but that is our inference), so attributing failure rates to named
public utilities would overclaim.

---

## D6 — Run date, freshness and baseline
**Date:** 2026-09-27 · **Status:** Locked

**Decision.** The pipeline processes a *reporting month* = the month before the logical `--run-date` (default
2025-02-01). **Freshness** PASSES if the latest session starts within **2 days** of the reporting month's end (the
known one-day export gap needs ~1 day of tolerance); otherwise FAIL. Age versus today is a WARN ("historical backfill"),
never a FAIL. The **baseline** is the last three monthly exports in the data, anchored to the end of the data, not the
run date.

**Why.** The data is a historical export (ends Jan 2025). Judging freshness against the wall clock would fail every run
and teach nothing; judging it against the logical date keeps the check meaningful and demonstrable (`--chaos stale_data`).

## D7 — Physical sites by distance, not address text
**Date:** 2026-09-27 · **Status:** Locked

**Decision.** Chargers whose registry coordinates are within **150 m** (single linkage) form one site.

**Evidence.** Address text split three real sites into six ("10772 US-51" vs "10772 U.S. 51", "114 SW ATLANTIC ST" vs
"… ST.", "110 COLLEGE ST W" vs "… STREET WEST"). Within-site distances are ≤ 33 m; the nearest separate site is 17 km
away, so any threshold between those gives the same **40 sites** (not 43).


## D8 — Validation hardening after independent review (definitions v1.2.0)
**Date:** 2026-09-27 · **Status:** Locked

**Decision.** Five rules added to the validation gate:
1. **A changed file layout is a FAIL.** Every header row in every monthly file must equal the first file's header.
2. **Missing energy is a FAIL; blank peak power is a counted WARN.** Values that do not parse are left missing, never
   imputed.
3. **Integrity checks test content, not column names.** Every attempt must be a real R1 `session_id`; KPI inputs may only
   hold R1 columns plus an allowlist of derived columns; every attempt sits in exactly one visit.
4. **Gate tolerances are configuration** (`validation_tolerances` in `config/kpi_definitions.json`), not literals in code.
5. **Gates speak on success.** Each gate logs its PASS/WARN counts and one line per WARN/UNKNOWN.

**Options considered.**
| Problem | Options | Chosen | Why |
|---|---|---|---|
| A later file's header is reordered or renamed | (a) parse with the first header (old behaviour) · (b) map columns by name per file · (c) FAIL | **(c)** | (a) silently swapped energy and peak power in a test, with zero warnings. (b) is safe for a pure reorder but not for a rename, and still hides that the export contract changed. A layout change is a conversation with the CPMS vendor, not a parsing problem. |
| 2,549 rows have blank `peak_power_kw` | impute (median or 0) · drop the rows · keep missing and count | **keep missing, WARN** | Imputing invents physics (0 kW would also trip the energy-without-power flag). Dropping would delete 1,952 port-less failed attempts — the D2 trap again, inflating FTCS. Peak power is only used as max-per-port for DC classification, where a blank is simply ignored. |
| `energy_kwh` does not parse | coerce to NaN (old) · treat as 0 · FAIL | **FAIL, zero tolerance** | `NaN >= 1 kWh` is False, so a missing energy value would silently become a failed attempt and lower the KPI. The KPI input gets zero tolerance. |

**Evidence.** Review F1: a reordered header in a later file swapped energy and peak power with no warning. All 52 real
header rows are identical, so no published number was affected. F2: the run manifest recorded 2,549 unparseable numbers
that no check read. F15: `visit_integrity` compared `value_counts().sum()` with `len()` — always true. F10: a clean run
printed no gate lines at all.

**Consequences.** No KPI number changes (86.03% / 83.87%). Validation summary 16/13/1 → 17/14/1. A future export with a
changed layout or missing energy stops the run with exit 2 and a message naming the file and column.


## D9 — Measurement corrections after independent review (definitions v1.3.0)
**Date:** 2026-09-27 · **Status:** Locked

**Decision.**
1. **Driver switching is measured by charger, among real retries.** Retry visit = first attempt failed and ≥ 2 attempts;
   a switch = the attempts span ≥ 2 chargers → **27.2%** of retry visits (previously reported as "43.5% switch port").
2. **The rejected D2 alternative is computed on every run**, not quoted from exploration: sensitivity row
   *drop port-less attempts (rejected, D2)* and `metrics.json → judgement_call`. Dropping would make FTCS read
   **90.33%** in the baseline quarter (+4.30 pts) and 88.92% over 13 months (+5.05).
3. **Inferred outages still open when the data ends are listed, never counted:** 2 chargers at S29 had no session at all
   for ~25 days at the end of January while their site-mates logged 74 and 77 successes.
4. **"Repair effect" is relabelled** as charger first-attempt success before → after a corrective work order, with the
   caveat that there is no control group.

**Options considered.**
| Question | Options | Chosen | Why |
|---|---|---|---|
| How often do retrying drivers move? | distinct port keys over all multi-attempt visits (old, 43.5%) · distinct identified ports · **distinct chargers over retry visits** | **distinct chargers, retry visits (27.2%)** | Every DC charger exposes exactly one port id (88/88), so port = charger; `UNBOUND@C → C` is the same place; 23.9% of multi-attempt visits succeeded first time, so they are not retries. 43.5% still answers a different question (how many visits port-level grouping would split) and stays as D3's rationale. |
| How to present the judgement call | quote "~4 pts" (old) · **compute every run** | **compute** | A number no code produces cannot be checked by a grader or protected by a test. |
| A run still open at the data end | ignore (old) · count as downtime up to the data end · **list for verification** | **list, WARN** | Counting would lower availability for what may be a decommissioning; ignoring hides the freshest operational signal in the reporting month. A site visit settles it cheaply. |
| Repair-effect label | "median FTCS before → after" (old) · **charger first-attempt success + caveat** · drop the metric | **relabel** | FTCS is a visit-grain network KPI; this is a charger-level measure. With simulated timing and no control group it is illustrative only. |

**Evidence.** Review F3 (charger switch 32.9% of multi-attempt visits, 27.2% of retry visits; port-key switch 43.5%),
F12, F5 (chargers 13664401 and 13164881: last success 5–6 Jan 2025; 74 / 77 site successes since, 31 / 45 needed), F14.

**Consequences.** No KPI number changes. The crew decision gains one verification item (S29). Validation summary
17/14/1 → 17/15/1 (33 checks). The judgement call now has its own block in `metrics.json` that the demo can show.

---

## Corrections log (self-corrections made during research — kept visible on purpose)

| ID | What was wrong | How it was caught | Effect |
|---|---|---|---|
| C1 | Visits grouped by `evse_name` prefix, assumed to be a site — it is the **owning organisation** (`BRIGHTRIDGE EV / BR-JC LIBRARY` vs `… / BR-JONESBOROUGH`) | Checking prefix semantics while defining "site" for D3 | "39 sites" were 39 orgs; true count 43 sites |
| C2 | Blank `port_id` rows were first lumped into one pseudo-port, then wrongly excluded as non-DC | Site-count mismatch (58 vs 43) → traced to blank keys → profiled the rows | Correct treatment = unbound failed attempts on DC chargers (D2) |
| C3 | Headline stats from Assignment 1 ("a third can't charge") outdated | 2026 research (J.D. Power 12%, Paren 93.8%) | Headline reframed (D1) |
| C4 | Claim "9 ports cause 52% of failures" and "fix 5 worst ports → 89%" | Artefact of C1/C2; with correct population, worst 10 chargers only lift FTCS 83.8% → 85.1%; failures are fleet-wide | Concentration claim and 89% target withdrawn; target amended (D1) |
| C5 | 15-min visit window chosen ad hoc | Fail-vs-success gap analysis + UC Davis evidence | Window set to 5 min (D3) |
| C6 | Registry "Available" status cited as evidence for 2024 | Registry is a 2026 snapshot | Removed from problem statement; recorded as temporal limitation |
| C7 | Sites keyed on address text → same site counted twice when spelled differently | Independent review asked how addresses are normalised; checking found 3 spelling variants | 43 → 40 sites; distance clustering (D7); FTCS 83.8% → 83.9% |
| C8 | D3 table labelled a site-level 2-min result as port-level | Independent review | Relabelled; port-level 2-min is 82.4% / 11.3% |
| C9 | Headline "1 in 6" used the 13-month figure while the baseline is the recent quarter | Independent review | Headline "1 in 7" (D1 amendment) |
| C10 | Each monthly export is missing its last calendar day (UTC) | Day-coverage check while defining "complete month" | WARN check + limitation + re-export request |
| C11 | Later files' header rows were counted but never compared with the first — a reordered export would be parsed into the wrong columns silently | Independent review F1: a scratch test swapped energy and peak power with zero warnings | FAIL check `sessions.header_consistency` (D8) |
| C12 | `to_numeric(errors="coerce")` turned 2,549 blank peak-power values into NaN; the count was stored but never checked or documented, and a blank energy value would have become a silent failed attempt | Review F2 (run manifest) | `sessions.numeric_parse`: missing energy FAIL, blank peak power WARN (D8) |
| C13 | The whitespace strip keyed on `dtype == object`, which pandas 3 no longer uses for text, so it silently did nothing | Review F9 (no padded cells in this data, so no number moved) | Strip keyed on string dtypes; `pandas>=2.0,<4` pinned |
| C14 | "43.5% of retry visits switch port" counted `UNBOUND@C → C` as a switch and included first-time successes, although every DC charger has one port id | Review F3 | Measured by charger over retry visits: 27.2% (D9) |
| C15 | Inferred outages still open at the data end were silently ignored — two S29 chargers dark for ~25 days at the end of the reporting month | Review F5 | Listed for on-site verification (WARN), never counted as downtime (D9) |
| C16 | The judgement call's "~4 pts" was quoted from exploration; no code produced it | Review F12 | Computed every run: 90.33% (+4.30) quarter · 88.92% (+5.05) 13 months (D9) |
| C17 | "Repair effect: median FTCS" was a charger-level measure with no control group | Review F14 | Relabelled with caveat (D9) |
