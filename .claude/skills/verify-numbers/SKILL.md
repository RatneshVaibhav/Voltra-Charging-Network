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

Goal: an **independent** second computation — not a rerun of the same code.

1. Read `docs/agent/reference_numbers.md` (targets + reproduction recipe), `config/kpi_definitions.json`, and
   `CLAUDE.md` §5 (exact definitions).
2. Mode:
   - Default (**independent**): write your own script in `.scratch/verify_numbers.py` (git-ignored). Download R1 from the
     Hugging Face URLs in `CLAUDE.md` §6, verify sizes + git-blob SHA-1, call the AFDC API at `developer.nlr.gov`
     using `AFDC_API_KEY` from the environment (ask Lakshya to export it; never print it), then implement the definitions
     from the text — do **not** import repo code.
   - `$ARGUMENTS` contains `from-pipeline`: run the repo's pipeline/scripts and read their outputs instead.
3. Produce a table: quantity | expected | got | Δ | OK (counts exact; rates ±0.1 pp).
4. For every mismatch: find the root cause (definition interpretation? data change upstream? bug?). Say which.
   Do not edit `reference_numbers.md`.
5. Save the result to `reviews/verify-numbers-<YYYY-MM-DD>.md` and summarise in chat.
