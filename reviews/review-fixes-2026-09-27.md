# Review fixes — 2026-09-27

Resolution of every finding in [`full-review-2026-09-27.md`](full-review-2026-09-27.md). Each fix is in a named commit
and verified by a test or a command. After all fixes: **30 tests pass** (on pandas 3.0.6 and 2.3.3, with byte-identical
outputs). Every §4 regression number is unchanged: FTCS 86.03% / 83.87%, 29,036 visits, 40 sites. Validation is
**33 checks: PASS 17 · WARN 15 · UNKNOWN 1**. The simulated systems rebuild byte-identical.

| ID | Severity | Fix | Commit | Verified by |
|---|---|---|---|---|
| F1 | MAJOR | `sessions.header_consistency` FAILs when any header row differs from the first file's; columns are never re-mapped | Validation hardening (D8) | `test_reordered_header_in_a_later_file_fails_the_schema_gate`; real data: 52/52 headers identical |
| F2 | MAJOR | `sessions.numeric_parse`: missing `energy_kwh` FAILs (zero tolerance); 2,549 blank `peak_power_kw` counted as WARN, left missing, documented | Validation hardening (D8) | `test_missing_energy_fails_but_blank_peak_power_only_warns`, `test_missing_numbers_are_counted_not_imputed` |
| F3 | MAJOR | Retry switching measured by charger over retry visits: **27.2%**. The 43.5% is kept for what it measures (visits port-level grouping would split, the D3 rationale) | Measurement corrections (D9) | `test_retry_switch_counts_chargers_not_unbound_port_keys` |
| F4 | MAJOR | 21 new tests (9 → 30): retry paths, redaction, rollback, conflicting duplicates, unresolved site, leak detection, lagging rule, baseline, open outages | all three fix commits | `pytest -q` → 30 passed |
| F5 | MINOR | `open_runs_at_data_end`: S29 chargers 13664401 and 13164881 listed (WARN, CSV, evidence page), never counted as downtime | Measurement corrections (D9) | `test_open_run_at_data_end_is_listed_not_counted_as_downtime`; run log `open at data end=2` |
| F6 | MINOR | Chaos runs write only under `data/*/chaos/<name>/` and `logs/*_chaos-<name>.*`; a stale failure report is removed on success | Dependability (D10) | Real partition and raw inputs byte-identical after all five demos |
| F7 | MINOR | A failed swap restores the previous partition | Dependability | `test_failed_swap_restores_the_previous_partition` |
| F8 | MINOR | API keys redacted from every log line and error message (`redact`, `from None`) | Dependability | `test_api_key_never_reaches_logs_or_error_messages` |
| F9 | MINOR | Whitespace strip works on pandas ≥ 3 `str` dtype; `pandas>=2.0,<4` pinned | Validation hardening | `test_whitespace_is_stripped_whatever_the_text_dtype`; suite passes on pandas 2.3.3 and 3.0.6 |
| F10 | MINOR | Every gate logs `VALIDATE \| <gate> PASSED \| counts` and one line per WARN/UNKNOWN | Validation hardening | `test_gate_logs_its_counts_and_every_warning`; console shows the D2 WARN line |
| F11 | MINOR | Decisions log: every pre-D7 figure marked *(superseded …)* with its current value; D5–D7 given options and consequences; decision index added | Docs | Read `docs/decisions_log.md` |
| F12 | MINOR | The judgement call is computed every run: `metrics.json → judgement_call` and a *drop port-less attempts (rejected, D2)* sensitivity row → **90.33% (+4.30)** quarter, 88.92% (+5.05) 13 months | Measurement corrections (D9) | `test_dropping_port_less_attempts_is_measured_not_applied` |
| F13 | MINOR | Federal-style uptime and the demo's uptime line labelled as simulated / illustrative | Docs | README §1, demo script 0:25 and Q&A |
| F14 | NIT | "Repair effect" relabelled charger first-attempt success before → after, with a no-control-group caveat in the metric, the evidence table and the docs | Measurement corrections (D9) | `metrics.json → illustrative_simulated_input.repair_effect.caveat` |
| F15 | NIT | `visit_integrity` checks ids, coverage and outcomes; `no_simulated_fields_in_kpi_inputs` checks content (R1 session ids, R1 + derived columns) | Validation hardening | `test_simulated_or_foreign_rows_in_kpi_inputs_fail` |
| F16 | NIT | Gate tolerances, baseline length, repair window and commissioning grace moved to `config/kpi_definitions.json`; the simulator reads the visit window from config | Validation hardening | `grep` finds no literal thresholds left in `validate.py`/`metrics.py` |
| F17 | NIT | `Retry-After` parsed as seconds or an HTTP date, capped (`MAX_RETRY_WAIT_SECONDS`); no wait is logged after the final attempt | Dependability | `test_429_honours_retry_after_seconds_and_http_dates`, `test_server_requested_wait_is_capped` |
| F18 | NIT | `stale_data` withholds the latest monthly export (a late delivery): only freshness fails, lag 32 days | Dependability (D10) | `--chaos stale_data` → exit 2, single failing check |
| F19 | NIT | Published partitions are `0755` | Dependability | asserted in the rollback test |
| R0 | — | `approved_in` now D1–D9; D3's site text marked superseded by D7; each version bump (1.2.0, 1.3.0) has a dated entry (D8, D9) | Validation hardening, measurement corrections, docs | `config/kpi_definitions.json`, `docs/decisions_log.md` |
| F20 (new) | MINOR | Found while fixing F3: the docs said port-less failures "cannot be located, so no crew can be sent". The charger id is present on every one, so the charger is known; what is missing is the port binding and the failure stage. Wording corrected in README, evidence (generated), data model and source map (C18) | Docs | `grep -ri "no crew"` → only in the correction note |

## Questions for the owner — resolved
- **Final build in git:** pushed as phased commits (Phases 2–7, then the review and the fixes).
- **S29:** surfaced as a verification item, not a crew item. It could be a decommissioning, and the 2026 registry
  snapshot cannot settle a 2025 question.
- **Port-switch restatement:** D3 is unchanged; its rationale now cites the 43.5% for what it measures, and the
  behavioural figure is 27.2% (D9 amendment).
