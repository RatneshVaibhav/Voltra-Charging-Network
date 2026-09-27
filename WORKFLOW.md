# WORKFLOW — installing, running, reviewing, submitting

## 1. Install the final snapshot into your existing repo (`~/Voltra-Charging-Network`)
The zip's top folder is named `Voltra-Charging-Network`, so extracting it into your home folder overwrites your repo
in place (your `.git`, `.venv` and `.env` are untouched):
```bash
cd ~
unzip -o ~/Downloads/voltra_final.zip
cd ~/Voltra-Charging-Network
ls                        # you should see run_pipeline.py, pipeline/, simulate/, docs/, CLAUDE.md …
```

## 2. Run it
```bash
source .venv/bin/activate
pip install -r requirements.txt
python run_pipeline.py --offline          # ~15 s → PIPELINE SUCCESS
pytest -q                                 # 9 passed
python run_pipeline.py                    # optional live run (internet; DEMO_KEY is fine)
```

## 3. Commit and push
```bash
git add -A
git commit -m "Final: phases 2-7 — source map, retrieval, validation gate, model, pipeline, evidence"
git push
```

## 4. Optional review with Claude Code (in the Claude Code panel)
Start a new conversation so it reads the new `CLAUDE.md`, then run any of:
```
/review-phase 6
/integrity-audit
/grader-view
```
Each writes a short report to `reviews/`. They are written to be token-efficient (no raw data read into context).
Commit the reports: `git add reviews && git commit -m "Reviews" && git push`.

## 5. Demo
Follow `docs/demo_script.md` (3–5 minutes).
