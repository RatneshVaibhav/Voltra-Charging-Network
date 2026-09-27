---
paths:
  - "simulate/**"
  - "data/simulated_client_systems/**"
---
# Simulation rules (D4)

- Simulate **only** S1 (charger status feed) and S2 (work orders). No simulated support tickets or sessions.
- Anchor every simulated event to a real signal: S1 lifecycle events derive from real sessions; Faulted/Unavailable periods
  come only from the 46 real inferred outage windows; S2 corrective orders map 1:1 to those windows (+ quarterly PM).
- Invented attributes are limited to: fault codes, counted-vs-excluded outage category, detection lag, trigger, repair
  action, resolution code. Each must be listed in `simulate/SIMULATION_SPEC.md` as **assumption**; everything else as
  **real anchor**.
- Seeded (`SIM_SEED`, default 42) and deterministic; regenerate byte-identically.
- Every record carries `data_origin = "simulated"`. Output only under `data/simulated_client_systems/`.
- A failed real attempt must appear in S1 as `Preparing → Available` with `NoError` (mirrors the real blank `session_error`).
  Never add a Faulted status to a failed attempt unless it lies inside an inferred outage window.
- Do not tune simulation parameters to make a finding look stronger. If a parameter changes a headline, log it in
  `docs/decisions_log.md`.
- Mock API mirrors the FlashEats pattern: `/health`, paginated list endpoint with `page`, `page_size`, `has_more`,
  `total_records`, `month=YYYY-MM` filter; first hit of one page returns HTTP 500, first hit of another returns HTTP 429
  with `retry_after_seconds`.
