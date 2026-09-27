# Reference Numbers — regression targets (definitions v1.3.1)

Generated from `data/processed/run_date=2025-02-01/` produced by `python run_pipeline.py --offline`.
Any change to extract / clean / transform code must reproduce these numbers or explain the difference **before**
proceeding. **Tolerances:** counts exact; percentages ±0.1 pp. If a number moves: (1) identify the rule that changed,
(2) check it is an approved entry in `docs/decisions_log.md`, (3) otherwise treat it as a regression — do not "update
the table". The live mode (`python run_pipeline.py`) reproduces the same numbers (verified 2026-09-27).

| Quantity | Value |
|---|---|
| Session rows (13 files) | 46,575 |
| Glued-header repairs | 39 |
| Data window (session_start, UTC) | 2024-01-01 00:17 → 2025-01-30 23:45 |
| DC chargers / sites (40 after merging 3 address variants) | 88 / 40 |
| Site resolution: port id / name match / unresolved | 86 / 2 / 0 |
| DC attempts (incl. unbound) / unbound | 35,996 / 2,187 |
| DC energy buckets =0 / (0,0.1] / (0.1,1) / [1,5] / >5 kWh | 6,899 / 215 / 259 / 846 / 27,777 |
| Visits | 29,036 |
| Attempt success (13 mo / baseline quarter) | 79.5% / 82.0% |
| **FTCS 13 months** | **83.87%** |
| **FTCS baseline quarter (Nov 2024–Jan 2025)** · visits | **86.03%** · 9,976 |
| Troubled success / failed visits / attempts per visit (13 mo) | 10.4% / 5.8% / 1.24 |
| Troubled success / failed visits (baseline quarter) | 9.3% / 4.7% |
| Multi-attempt visits · split by port-level grouping | 16.0% · 43.5% |
| Retry visits (first failed, ≥ 2 attempts) · of which moved charger | 12.2% · 27.2% |
| Identified ports per DC charger | 1 (88 of 88) |
| Port-less share of failed attempts | 29.6% |
| Sensitivity FTCS: >0 / ≥0.1 kWh / site 2 min / 10 min / 15 min / port 2 min | 84.8% / 84.4% / 83.2% / 84.1% / 84.1% / 82.4% |
| Sensitivity FTCS baseline quarter, same order | 86.6% / 86.4% / 85.4% / 86.2% / 86.1% / 84.5% |
| Judgement call: FTCS if port-less attempts dropped (quarter · 13 mo) | 90.33% (+4.30) · 88.92% (+5.05) |
| Sensitivity failed-visit range | 4.9–11.3% |
| Monthly FTCS Jan 2024 → Jan 2025 | 77.69% → 86.44% |
| Worst site ≥200 visits (13 mo) | S32 69.2% (487 visits) |
| Lagging sites (baseline, ≥50 visits, >5.0 pts below median 86.379%) | S40 75.32%, S17 77.21%, S01 78.47%, S08 79.9%, S28 81.33% |
| Target projection if lagging sites reach the median | 86.03% → 87.01% |
| Inferred outages: windows · fleet availability · silent chargers · corr | 46 · 97.05% · 15 · 0.55 |
| Inferred outages open at data end | 2 — S29 chargers 13664401, 13164881 |
| Blank `peak_power_kw` (all rows) · missing `energy_kwh` | 2,549 · 0 |
| Illustrative: operator uptime / federal-style / inferred availability | 99.77% / 98.18% / 97.05% |
| Illustrative: charger first-attempt success before → after corrective work orders (median, n) | 82.2% → 88.5% (n=25) |
| Simulated volumes: S1 events / S2 work orders | 124,968 / 426 |
| Validation summary (33 checks) | PASS 17, WARN 15, UNKNOWN 1 |
| Tests | 30 passed |
