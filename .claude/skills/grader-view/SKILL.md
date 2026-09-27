---
name: grader-view
description: Score the whole repository the way the course grader would (five pillars x 20%) and list the highest-leverage improvements before submission.
disable-model-invocation: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git log *)
---

# Grader view

Act as the FDE course grader. Read `docs/agent/project_context.md` §1 (assignment + rubric) and
`docs/agent/review_checklist.md` §B and §G first. You may delegate to the `fde-reviewer` subagent.

1. For each pillar (source reasoning, retrieval, validation, workflow + metrics, pipeline dependability) give a score
   1–5, the evidence a grader would see (file paths), and the single biggest gap.
2. Check the submission package: README sections, source map + diagram, runnable one-command pipeline, evidence table
   with 3–5 metrics, Known/Unknown/Assumption/Limitation, demo-able judgement call.
3. Answer the nine grader questions in §G with the file that answers each — or "not answerable yet".
4. List the **top 5 improvements ranked by rubric impact per hour of work**, given the deadline in `CLAUDE.md`.
5. Save to `reviews/grader-view-<YYYY-MM-DD>.md`; summarise in chat.
