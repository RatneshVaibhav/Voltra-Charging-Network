# Verify numbers — 2026-09-27

**Mode:** independent. The script is my own (`.scratch/verify_numbers.py`, git-ignored, plus diagnostics
`.scratch/diag*.py`). It imports no repo code; it implements the text definitions in `CLAUDE.md` §5 and
`docs/agent/project_context.md` §5–7, and asserts that `config/kpi_definitions.json` holds the same thresholds.
**Scope:** all 19 rows of `docs/agent/reference_numbers.md` (`CLAUDE.md` §9 says "22 regression numbers"; the table has
19 rows), plus the other figures quoted in `CLAUDE.md`, `docs/decisions_log.md` and `project_context.md` §7.
**Verdict:** **READY WITH FIXES.** 17 of 19 reference rows reproduce within tolerance. Lagging sites reproduce only under an
unstated tie-break. The outage inference reproduces only under 1 of 9 plausible readings. The headline KPI is robust.
There are 3 MAJOR findings, all fixable in docs and config.

## Retrieval (completeness proof)
| Source | Check | Result |
|---|---|---|
| R1 HF `raw_charging_stations/` | 13 files; byte size == tree API `size` and git-blob SHA-1 == `oid` (no LFS) | **13/13 OK** |
| R2 AFDC `developer.nlr.gov` (DEMO_KEY, 1 request) | `len(fuel_stations) == total_results` | **4,593 == 4,593 OK** (`x-ratelimit-limit: 10`) |

## Reference numbers
Tolerance: counts exact, rates ±0.1 pp.

| Quantity | Expected | Got | Δ | OK |
|---|---|---|---|---|
| Session rows (13 files) | 46,575 | 46,575 (46,575 distinct `session_id`) | 0 | ✅ |
| Glued-header defects | 39 | 39 (1–5 per file); 39 repeated header rows dropped; 0 malformed rows | 0 | ✅ |
| Date range (UTC) | 2024-01-01 00:17 → 2025-01-31 03:25 | first start 2024-01-01 00:17:12 → last **end** 2025-01-31 03:25:06 | — | ✅ (last *start* is 2025-01-30 23:45) |
| Distinct chargers / non-blank ports | 140 / 200 | 140 / 200 | 0 | ✅ |
| DC chargers / DC identified ports / sites | 88 / 88 / 43 | 88 / 88 / 43 | 0 | ✅ as defined — but see **F1** (43 keys = 40 physical sites) |
| DC attempts / unbound | 35,996 / 2,187 | 35,996 / 2,187 | 0 | ✅ |
| Energy buckets =0 / (0,0.1] / (0.1,1) / [1,5] / >5 | 6,899 / 215 / 259 / 846 / 27,777 | 6,899 / 215 / 259 / 846 / 27,777 | 0 | ✅ |
| Visits (D2 + D3) | 29,101 | 29,101 | 0 | ✅ — tie-break dependent, see **F3** |
| Attempt success | 79.5% | 79.52% | +0.02 | ✅ |
| **FTCS (13 months)** | **83.8%** | **83.83%** | +0.03 | ✅ |
| Troubled / failed visits / attempts per visit | 10.3% / 5.9% / 1.24 | 10.26% / 5.91% / 1.237 | ≤0.04 | ✅ |
| Multi-attempt visits / switched port | 15.9% / 42.3% | 15.90% / 42.33% | ≤0.03 | ✅ |
| Unbound share of failed attempts | 29.7% | 29.64% (2,185 / 7,373) | −0.06 | ✅ within tolerance — see **F7** |
| Recent quarter: visits / FTCS / failed / attempt success | 9,989 / 86.0% / 4.8% / 82.0% | 9,989 / 86.02% / 4.77% / 81.97% | ≤0.03 | ✅ |
| Sensitivity FTCS >0 / ≥0.1 / 2-min / 10-min / 15-min | 84.7 / 84.4 / 83.2 / 84.0 / 84.1 | 84.73 / 84.35 / 83.16 / 84.04 / 84.06 | ≤0.05 | ✅ (all at site grain — see **F2**) |
| Monthly FTCS Jan 2024 → Jan 2025 | 77.7% → 86.4% | 77.69% → 86.46% | +0.06 | ✅ within tolerance (86.46 rounds to 86.5) |
| Worst site (≥200 visits, 13 months) | 69.2% (487) | 69.20% (487) | 0 | ✅ |
| 5 lagging sites / median / lifted network | 75.3, **76.8**, 78.5, 79.9, 81.3 / 86.3 / 86.0 → 87.0 | 75.32, **77.21**, 78.47, 79.90, 81.33 / 86.34 / 86.02 → 87.00 | **+0.41** on site #2 | ❌ with a deterministic tie-break; ✅ only with input-row order — **F3** |
| Outage inference: windows / fleet availability / silent / corr | 44 / 97.05% / 14 / 0.59 | 44 / 96.77–97.20% / 14 / 0.577–0.588 | avail. −0.28…+0.15 | ⚠️ within tolerance under 1 of 9 readings — **F4** |

