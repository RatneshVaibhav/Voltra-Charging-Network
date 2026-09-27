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
