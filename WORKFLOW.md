# WORKFLOW — running, reviewing, changing, submitting

## 1. Set up and run
```bash
git clone https://github.com/RatneshVaibhav/Voltra-Charging-Network.git && cd Voltra-Charging-Network
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_pipeline.py --offline          # ~10 s → PIPELINE SUCCESS, exit 0
pytest -q                                 # 30 passed
python run_pipeline.py                    # optional live run (internet; DEMO_KEY is fine)
```

## 2. Show the failure paths
```bash
python run_pipeline.py --offline --chaos missing_column    # exit 2
python run_pipeline.py --offline --chaos duplicate_rows    # exit 0, 50 collapsed
python run_pipeline.py --offline --chaos stale_data        # exit 2, lag 32 days
python run_pipeline.py --offline --chaos api_outage        # exit 1 after 3 attempts
python run_pipeline.py --offline --chaos bad_checksum      # exit 2
```
Chaos runs write only under `data/*/chaos/<name>/` and `logs/*_chaos-<name>.*`; the real result is never touched.

## 3. Changing a rule
1. Add a dated entry to `docs/decisions_log.md` (decision · options · evidence · consequences).
2. Change `config/kpi_definitions.json` and bump its version.
3. Run the pipeline and tests; explain every number that moves against `docs/agent/reference_numbers.md`.
4. Commit the config, code, docs and the refreshed reference numbers together.

## 4. Review with Claude Code (optional)
In a new conversation (so it reads `CLAUDE.md`): `/review-phase 6`, `/integrity-audit`, `/grader-view`,
`/verify-numbers`. Each writes a short report to `reviews/`; commit the reports.

## 5. Demo
Follow `docs/demo_script.md` (about 4½ minutes, word for word, with likely questions and answers).