## Other quoted figures (CLAUDE.md, decisions_log, project_context §7)
All ✅ unless marked:
- **`session_error`:** non-blank on 0 of 46,575 rows.
- **Blank `station_id` / `site_id`:** 100% of rows. The only provider is ChargePoint Network.
- **Blank `port_id`:** 2,187 rows (4.70%). All are on DC chargers, 99.86% are zero energy, and the median duration is 2.0 min.
- **Energy > 0 with peak 0:** 1,766 rows overall, 1,671 on DC.
- **Sessions > 24 h:** 89 overall, 4 on DC. Overlapping sessions on the same DC port: 23.
- **Site resolution:** 86 chargers via posts (86 AFDC records), 2 via fuzzy match (full `evse_name` scores 0.95), 0 unresolved.
  No charger's ports map to conflicting addresses.
- **Site mix:** 35 multi-charger sites (80 chargers) and 8 single-charger sites. Correct as defined; see F1.
- **D2 table:** 84.7 / 84.4 / 83.8. **D3 table:** site 10 min 84.0% / 5.3%; site 15 min 84.1% / 5.0%.
- **Energy distribution:** 474 attempts in (0, 1) kWh; 93.6% of sub-1 kWh attempts are exactly 0.
- ❌ **D3 "Same port, 2 min: 83.2% / 7.6%":** see **F2**.
- ⚠️ **"Dropping unbound inflates FTCS ~4 pts":** see **F5**.
- ⚠️ **"42 of 88 commissioned mid-window, 3 stopped reporting":** see **F6**.

## Findings
| ID | Severity | Where | Finding | Evidence | Suggested fix (for the design session) |
|---|---|---|---|---|---|
| F1 | **MAJOR** | `CLAUDE.md` §3/§5.4, D3, C1, `domain_primer.md` §1, D4 anchor | **The 43 site keys are 40 physical sites.** Three pairs of AFDC records sit 2–6 m apart but have different address strings, so each pair is split into two single-charger "sites": Tullahoma `114 SW ATLANTIC ST` vs `…ST.`; Atoka `10772 US-51` vs `10772 U.S. 51`; Fayetteville `110 COLLEGE STREET WEST` vs `110 COLLEGE ST W`. Retries across the two chargers are currently counted as separate visits. Example: Atoka has 368 visits at 79.1%; merged it has 343 visits at 80.5%. | With the 3 pairs merged: 40 sites; 29,036 visits; FTCS 83.87% (was 83.83%); failed visits 5.75% (was 5.91%); recent FTCS 86.03% (unchanged); the same 5 lagging sites, lifted to 87.0% (unchanged); multi-charger sites 38 with 86 chargers (was 35 with 80); single-charger sites 2 (was 8); outage windows **47** (was 44); silent chargers **15** (was 14); corr 0.54–0.55 (was 0.59); failed-visit sensitivity range **4.9–7.5%** (was 5.0–7.6%). Punctuation-only normalisation gives 41 sites; the Fayetteville pair also needs abbreviation handling or clustering by coordinates. | Decide the site-key rule: representation-only normalisation (→ 41), or cluster by AFDC coordinates with the address as a label (→ 40). Log it as correction **C7** with a config version bump, then regenerate `reference_numbers.md`. The headline KPI barely moves, which is itself good evidence of robustness for the demo. |
| F2 | **MAJOR** | `docs/decisions_log.md` D3 options table, row 1 | The row labelled **"Same port, 2 min (kwwhat)" = 83.2% / 7.6%** is actually **same *site*, 2 min**; I reproduced 83.16% / 7.62% at site grain. True same-port grouping gives **82.37% / 11.33%** at 2 min and 82.78% / 10.48% at 5 min. D3's conclusion stands, and is stronger: port grouping nearly doubles failed visits. This also settles the config question from the context review: `sensitivity_max_gap_minutes: [2, 10]` at site grain matches the reference table. | `.scratch/verify_results.json` → `sensitivity.site_2min`, `port_2min`, `port_5min` | Relabel the row as "Same site, 2 min" and add a real "Same port, 2 min: 82.4% / 11.3%" row. Check any other doc that says "failed-visit rate 5.0–7.6%" implies the kwwhat rule is in range. |
| F3 | **MAJOR** | `config/kpi_definitions.json` `visit`; `reference_numbers.md` | **No tie-break is defined for attempts at the same site that start in the same second.** There are 4 such pairs (8 rows): Starkville, Columbus, Clarksville and Bristol. The reference numbers reproduce only with a *stable* sort on (site, start) over files loaded alphabetically (`Se_01_2024, Se_01_2025, Se_02_2024…`). A deterministic tie-break on (end, session_id) gives Starkville **77.21%**, not 76.8%. A success-first order gives **29,100** visits, not 29,101. Network FTCS moves by at most 0.01 pp, but the counts the table requires to match exactly do not. | Starkville: 209/272 vs 210/272 first-time successes. Tie rows listed in the diagnostics output. | Add an explicit sort order to the config (e.g., `sort_keys: [site, session_start, session_end, session_id]`) through a decisions-log entry, then regenerate the lagging-site row. Otherwise the Phase 5 regression check fails, or passes only by luck of file order. |
| F4 | MINOR | `project_context.md` §6 outage recipe | **The recipe doesn't pin down window bounds, fleet weighting, or what "first-attempt success" means per charger.** 44 windows and 14 silent chargers reproduce under every reading I tried. Fleet availability ranges from 96.77% to 97.20% (life-weighted) and correlation from 0.577 to 0.588 across 9 window-bound readings. Only one reading gives 97.10% and 0.587: the window runs from the first other-charger success in the run to the charger's next own success, weighted by life over the 80 chargers. "Silent" must use the FTCS of visits whose first attempt was on that charger; using the charger's attempt success rate gives 28 silent chargers, not 14. | `.scratch/diag3.py` output | Write the exact window bounds, weighting and per-charger FTCS definition into `simulate/SIMULATION_SPEC.md` (Phase 3). S1 and S2 are anchored on this. |
| F5 | MINOR | `CLAUDE.md` §7, D2, `project_context.md` §7 #3 | **"Dropping unbound rows inflates FTCS by ~4 pts" understates the 13-month effect.** Dropping them gives **83.8% → 88.9% (+5.1)** over 13 months and **86.0% → 90.3% (+4.3)** in the recent quarter. Attempt success goes 79.5% → 84.7% (+5.1). | `sensitivity.drop_unbound` | Say "~5 pts over 13 months (~4 pts in the recent quarter)". This is the demo's judgement call, so the number should be exact. |
| F6 | MINOR | `CLAUDE.md` §7, `project_context.md` §7 #11 | **"42 of 88 commissioned mid-window, 3 stopped reporting" only reproduces with guessed cut-offs:** first session ≥ 2024-01-15 and last session < 2025-01-24. With first session ≥ 2024-02-01 the count is 39; with last session < 2025-01-01 it is 0. | `.scratch/diag.py` output | State the rule, or show a per-charger life table instead of a count. |
| F7 | NIT | `reference_numbers.md` | **Unbound share of failed attempts is 29.64%, which rounds to 29.6%.** 2 unbound attempts delivered ≥1 kWh. The doc's 29.7% matches all 2,187 unbound rows over 7,373 failed attempts, so the numerator probably included the 2 successes. Jan 2025 FTCS is 86.46%, which rounds to 86.5% (doc says 86.4%). | — | Rounding fixes when the table is regenerated. |
| F8 | MINOR (new defect) | `project_context.md` §7 (13 defects) | **Blank `peak_power_kw` isn't in the defect list.** It affects 2,549 rows overall and 2,146 DC attempts: 1,952 unbound, 194 on identified ports, and 166 of those with ≥1 kWh. It doesn't affect DC classification (the per-port max ignores blanks) or FTCS (which uses energy), but it belongs in the validation contract. | — | Add it as defect #14 in Phase 4 (WARN, counted). |

