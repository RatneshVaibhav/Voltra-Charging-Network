---
name: review-phase
description: Full independent review of one delivered phase against the rubric, its Definition of Done, reference numbers and red flags. Writes reviews/phase-N-review.md.
argument-hint: "[phase-number]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git status *)
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(git tag *)
---

# Review phase $0

1. **Orient.** Read `CHANGELOG.md` (entry for phase $0), `CLAUDE.md`, and the phase $0 Definition of Done in
   `docs/agent/review_checklist.md` §C. Run `git status` and `git log --oneline --decorate -n 8`.
   If the working tree has uncommitted changes other than `reviews/`, say so first — the review must be of a known state.
2. **Scope the diff.** `git diff phase-<previous>..HEAD --stat` (if the previous tag is missing, diff against the first commit).
3. **Delegate the deep review** to the `fde-reviewer` subagent with this brief:
   "Review phase $0 of the Voltra project. Follow your full procedure: read the context files, run what can be run,
   reproduce reference numbers, check the phase $0 Definition of Done, grep red flags, judge all five rubric pillars,
   and return the report in the review_checklist §F template."
4. **Sanity-check the subagent's report**: every finding has severity + location + evidence + fix; no finding asks to
   change a locked decision (those go under "Questions for the design session").
5. **Write** the report to `reviews/phase-$0-review.md` (create the folder if needed). Do not modify any other file.
6. **Tell Lakshya** the verdict in 3–5 lines, the BLOCKER/MAJOR count, and: "Upload or paste
   `reviews/phase-$0-review.md` into the design session so fixes land in the next snapshot."
