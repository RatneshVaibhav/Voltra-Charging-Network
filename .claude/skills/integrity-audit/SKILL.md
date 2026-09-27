---
name: integrity-audit
description: Audit the repo for silent data loss, simulated data leaking into the KPI, env-driven business rules, stale/fabricated endpoints, secrets, and non-atomic or non-idempotent outputs.
disable-model-invocation: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git status *)
  - Bash(git log *)
  - Bash(git diff *)
---

# Integrity audit

Check each item; report PASS / FAIL / N/A (not yet built) with file:line evidence.

1. **Silent row loss:** every `dropna`, `drop_duplicates`, `fillna`, `.replace`, boolean row filter, and `merge(how="inner")`
   has a count + log line and a rule reference. Blank `port_id` rows on DC chargers are kept (D2).
2. **Silent column skip:** no `[c for c in cols if c in df.columns]`-style selection; missing required columns FAIL.
3. **Site logic:** no use of the `evse_name` "/" prefix as a site; DC classification per charger.
4. **Simulation leakage:** no field from `data/simulated_client_systems/` (or `data_origin == "simulated"`) reaches FTCS or
   headline metrics; illustrative metrics are labelled.
5. **Config discipline:** thresholds/windows only from `config/kpi_definitions.json`; env only for infra settings.
6. **Endpoints & secrets:** no `developer.nrel.gov`; no API keys, tokens or `.env` committed (`git log -p` spot-check);
   `.gitignore` covers `.env`, `course/`, `.scratch/`, raw/processed data.
7. **Retrieval honesty:** completeness proven for every source; raw saved before parsing; retries bounded and only on
   transient errors; timeouts set.
8. **Publishing:** outputs written atomically as a whole partition; rerun idempotent; raw partition cleared per run.
9. **Docs honesty:** every number in `README.md`/`docs/` traceable to code output or a cited source; no causal claims;
   no named real operator attributed.

Write findings to `reviews/integrity-audit-<YYYY-MM-DD>.md` using the severity scale in
`docs/agent/review_checklist.md` §A, and summarise in chat.
