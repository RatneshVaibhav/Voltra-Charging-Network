---
name: review-phase
description: Independent review of one phase (1-7) against the rubric, its Definition of Done, reference numbers and red flags. Writes reviews/phase-N-review.md.
argument-hint: "[phase-number]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git status *)
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(python run_pipeline.py *)
  - Bash(pytest *)
---

# Review phase $0

Follow `.claude/rules/agent-efficiency.md` throughout: never Read raw/generated data files; run scripts and read
their summaries.

1. Read `CLAUDE.md`, the phase $0 Definition of Done in `docs/agent/review_checklist.md` §C, and the matching
   deliverable (Phase 2 `docs/source_map.md`, 3 `pipeline/extract.py` + `simulate/`, 4 `docs/validation_contract.md`
   + `pipeline/validate.py`, 5 `docs/data_model.md` + `pipeline/transform.py`/`metrics.py`, 6 `run_pipeline.py` +
   `docs/gate2_data_readiness.md` + `tests/`, 7 `docs/evidence.md` + `README.md` + `docs/demo_script.md`).
2. **Phase 1 is documentation only:** check internal consistency; do not run the pipeline.
   **Phases 3–7:** run `python run_pipeline.py --offline` once and `pytest -q`; read only `metrics.json`,
   `validation_report.json` and `evidence_table.md` from `data/processed/run_date=2025-02-01/`; compare with
   `docs/agent/reference_numbers.md` (counts exact, rates ±0.1 pp).
3. Grep the phase's code for the red flags in `docs/agent/review_checklist.md` §D.
4. Judge each rubric pillar (strong / adequate / at risk) with the single most important reason.
5. Write `reviews/phase-$0-review.md` using the template in §F. Every finding: severity, file:line, evidence, fix.
   Findings that would change a locked decision go under "Questions for the design session".
6. Tell Lakshya the verdict and the BLOCKER/MAJOR count in 3–5 lines.
