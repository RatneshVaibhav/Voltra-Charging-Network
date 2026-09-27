# WORKFLOW — how phases move from the design session into this repo

**Single-writer rule:** tracked project files are written in the design session (Claude.ai) and arrive as full repo
snapshots. Claude Code **reviews and verifies**; it does not rewrite tracked files unless you explicitly ask. Anything you
change locally must be sent back to the design session, or the next snapshot will overwrite it. Exceptions: `.env`
(never committed) and `reviews/` (Claude Code writes reports there).

The GitHub repo is the source of truth. If the design session ever loses its working copy, upload the latest repo ZIP
(GitHub → Code → Download ZIP) to the design chat and work continues from it.

---

## One-time setup

> The repo folder **must** be named `voltra-charging-reliability` so snapshots extract on top of it.

```bash
# 1) extract voltra_phase1.zip somewhere, then:
cd voltra-charging-reliability
git init -b main
git add -A
git commit -m "Phase 1: decisions, context layer, skeleton"
git tag phase-1
# 2) create an EMPTY public repo on GitHub named voltra-charging-reliability (no README), then:
git remote add origin https://github.com/<your-username>/voltra-charging-reliability.git
git push -u origin main --follow-tags

# 3) Python environment
python -m venv .venv
# macOS/Linux:  source .venv/bin/activate      Windows (PowerShell):  .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 4) secrets (never committed)
cp config/.env.example .env        # Windows: copy config\.env.example .env
# edit .env → AFDC_API_KEY=<your free key from developer.nlr.gov>
```
Claude Code is blocked from reading `.env` (see `.claude/settings.json`). When a review needs the key, export it in
the terminal session instead: macOS/Linux `export AFDC_API_KEY=...` · PowerShell `$env:AFDC_API_KEY="..."`.

**Check Claude Code sees the context:** open the folder in VS Code, start Claude Code, run `/context` and confirm
`CLAUDE.md` is listed under memory files; type `/` and confirm `review-phase`, `verify-numbers`, `integrity-audit`,
`grader-view` appear.

**Optional:** put the course PDFs in `course/` (git-ignored) so Claude Code can consult the original brief.

---

## The loop for every phase N

| # | Step | Command |
|---|---|---|
| 1 | Start clean | `git status` → nothing to commit |
| 2 | Download `voltra_phaseN.zip` from the design session | — |
| 3 | Extract **on top of** the repo (run from inside the repo) | macOS/Linux: `unzip -o ~/Downloads/voltra_phaseN.zip -d ..`<br>Windows: `Expand-Archive -Path $HOME\Downloads\voltra_phaseN.zip -DestinationPath .. -Force` |
| 4 | Apply deletions listed under **Removed** in `CHANGELOG.md` (if any) | `git rm <path>` |
| 5 | See exactly what changed | `git status` · `git diff --stat` |
| 6 | Commit the snapshot (not yet tagged) | `git add -A && git commit -m "Phase N: <title>"` |
| 7 | Independent review in Claude Code | `/review-phase N` (+ optionally `/integrity-audit`, `/verify-numbers`) |
| 8 | Run what the phase provides | see **How to run** in `CHANGELOG.md` for phase N |
| 9 | Commit the review, tag, push | `git add reviews && git commit -m "Review: phase N"`<br>`git tag phase-N && git push --follow-tags` |
| 10 | Bring back to the design session | upload/paste `reviews/phase-N-review.md` + any error output |

If the review finds problems, the design session ships `voltra_phaseN.1.zip` → repeat steps 1–10 and tag `phase-N.1`.

**If you changed a tracked file locally** (e.g., a Windows path fix), send it back before the next phase:
```bash
git diff phase-N -- . ':!reviews' > local_changes.patch   # then upload local_changes.patch to the design chat
```

---

## Useful Claude Code commands (defined in `.claude/skills/`)

| Command | What it does | Output |
|---|---|---|
| `/review-phase N` | Full review vs rubric, phase Definition of Done, reference numbers, red flags (uses the `fde-reviewer` subagent) | `reviews/phase-N-review.md` |
| `/verify-numbers` | Independently recomputes the reference numbers from raw data with its own script | `reviews/verify-numbers-<date>.md` |
| `/integrity-audit` | Hunts silent data loss, simulation leakage, env-driven rules, secrets, non-atomic outputs | `reviews/integrity-audit-<date>.md` |
| `/grader-view` | Scores the repo like the course grader (5 × 20%) + top-5 improvements | `reviews/grader-view-<date>.md` |

Suggested cadence: `/review-phase N` every phase; `/verify-numbers` after Phase 1 (independent check of the research)
and after Phases 3 and 5; `/integrity-audit` after Phases 4 and 6; `/grader-view` before submission.
