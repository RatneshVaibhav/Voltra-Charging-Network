---
paths:
  - "docs/**/*.md"
  - "README.md"
  - "notebooks/**"
  - "reviews/**"
---
# Documentation & evidence rules

- Every number in docs must be produced by code in this repo (cite the script/output) or by a cited source.
- Evidence language: "the data shows…", "is associated with…", "we cannot determine…", "we would need X before concluding Y".
  Never claim causation from association.
- State the grain and definition next to every metric (e.g., "FTCS (visit grain, <1 kWh = fail, 5-min site window)").
- Always show sensitivity for definition-dependent metrics (failed-visit rate 5.0–7.6%).
- Separate **real-data metrics** from **illustrative (simulated input)** metrics in every table.
- Known / Unknown / Assumption / Limitation sections must be concrete and each item traceable to evidence.
- Do not name a real operator as the client or attribute failure rates to named utilities. Use site codes S01–S43.
- Keep the corrections log (C1–C6) visible — it is evidence of judgement, not an embarrassment.
