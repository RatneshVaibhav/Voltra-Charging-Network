# Domain Primer — EV fast charging (what a reviewer must know to judge correctness)

Items marked **[fact]** come from standards/regulation/research cited in `docs/research_sources.md`.
Items marked **[hypothesis]** are plausible explanations we have **not** verified — never present them as findings.

## 1. Hardware hierarchy
- **Site** (physical location) → **charger / EVSE** (one cabinet/dispenser) → **port** (serves one vehicle at a time)
  → **connector** (plug type: CCS, CHAdeMO, NACS). [fact]
- In our data: 88 DC chargers, each with 1 identified DC port; 40 sites; many sites have 2–4 chargers.
- Driver experience is measured per **visit** (site-level), reliability per **charger/port**.

## 2. How a DC fast-charging session works (and where it fails)
1. **Arrive & select** a charger. *Failure: blocked bay, charger dark/offline, broken screen.*
2. **Authorise** — membership card/app, credit-card terminal, roaming. *Failure: payment/auth errors.*
3. **Plug in** → vehicle and charger establish **digital communication** over the charging cable (DIN SPEC 70121 /
   ISO 15118 for CCS). *Failure: communication/handshake errors — the most prevalent cause of persistent failures in the
   UC Davis study* [fact]. Causes include dirty/damaged pins, misaligned connector, interoperability gaps.
4. **Safety checks** (insulation/cable check, pre-charge). *Failure: safety faults, emergency stops.*
5. **Energy transfer** — power ramps to what the battery accepts. *Failure: interruption, throttled power.*
6. **Stop** — driver stops, battery full, or fault. Record written (energy, times, stop reason).

A session that ends with **~0 kWh** means the flow broke somewhere in steps 2–4 (or the driver aborted, or the vehicle
refused). **Which step is unknown in our data** because `session_error` is never populated. [fact about our data]

**Port-less (unbound) sessions** — 2,187 rows with blank `port_id`, 99.9% zero energy, median 2 min, all on DC chargers.
[hypothesis] the session record was created at charger level (e.g., authorisation) but never bound to a port because the
plug-in/handshake never completed. Treat as failed attempts; say "we cannot determine the exact stage".

## 3. OCPP (Open Charge Point Protocol) essentials — used to design the simulated status feed (S1)
- Charger ↔ back-office protocol. Key messages: `BootNotification`, `Heartbeat`, `StatusNotification`, `Authorize`,
  `StartTransaction`, `MeterValues`, `StopTransaction` (OCPP 1.6). [fact]
- **Connector status values (1.6):** `Available`, `Preparing`, `Charging`, `SuspendedEVSE`, `SuspendedEV`, `Finishing`,
  `Reserved`, `Unavailable`, `Faulted`. [fact]
- **Error codes (1.6):** `NoError`, `ConnectorLockFailure`, `EVCommunicationError`, `GroundFailure`, `HighTemperature`,
  `InternalError`, `LocalListConflict`, `OtherError`, `OverCurrentFailure`, `OverVoltage`, `PowerMeterFailure`,
  `PowerSwitchFailure`, `ReaderFailure`, `ResetFailure`, `UnderVoltage`, `WeakSignal`. [fact]
- **Key insight for this project:** a failed handshake often returns the connector to `Available` without ever entering
  `Faulted`. Time-based uptime (online and not Faulted) therefore stays high while drivers fail — UC Davis calls these
  **"point errors"**: failures while online, invisible to uptime. [fact: concept; S1 behaviour is simulated]
- ChargeX KPIs (charge start success, session success) are defined on OCPP message logs; we only have session exports,
  so we approximate at session/visit level. [fact → limitation]

## 4. Three competing definitions of "reliability" (the organisational conflict)
| Definition | Who uses it | What it counts | Our value |
|---|---|---|---|
| **Operator uptime** | VP Ops / NOC dashboard | Time online and not `Faulted`, excluding maintenance & utility outages | "99%" (client claim; reproduced by simulated S1) |
| **Federal (NEVI, 23 CFR 680.116)** | Grants & Compliance | Up only if online **and dispensing electricity**; >97% annual; excludes vehicle-caused failures, utility outages, scheduled maintenance, vandalism, disasters | ~97% (real-data outage inference: 97.05%) |
| **Driver experience (FTCS)** | Customer Experience | Visits where the first attempt delivered ≥1 kWh | **83.87%** (13 mo) / **86.03%** (last quarter) — real data |

The **gap between these numbers is the finding**. No KPI owner is documented → organisational validation issue (Class 6).

## 5. Reporting standards
- **EV-ChART** (federal reporting format): Module 2 sessions (incl. `session_error`, `energy_kwh`, `peak_power_kw`,
  payment), Module 3 uptime, Module 4 outages. Our session columns match Module 2 style — so a blank `session_error`
  is a **reporting gap** against the format's intent, not merely missing data. [fact about format; inference about intent]

## 6. Industry context (2026)
- J.D. Power 2026: 12% of public charging visits end without charging (record low; 14% in 2025, 19% in 2024). [fact]
- Paren Q2 2026: national DCFC reliability index 93.8%; most states 90–95%; laggards ~78%. [fact]
- UC Davis (California corridor DCFCs, 2019–22): 83% and 77% generally successful visits on two networks; station range
  13–95%; 8–9% troubled success. [fact] — our 10.4% troubled success is in the same ballpark.
- Bay Area field study: 72.5% of connectors functional vs 95–98% operator-reported uptime. [fact]

## 7. Things that look like bugs but are correct here
- Peak power 0 kW on failed attempts → why DC classification is **per charger**, not per port.
- Many sites have one AFDC record per charger → site = **address cluster**, not AFDC id.
- 42 of 88 chargers start mid-window → network build-out, not missing data.
- Visit gap tolerance of −2 min → absorbs small overlaps/clock skew between consecutive sessions.

## 8. Things that ARE bugs here
- Dropping blank `port_id` rows; site = organisation prefix; thresholds read from env; simulated fields in FTCS;
  reporting FTCS without the visit definition; using the 2026 registry status as evidence about 2024 availability.
