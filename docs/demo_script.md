# Demo script (3–5 minutes) — using the GitHub repo

**Before recording:** `source .venv/bin/activate`; have the repo open on GitHub and a terminal ready.

**0:00 — The problem (30 s).** Open `README.md`. "The operator's dashboard says 99% uptime. Drivers say chargers
don't work. The headline: 1 in 7 drivers fail on their first try — first-time charge success is 86.0% last quarter."

**0:30 — Where the truth lives (45 s).** Open `docs/source_map.md` §3. "Energy delivered per session is the system
of record for success — the status feed can't be, because a failed handshake returns the connector to *Available*.
The registry gives location, not 2024 availability. And the export's error field is blank on all 46,575 rows."

**1:15 — The judgement call (90 s).** Open `docs/decisions_log.md` → D2 and correction C2. "4.7% of rows have no
port id. The obvious 'cleaning' move is to drop them as bad keys. I checked first: every one is on a fast charger and
99.9% delivered zero energy — they are failed attempts that died before the port was recorded. Dropping them would
delete 29.6% of all failures and inflate the KPI by about 4 points. So they are kept as *unbound* attempts, counted
and logged, and they became a finding: a third of failures can't be located by any crew." Show the WARN line in
`validation_report.json`.

**2:45 — Run it (60 s).** `python run_pipeline.py --offline` → point at: checksum lines, the HTTP 500/429 retries,
the three gates, `PIPELINE SUCCESS`. Then `python run_pipeline.py --offline --chaos missing_column` → exit 2,
"no processed output published".

**3:45 — Evidence and decision (45 s).** Open `docs/evidence.md`. "Five sites below the median — lifting them reaches
the 87% target. Uptime 99.8% vs driver success 86%: uptime can't be the headline. Next: record port and error code on
every attempt, then target 90%. No AI predictor yet — there's no failure label to learn from."
