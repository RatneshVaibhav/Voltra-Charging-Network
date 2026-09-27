# Demo script (about 4½ minutes) — one FDE judgement call, shown on the GitHub repo

**The judgement call:** 2,187 charging attempts with no port id were **kept as failed attempts** instead of being
dropped as "bad rows". Dropping them would have shown the client 90.33% — their stretch target — with no repair at all.

## Before you record (5 minutes)
1. Terminal: `cd Voltra-Charging-Network && source .venv/bin/activate`, run `python run_pipeline.py --offline` once
   (so the outputs exist), then `clear`. Make the font large (≥ 16 pt). If `python` is not found, use `python3`.
2. Browser tabs, in this order:
   - (a) the repo's README on GitHub, scrolled to the top
   - (b) `docs/decisions_log.md`, jumped to **D2**
   - (c) `docs/evidence.md`
3. Keep this script on a second screen. Speak slowly: ~600 words is about 4½ minutes.

---

## 0:00 – 0:25 · The problem
**Screen:** tab (a), README top: the headline and the "At a glance" table.

> "Voltra's operator dashboard says its fast chargers have 99% uptime. Drivers say the chargers don't work. I built a
> pipeline on 46,575 real charging sessions to measure what drivers actually experience. The answer: first-time charge
> success is 86% — one in seven drivers fail on their first try."

## 0:25 – 1:00 · Where the truth lives
**Screen:** scroll to README §5, *Data sources and where the truth lives*.

> "Four sources. Two are real: the session exports and the US Department of Energy station registry. Two are simulated
> stand-ins for systems no operator publishes, and they are labelled and never touch the KPI. For 'did the driver get a
> charge?', the system of record is the metered energy on each session. It can't be the status feed, because a failed
> attempt simply returns the charger to 'Available'. That's exactly why the uptime number looks so good."

## 1:00 – 2:30 · The judgement call ← the heart of the demo
**Screen:** README §4. Point at the first table, row by row.

> "Here is the call I want to walk you through. 2,187 rows — about 5% — have no port id. Every cleaning checklist says a
> row with a missing key is a bad row: drop it. Before touching them I checked four things. Every one is on a DC fast
> charger. 99.9% delivered exactly zero energy. The median one lasted two minutes. And the charger id is still there,
> so I know where it happened. These aren't corrupt rows — they are failed charging attempts that died before the
> charger recorded a port."

**Screen:** the second table in §4.

> "So what would dropping them do? First-time success would jump from 86.03% to 90.33%. That is the client's stretch
> target — reached on paper, with no repair at all. And 30% of all failures would simply disappear. I kept them, as
> failed attempts at their charger's site, and I label them 'unbound'."

**Screen:** switch to tab (b), D2 in the decisions log. Scroll slowly past the options table.

> "The decision is logged with every option I rejected, including my own first mistake: I initially excluded these
> rows as 'not fast chargers', which was wrong. That correction is kept visible as C2. The impact isn't a number I
> typed. The pipeline recomputes it on every run, so anyone can check it."

## 2:30 – 3:30 · Run it
**Screen:** terminal. Type `python run_pipeline.py --offline`.

> "One command runs everything: extract, three validation gates, transform, metrics, and an atomic save."

While it runs (about 10 seconds), point at each line as it appears:
- `sha1_ok=True` → "Every file is checked against the publisher's checksum, so I can prove retrieval is complete."
- `status=500 … wait` and `status=429 … wait` → "The status API fails on purpose. The pipeline retries, with a limit."
- `WARN sessions.blank_port_id n=2187 … KEPT as unbound attempts` → "And here is the judgement call, printed on every
  run: counted, logged, never silently dropped."
- `PIPELINE SUCCESS` → "86.03%, and 33 checks: 17 pass, 15 known warnings, 1 unknown — nobody owns the KPI yet."

Then type `python run_pipeline.py --offline --chaos missing_column`.

> "Now I remove the energy column, as if the vendor changed the export. The gate stops the run with exit code 2, and
> nothing is published. Demo runs write to their own folder, so they can never overwrite the real result."

## 3:30 – 4:15 · Evidence and the decision
**Screen:** tab (c), `docs/evidence.md`. Show the judgement-call table, then scroll to *Where to send crews first*.

> "The output supports one decision: where to send crews now. Five sites sit more than five points below the median.
> Lifting them to the median gets the network to 87%, the six-week target. One more site, S29, has two chargers that
> have been silent since early January. The KPI can't see that, so it's flagged for a check."

## 4:15 – 4:40 · Close
**Screen:** scroll to *Known / Unknown / Assumption / Limitation*.

> "What this data cannot tell us is *why* anything failed — no session carries an error code. So the real
> recommendation is to make the charging software record the port and an error code on every attempt. Then 90% becomes
> a target you can manage, not a number you can reach by deleting rows. Thank you."

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
