# Simulation Specification (D4) — v1.0.0, seed 42

S1 and S2 stand in for client systems that exist at every charging operator but are not public. They are generated
by `python -m simulate.build_client_systems` from the committed real snapshot and are **byte-identical on rerun**.
Every record carries `data_origin = "simulated"`. Nothing simulated feeds the KPI (enforced by
`model.no_simulated_fields_in_kpi_inputs`).

| Rule | Basis |
|---|---|
| One S1 lifecycle per real non-unbound session: `Preparing` → (`Charging` → `Finishing` if ≥ 1 kWh) → `Available` | **Real anchor** (R1 session times and energy) |
| Failed real attempts return to `Available` with `NoError` | **Real anchor** — mirrors the real, always-blank `session_error` |
| Unbound attempts emit no port status | **Real anchor** — no port was recorded |
| Outage periods = the 46 statistically inferred windows (`pipeline/inference.py`) | **Real anchor** (inferred from R1) |
| Attempts made during an outage window emit no status events (connector stays Faulted/Unavailable) | Assumption (realism) — 326 attempt lifecycles suppressed |
| Outage status placed 10 s after the window start | Assumption (ordering) |
| Outages > 7 days are logged by the NOC as `Unavailable / AwaitingParts` | **Assumption** |
| 15% of shorter outages are logged as `Unavailable / ScheduledMaintenance` (seeded) | **Assumption** |
| Other outages are `Faulted` with an OCPP 1.6 error code: InternalError 30%, EVCommunicationError 25%, PowerSwitchFailure 15%, GroundFailure 10%, OverCurrentFailure 10%, OtherError 10% | **Assumption** (codes are real OCPP 1.6 values; the mix is invented) |
| Operator dashboard = time not `Faulted`; all `Unavailable` time excluded → 99.77% | Assumption (models how the "99%" claim can arise) |
| One corrective work order per non-maintenance outage; opened after a seeded detection lag (0.5–24 h, 0.5–48 h for awaiting parts, never more than half the window); closed at the window end | Window timing = **real anchor**; lag = **assumption** |
| Repair action mix: remote reset 35%, connector 20%, power module 20%, firmware 15%, no fault found 10% | **Assumption** |
| Quarterly preventive maintenance (60–120 min, weekday daytime) per charger quarter ≥ 20 days, also emitted to S1 as `Unavailable / ScheduledMaintenance` | **Assumption** |
| Mock API: first request for page 3 → HTTP 500, first request for page 5 → HTTP 429 (`retry_after_seconds: 1`); `MOCK_API_OUTAGE=1` → every request 503 | Assumption (retrieval realism, FlashEats pattern) |

**Consequence to state honestly:** silent chargers get no corrective work orders *because* the simulated process only
dispatches on alarms and no outage was inferred for them. This follows from the assumed alarm-driven process plus the
real inference — it must be checked against a real CMMS before it is presented as a finding.
