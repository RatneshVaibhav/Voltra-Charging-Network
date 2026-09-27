# Reference Numbers — regression targets

These numbers were computed during Phase 1 research (2026-09-27) on the final locked definitions (D2, D3).
Any change to extract / clean / transform code must reproduce them, or explain the difference **before** proceeding.

**Tolerances:** counts must match exactly; percentages within ±0.1 percentage point.
If a number moves: (1) identify which rule changed, (2) check whether the change is an approved decision in
`docs/decisions_log.md`, (3) if not approved, it is a regression — report it, do not "update the table".

**How they were computed (so you can reproduce independently):**
- Load all 13 `Se_*.csv` files; repair glued headers by inserting a newline before any `provider_id,station_id` not at
  line start; parse with a CSV reader (quoted fields contain commas); drop repeated header rows.
- DC chargers per `config/kpi_definitions.json`; include blank-`port_id` rows on DC chargers as unbound attempts.
- Sites via the resolution chain using the AFDC regional pull (TN, AL, KY, MS, GA, VA, NC; ChargePoint Network).
- Visits: sort by (site, session_start); new visit unless gap to previous end at the same site ∈ [−2, +5] min.
- Recent quarter = visits whose first attempt started in 2024-11, 2024-12 or 2025-01.
- Lagging sites = recent-quarter sites with ≥ 50 visits and FTCS more than 5 pts below the recent median site FTCS.
- Outage inference: see `docs/agent/project_context.md` §6 ("Real-data outage inference").

## Table

| Quantity | Value |
|---|---|
| Session rows (13 files) | 46,575 |
| Glued-header defects | 39 |
| Date range (UTC) | 2024-01-01 00:17 → 2025-01-31 03:25 |
| Distinct chargers / non-blank ports (all) | 140 / 200 |
| DC chargers / DC identified ports / sites | 88 / 88 / 43 |
| DC attempts (incl. unbound) / unbound | 35,996 / 2,187 |
| DC energy buckets: =0 / (0,0.1] / (0.1,1) / [1,5] / >5 kWh | 6,899 / 215 / 259 / 846 / 27,777 |
| Visits (D2 + D3) | 29,101 |
| Attempt success | 79.5% |
| **FTCS (13 months)** | **83.8%** |
| Troubled success / failed visits / attempts per visit | 10.3% / 5.9% / 1.24 |
| Multi-attempt visits / of which switched port | 15.9% / 42.3% |
| Unbound share of failed attempts | 29.7% |
| Recent quarter (Nov 2024–Jan 2025): visits / FTCS / failed visits / attempt success | 9,989 / 86.0% / 4.8% / 82.0% |
| Sensitivity FTCS: >0 kWh / ≥0.1 kWh / 2-min / 10-min / 15-min | 84.7% / 84.4% / 83.2% / 84.0% / 84.1% |
| Monthly FTCS Jan 2024 → Jan 2025 | 77.7% → 86.4% |
| Worst site (≥200 visits, 13 months) | 69.2% (487 visits) |
| 5 lagging sites (recent quarter, ≥50 visits, >5 pts below median 86.3%) | 75.3, 76.8, 78.5, 79.9, 81.3% → network 86.0% → 87.0% if lifted to median |
| Outage inference | 44 windows · fleet availability 97.05% · 14 silent chargers · corr 0.59 |

---
