# Research Sources

Sources consulted during Phase 1 (2026-09-27), and what each one was used for.

## Data sources
| Source | Link | Used for |
|---|---|---|
| Hugging Face `shadenn/EV_Charging_demand` (CC-BY-4.0) | https://huggingface.co/datasets/shadenn/EV_Charging_demand | R1 — real session exports (Jan 2024–Jan 2025, ChargePoint, Tennessee & neighbouring states) |
| AFDC Alternative Fuel Stations API (US DOE) | https://developer.nlr.gov/docs/transportation/alt-fuel-stations-v1/ (docs historically at developer.nrel.gov) | R2 — station registry, port-id join, site addresses |
| Open Charge Map API | https://openchargemap.org/site/develop/api | Considered for driver check-ins; not used (needs key; sparse regional coverage) |

## Definitions and methodology
| Source | Link | Used for |
|---|---|---|
| Gamage, Jenn, Tal (2024). *Novel Methodology to Measure the Reliability of Public DC Fast Charging Stations.* Transportation Research Record 2678(11). Open access, CC-BY-4.0 | https://doi.org/10.1177/03611981241244798 | D2 (1 kWh screen), D3 (5-min visit window, site grouping, no-user-ID variation), outcome categories (first-time / troubled / persistent failure), "point errors" invisible to uptime; error codes alone are a poor proxy |
| ChargeX Consortium (INL, ANL, NREL) — Customer-Focused KPIs; Implementation Guide (Savargaonkar et al., Dec 2024) | https://www.osti.gov/biblio/2513383 · https://driveelectric.gov/news/kpi-ev-playbook | KPI framing (charge start success, session success); aspiration "every session successful on the first attempt" |
| ChargeX OCPP 2.0.1 Interim KPI Calculator (MIT) | https://github.com/chargex-consortium/OCPP-2.0.1-Interim-KPI-Calculator | Confirms full ChargeX KPIs need OCPP message logs (we have session exports only → limitation); shapes S1 event design |
| kwwhat — open-source OCPP analytics (MIT) | https://www.kwwhat.com | 0.1 kWh success rule; visit models (30 min authenticated / 2 min port-level unauthenticated); first-attempt / troubled / failed metrics |
| 23 CFR 680.116 (NEVI minimum uptime) | https://www.law.cornell.edu/cfr/text/23/680.116 | Federal uptime definition: "up" only if online **and** dispensing electricity; >97%; exclusions incl. vehicle-caused failures |
| EV-ChART Data Format & Preparation Guidance (DOE/Joint Office) | https://driveelectric.gov/files/ev-chart-data-guidance.pdf | Session-error field semantics; Modules 2–4 (sessions, uptime, outages); R1 column alignment |

## Industry benchmarks
| Source | Link | Used for |
|---|---|---|
| J.D. Power 2026 U.S. EVX Public Charging Study (Aug 12, 2026) | https://www.jdpower.com/business/press-releases/2026-u-s-electric-vehicle-experience-evx-public-charging-study/ | Headline context: failed visits at an all-time low of 12% (14% in 2025, 19% in 2024) |
| Paren — US EV Fast Charging Q1/Q2 2026 reports | https://www.paren.app/reports/us-ev-fast-charging-q1-2026 | National reliability index 93.8% (Q2 2026); most states 90–95%; laggards ~78%; index counts first-time plug success, retries, failed attempts |
| Rempel et al. — Reliability of Open Public EV DC Fast Chargers (Bay Area field study) | https://arxiv.org/abs/2203.16372 | 72.5% of 657 connectors functional vs 95–98% uptime reported by operators — the original uptime-vs-reality gap |
| TVA / EnergyRight — Fast Charge Network | https://energyright.com/ev/fast-charger-program | Context for the region's network build-out (inference only — not used to name the client) |

## Course material (not committed — keep in git-ignored `course/`)
FDE Sessions 1–3, Class 4 deck, Class 5 FlashEats solution, Class 6 validation notebook, Class 7 challenge,
Class 8 pipeline pack, Assignment 2 brief.
