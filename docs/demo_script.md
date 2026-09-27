# Demo script (about 4 minutes) — shown entirely from the README on GitHub

**The judgement call:** 2,187 charging attempts with no port id were **kept as failed attempts** instead of being
dropped as "bad rows". Dropping them would have shown the client 90.33% — their stretch target — with no repair at all.

No terminal is needed: every command, and its real output, is printed in the README (§4, §7, §8).

## Before you record
1. Open the repo's front page on GitHub (the README). Zoom the browser to 110–125%.
2. Scroll slowly to the bottom once, so every diagram has rendered, then press **Home** to return to the top.
3. **How to move around:** the **Contents:** line of links sits just under the small *How to read this repo* table
   near the top. Press **Home**, then click a Contents link to jump to a section. Scroll down with the mouse wheel.
4. Loom: Screen + Camera, full screen, notifications off. Keep this script on a second screen.

---

## Scene 1 · 0:00–0:25 · The chart
**SHOW:** The top of the README: the bar chart titled *Same fleet, four ways of measuring reliability*. Rest the
mouse on the three **grey** bars, then on the **blue** bar.
> "Hi, I'm [your name]. This is my FDE data-foundations project for a fictional client, Voltra Charging Network,
> built on real public charging data. This chart is the whole story. The operator's dashboard says 99.8% uptime.
> The blue bar is what drivers experience: only 86% get a charge on their first try. One in seven drivers fail."

## Scene 2 · 0:25–0:50 · The whole project in one picture
**SHOW:** Scroll down to the heading **The whole project in one picture**. Move the mouse down the diagram, box by box.
> "Here's the project in one picture. Four sources: the two solid boxes are real — charging sessions and the
> government station registry. The two dashed boxes are simulated, and never touch the KPI. One command runs the
> pipeline, through three validation gates, down to the KPI and three actions."

## Scene 3 · 0:50–1:45 · The judgement call
**SHOW:** Press **Home**, then click **4 Judgement call** in the Contents line. Under the bold line **The call in one
picture:**, point at the diagram from top to bottom: the top box · the four small check boxes · the middle box · the
two boxes marked ❌ (red outline) · the box marked ✅ (green outline) · the two boxes at the bottom.
> "Here's the call. 2,187 rows, about 5% of the data, have no port id. The reflex is: bad key, drop the row. First I
> checked them. Every one is on a fast charger, 99.9% delivered zero energy, the median lasted two minutes, and the
> charger is still known. So they're not corrupt rows — they're failed charging attempts. Drop them, and first-time
> success reads 90.33%: the client's stretch target, met on paper without fixing a single charger. So I kept them.
> And that became a finding: a third of failures never reach any uptime record, and the fix is asking the vendor to
> record the port and an error code on every attempt."

## Scene 4 · 1:45–2:10 · The proof, printed on every run
**SHOW:** Scroll down past the two tables to the bold line **What the pipeline writes about it on every run**. Point
at `"ftcs_baseline_if_dropped_pct": 90.33` and `"dropping_would_appear_to_meet_stretch_target": true`. Then scroll a
little to **And what it prints on every run** and point at the line with `WARN sessions.blank_port_id n=2187`.
> "This isn't a number I typed into a slide — the pipeline recomputes it on every run, and prints the decision: 2,187
> kept, never dropped. It's also logged in the decisions log with every option I rejected, including my own first
> mistake."

## Scene 5 · 2:10–2:40 · What a run looks like
**SHOW:** Keep scrolling down to the heading **6. How the pipeline works** and pause on its diagram. Keep scrolling to
**7. Run it**: show the table under **Every command, and what it does:**, then the block under **What a run prints**.
Point at the `sha1_ok=True` line, the `status=500` and `status=429` lines, and the three lines ending in `PASSED`.
> "One command runs everything, and here's what it prints. Every file is checked against the publisher's checksum.
> The status API fails on purpose, and the pipeline retries with a limit. Then three validation gates, each
> reporting what passed and what it accepted as a known warning."

## Scene 6 · 2:40–3:05 · It fails safely
**SHOW:** Scroll down to **8. Show me it fails safely**. Point at the table, then under the bold line **What each demo
prints**, point at the `missing_column` example's line `PIPELINE STOPPED AT VALIDATION GATE (exit 2)`.
> "And when something breaks, it stops. If the vendor drops the energy column, the gate stops the run and publishes
> nothing. Late data, a corrupted file or an API outage stop it the same way."

## Scene 7 · 3:05–3:40 · The decision it supports
**SHOW:** Press **Home**, then click **2 Decision** in the Contents line. Point at items **1**, **2** and **3** of the
numbered list.
> "So what does the client do on Monday? Send crews to five sites more than five points below the median — that gets
> the network to 87%, the six-week target. Check S29, where two chargers have been silent since January — invisible
> to the KPI. And ask the vendor to record the port and an error code on every attempt."

## Scene 8 · 3:40–4:00 · Close
**SHOW:** Press **Home** and finish on the chart.
> "Record that, and 90% becomes a target you can manage — not a number you can reach by deleting rows. That was the
> judgement call: make the number true, not the data look clean. Thanks for watching."

---

## If you are asked (short, honest answers)
| Question | Answer |
|---|---|
| Why not just drop the blank-port rows? | They are failed attempts (all on DC chargers, 99.9% zero energy, 2-minute median). Dropping them gives 90.33%, which would falsely "meet" the stretch target. |
| How do you know a visit is one driver? | We don't have driver ids. The 5-minute site window comes from UC Davis, and our own retry-gap curves cross at ~5 min. FTCS stays within 82.4–84.8% across every definition tested. Two drivers arriving within 5 minutes can merge — a stated limitation. |
| Isn't 1 kWh arbitrary? | It is the peer-reviewed UC Davis screen, and 93.6% of sub-1 kWh attempts are exactly zero, so thresholds from 0 to 1 kWh move FTCS by ≤ 0.9 pts. |
| Is the 99.77% uptime real? | No. It comes from the simulated status feed and shows how exclusions produce "99%". The only real availability figure is the inferred 97.05%. |
| How do you know you got all the data? | Checksum and size for every file, `total_results` for the registry, `total_records` per month for the API, and a manifest row count. Demo: `--chaos bad_checksum`. |
| Did operations cause the rise from 77.7% to 86.4%? | Unknown. 42 of 88 chargers were commissioned mid-window, so part of the rise is a mix effect. |
| What if a column is renamed or reordered? | A missing column fails the schema gate. A reordered or renamed header in any file also fails (`sessions.header_consistency`). Columns are never re-mapped by guesswork. |
| Why sites by distance, not address? | The registry spells three sites two ways. Within-site distances are ≤ 33 m and the next site is 17 km away, so any threshold in between gives 40 sites. |
| Why no machine learning? | The system records no failure label or cause, and a model cannot learn a label the system cannot define. |
| What did you get wrong? | The corrections log (C1–C18) lists every mistake, e.g. grouping visits by an owner name instead of a site (C1) and overstating how often drivers switch port (C14 — it is 27.2%). |
