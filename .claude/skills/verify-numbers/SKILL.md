---
name: verify-numbers
description: Independently recompute the project's reference numbers from raw sources and compare them to docs/agent/reference_numbers.md. Use to double-check any claimed figure.
argument-hint: "[optional: 'from-pipeline' to use repo code instead of an independent script]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Verify reference numbers

Goal: an **independent** second computation — not a rerun of the same code. This is the only command that
re-derives numbers from raw data. Keep raw data OUT of your context: your script must print compact summaries only
(see `.claude/rules/agent-efficiency.md`). Use the committed snapshot in `data/source_snapshot/` unless asked to go live.

1. Read `docs/agent/reference_numbers.md` (targets + reproduction recipe), `config/kpi_definitions.json`, and
   `CLAUDE.md` §5 (exact definitions).
2. Mode:
   - Default (**independent**): write your own script in `.scratch/verify_numbers.py` (git-ignored). Read the snapshot CSVs in
     `data/source_snapshot/sessions/`, verify sizes + git-blob SHA-1 against `hf_tree_snapshot.json`, load
     `afdc_stations_snapshot.json`, then implement the definitions from `config/kpi_definitions.json` in your own code —
     do **not** import repo code.
   - `$ARGUMENTS` contains `from-pipeline`: run the repo's pipeline/scripts and read their outputs instead.
3. Produce a table: quantity | expected | got | Δ | OK (counts exact; rates ±0.1 pp).
4. For every mismatch: find the root cause (definition interpretation? data change upstream? bug?). Say which.
   Do not edit `reference_numbers.md`.
5. Save the result to `reviews/verify-numbers-<YYYY-MM-DD>.md` and summarise in chat.
