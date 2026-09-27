# Data integrity rules (always loaded)

- No row may leave the dataset without a written rule, a count, and a log line. "Cleaning" is a decision, not a chore.
- Representation fixes (case, whitespace, glued-header repair) are allowed if counted and logged.
  Semantic fixes (re-mapping categories, imputing values, reclassifying anomalies) need an approved rule in
  `docs/validation_contract.md` or `docs/decisions_log.md`.
- Blank `port_id` rows on DC chargers are **failed attempts**, never "bad keys" (D2).
- Label every inferred fact as inferred (e.g., "inferred outage", "zero energy ⇒ inferred failed attempt").
- The KPI and headline metrics use **real data only**. Anything touching simulated inputs is labelled
  "illustrative (simulated input)".
- If a number in `docs/agent/reference_numbers.md` moves, stop and explain before continuing.
