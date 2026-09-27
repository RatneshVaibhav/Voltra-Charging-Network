# Voltra Charging Network — Charging Reliability Data Pipeline

> **"Our fast chargers report 99% uptime — so why do 1 in 6 drivers fail on their first try?"**

FDE Data Foundations Assignment (Classes 4–8), Track C. A dependable monthly pipeline that turns fragmented
charging-network data into a trustworthy measure of driver-experienced reliability.

**Status:** 🚧 Phase 1 of 7 complete (decisions locked). This README will be completed in Phase 7.

## The problem (short)
First-time charge success across 88 DC fast chargers at 43 sites was **83.8%** over 13 months and **86.0%** in the most
recent quarter. One in five attempts delivered no usable energy, yet **no session carried an error code**, and 29.7% of
failed attempts died before a port was recorded. The operator's dashboard reports 99% uptime.

**Decision this supports:** which sites need crews now, and what the operator must start recording before it can fix the rest.

## Where to look
- `WORKFLOW.md` — how phases are applied, reviewed and committed
- `CLAUDE.md` — core project context (auto-loaded by Claude Code); deeper layers in `docs/agent/` and `.claude/`
- `docs/decisions_log.md` — every decision with evidence, alternatives, and self-corrections
- `docs/research_sources.md` — cited research
- `config/kpi_definitions.json` — versioned business definitions (KPI, thresholds, visit rule)

## Data provenance
- **Real:** charging-session exports from the public Hugging Face dataset
  [`shadenn/EV_Charging_demand`](https://huggingface.co/datasets/shadenn/EV_Charging_demand) (CC-BY-4.0; ChargePoint
  sessions, Tennessee and neighbouring states, Jan 2024–Jan 2025), and the US DOE AFDC station registry API.
- **Simulated (clearly labelled):** a charger status feed and a maintenance work-order system, anchored to signals
  inferred from the real data. They never feed the headline KPI.
- **Voltra Charging Network is a fictional persona.** Results are not attributed to any named real operator.