## Ambiguities from the context review that the data resolves (no effect on these numbers)
- **">0 kWh" coded as `0.0001`:** no energy values fall in (0, 0.0001), so the result is identical.
- **≥0.1 vs >0.1 kWh:** identical FTCS.
- **"Previous end" as previous row vs the visit's latest end:** identical visits, 29,101 either way.
- **Fuzzy match input:** must be the **full uppercased `evse_name`** (score 0.95). Matching on the text after "/" would put
  both GEA-1 chargers at the wrong sites (FPU in Fayetteville at 0.867, MU in Morristown at 0.897). Spec this explicitly.
- **DC chargers:** none has a non-DC identified port, so "attempt = any row on a DC charger" is unambiguous here.

## Questions for the design session (not decided here)
1. F1: which site-key rule, 41 or 40 sites? It changes structural counts and the D4 outage anchor (44 → 47 windows,
   14 → 15 silent chargers), not the headline.
2. F3: which tie-break is canonical? (Proposed: session_end, then session_id.)
3. F4: which outage-window reading is the intended one? It becomes the S1/S2 generator spec.

## What is genuinely strong (keep it)
- **Retrieval is provably complete** for both real sources, with zero drift since the research date.
- **Every headline and target figure reproduces independently from the text definitions alone:** 83.8%, 86.0%,
  1 in 6, the 5 lagging sites, 87.0%, 0 error codes and the ~30% unbound share of failures.
- **FTCS is robust** across every perturbation I tried: tie order, site merging, gap-reference reading and threshold
  boundary all stay within 83.8–83.9%.

## How to reproduce
```bash
# from repo root, with .venv active; downloads go to .scratch/raw/ (git-ignored)
python .scratch/verify_numbers.py      # writes .scratch/verify_results.json
python .scratch/diag.py; python .scratch/diag2.py; python .scratch/diag3.py; python .scratch/diag4.py
```
Note: `.scratch/` is git-ignored by design, so the script is not in the repo. Copy it into `reviews/` if you want the
check itself preserved as evidence.
