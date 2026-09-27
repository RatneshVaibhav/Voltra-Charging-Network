# Agent efficiency rules (always loaded)

- Never use the Read tool on raw or generated data files: `data/source_snapshot/**`, `data/raw/**`,
  `data/processed/**/*.csv`, `*.json.gz`, `*.db`. Process them with a short script via Bash and read only the
  script's printed summary. Small files (metrics.json, validation_report.json, evidence_table.md) are fine to read.
- To understand a file's structure, read only its first ~20 lines.
- To verify numbers, prefer `python run_pipeline.py --offline` and read `metrics.json` — do not re-derive from raw data
  unless the user explicitly asked for an independent reproduction (`/verify-numbers`).
- A review of documentation-only changes checks internal consistency; it does not rerun data pipelines.
- If a task has used a lot of tokens without findings, stop, summarise, and ask before expanding scope.
