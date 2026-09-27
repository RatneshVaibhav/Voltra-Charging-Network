"""Build the two SIMULATED client systems from the REAL data (run once; deterministic, seeded).

  S1 status feed   -> data/simulated_client_systems/status_events.json.gz   (served by mock_status_api.py)
  S2 work orders   -> data/simulated_client_systems/sim_cmms.db             (SQLite, read with SQL)

Real anchors: every status lifecycle event comes from a real session; every Faulted/Unavailable period and every
corrective work order comes from a real INFERRED outage window. Invented attributes (fault codes, outage categories,
detection lag, repair actions, PM dates) are listed in simulate/SIMULATION_SPEC.md. Run:

    python -m simulate.build_client_systems
"""
from __future__ import annotations

import gzip
import json
import logging
import random
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.clean import parse_session_files, standardise_sessions  # noqa: E402
from pipeline.config import SIM_DIR, SNAPSHOT_DIR, load_kpi_definitions  # noqa: E402
from pipeline.inference import infer_outages  # noqa: E402
from pipeline.transform import build_attempts, build_visits, classify_dc_chargers, resolve_sites  # noqa: E402

SPEC_VERSION = "1.0.0"
AWAITING_PARTS_HOURS = 168          # assumption: outages longer than 7 days are logged by the NOC as "awaiting parts"
MAINTENANCE_SHARE = 0.15            # assumption: share of shorter outages the NOC logs as scheduled maintenance
FAULT_CODES = [("InternalError", .30), ("EVCommunicationError", .25), ("PowerSwitchFailure", .15),
               ("GroundFailure", .10), ("OverCurrentFailure", .10), ("OtherError", .10)]
FAULT_ACTIONS = [("remote_reset", .35), ("connector_replace", .20), ("power_module_replace", .20),
                 ("firmware_update", .15), ("no_fault_found", .10)]


def _pick(rng: random.Random, weighted):
    r, acc = rng.random(), 0.0
    for value, w in weighted:
        acc += w
        if r <= acc:
            return value
    return weighted[-1][0]


def _iso(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def main(seed: int = 42) -> dict:
    log = logging.getLogger("simulate")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    defs = load_kpi_definitions()
    rng = random.Random(seed)
    files = sorted((SNAPSHOT_DIR / "sessions").glob("Se_*.csv"))
    sessions, _ = parse_session_files(files, log)
    sessions, _ = standardise_sessions(sessions, log)
    stations = json.loads((SNAPSHOT_DIR / "afdc_stations_snapshot.json").read_text())["fuel_stations"]
    dc = classify_dc_chargers(sessions, defs, log)
    _, chargers, _ = resolve_sites(sessions[sessions["charger_id"].isin(dc)], stations, defs, log)
    attempts = build_attempts(sessions, dc, chargers, defs, log)
    v = defs["visit"]
    attempts, _ = build_visits(attempts, grouping_key=v["grouping_key"], min_gap=v["min_gap_minutes"],
                               max_gap=v["max_gap_minutes"])
    outages, charger_stats = infer_outages(attempts, defs)
    port_of = (attempts[~attempts["is_unbound"]].groupby("charger_id")["port_id"]
               .agg(lambda s: s.value_counts().index[0]))

    # ---- outage categories (assumption, see SIMULATION_SPEC.md)
    cats = []
    for _, w in outages.iterrows():
        if w["hours"] > AWAITING_PARTS_HOURS:
            cats.append(("awaiting_parts", "Unavailable", "NoError", "AwaitingParts"))
        elif rng.random() < MAINTENANCE_SHARE:
            cats.append(("scheduled_maintenance", "Unavailable", "NoError", "ScheduledMaintenance"))
        else:
            cats.append(("fault", "Faulted", _pick(rng, FAULT_CODES), ""))
    outages = outages.assign(category=[c[0] for c in cats], status=[c[1] for c in cats],
                             error_code=[c[2] for c in cats], info=[c[3] for c in cats])

    # ---- S1 events
    # While a charger is inside an (inferred) outage window its connector stays Faulted/Unavailable: attempts made
    # during the window still exist as sessions in the CPMS (R1), but emit no lifecycle status events here.
    windows_by_charger = {c: list(zip(g["start"], g["end"])) for c, g in outages.groupby("charger_id")}

    def in_outage(charger_id, ts):
        return any(s <= ts <= e for s, e in windows_by_charger.get(charger_id, []))

    events, suppressed = [], 0
    for a in attempts[~attempts["is_unbound"]].sort_values(["port_key", "session_start"]).itertuples():
        if in_outage(a.charger_id, a.session_start):
            suppressed += 1
            continue
        base = {"charger_id": a.charger_id, "port_id": a.port_id, "data_origin": "simulated",
                "anchor": f"real_session:{a.session_id}"}
        events.append({**base, "timestamp": _iso(a.session_start), "status": "Preparing", "error_code": "NoError", "info": ""})
        if a.is_success:
            events.append({**base, "timestamp": _iso(a.session_start + pd.Timedelta(seconds=30)), "status": "Charging",
                           "error_code": "NoError", "info": ""})
            events.append({**base, "timestamp": _iso(a.session_end), "status": "Finishing", "error_code": "NoError", "info": ""})
        # failed attempts return straight to Available with NoError: mirrors the real, always-blank session_error
        events.append({**base, "timestamp": _iso(a.session_end + pd.Timedelta(seconds=5)), "status": "Available",
                       "error_code": "NoError", "info": ""})
    for w in outages.itertuples():
        base = {"charger_id": w.charger_id, "port_id": port_of.get(w.charger_id, ""), "data_origin": "simulated",
                "anchor": f"inferred_outage:{w.outage_id}"}
        # the window opens at the end of the charger's last successful session; that session's own Available event
        # is emitted 5 s later, so the outage status is placed 10 s after the window start to keep order correct
        events.append({**base, "timestamp": _iso(w.start + pd.Timedelta(seconds=10)), "status": w.status,
                       "error_code": w.error_code, "info": w.info})
        events.append({**base, "timestamp": _iso(w.end), "status": "Available", "error_code": "NoError", "info": "Restored"})

    # ---- S2 work orders: corrective (one per inferred outage) + quarterly preventive maintenance
    work_orders = []
    for w in outages.itertuples():
        if w.category == "scheduled_maintenance":
            opened, trigger, action = w.start, "scheduled_pm", "preventive_maintenance"
        else:
            max_lag = max(min(48.0 if w.category == "awaiting_parts" else 24.0, w.hours * 0.5), 0.5)
            opened = w.start + pd.Timedelta(hours=rng.uniform(0.5, max_lag))
            trigger = "fault_alarm"
            action = rng.choice(["power_module_replace", "cable_replace"]) if w.category == "awaiting_parts" \
                else _pick(rng, FAULT_ACTIONS)
        work_orders.append({"charger_id": w.charger_id, "work_type": "corrective" if trigger == "fault_alarm" else "planned",
                            "trigger": trigger, "opened_at": _iso(opened), "closed_at": _iso(w.end), "action": action,
                            "resolution_code": "NFF" if action == "no_fault_found" else "RESOLVED",
                            "linked_outage_id": w.outage_id})
    for c in charger_stats.itertuples():
        for q in pd.period_range(c.first_seen.tz_convert(None), c.last_seen.tz_convert(None), freq="Q"):
            start = max(q.start_time.tz_localize("UTC"), c.first_seen)
            end = min(q.end_time.tz_localize("UTC"), c.last_seen)
            if (end - start).days < 20:
                continue
            day = start + pd.Timedelta(days=rng.randint(3, (end - start).days - 3), hours=rng.randint(8, 15))
            dur = pd.Timedelta(minutes=rng.choice([60, 90, 120]))
            work_orders.append({"charger_id": c.charger_id, "work_type": "planned", "trigger": "scheduled_pm",
                                "opened_at": _iso(day), "closed_at": _iso(day + dur), "action": "preventive_maintenance",
                                "resolution_code": "RESOLVED", "linked_outage_id": None})
            base = {"charger_id": c.charger_id, "port_id": port_of.get(c.charger_id, ""), "data_origin": "simulated",
                    "anchor": "planned_pm"}
            events.append({**base, "timestamp": _iso(day), "status": "Unavailable", "error_code": "NoError",
                           "info": "ScheduledMaintenance"})
            events.append({**base, "timestamp": _iso(day + dur), "status": "Available", "error_code": "NoError",
                           "info": "Restored"})

    events.sort(key=lambda e: (e["timestamp"], e["charger_id"], e["status"]))
    for i, e in enumerate(events, 1):
        e["event_id"] = f"EV-{i:07d}"
    wo = pd.DataFrame(work_orders).sort_values(["opened_at", "charger_id"]).reset_index(drop=True)
    wo.insert(0, "work_order_id", [f"WO-{i + 1:05d}" for i in range(len(wo))])
    wo["data_origin"] = "simulated"

    SIM_DIR.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(SIM_DIR / "status_events.json.gz", "wb", mtime=0) as fh:   # mtime=0 -> byte-identical reruns
        fh.write(json.dumps(events, separators=(",", ":")).encode())
    db = SIM_DIR / "sim_cmms.db"
    db.unlink(missing_ok=True)
    with sqlite3.connect(db) as con:
        wo.to_sql("work_orders", con, index=False)
        pd.DataFrame([{"key": "work_orders_rows", "value": str(len(wo))}, {"key": "seed", "value": str(seed)},
                      {"key": "spec_version", "value": SPEC_VERSION}, {"key": "data_origin", "value": "simulated"}]
                     ).to_sql("generation_manifest", con, index=False)
    by_month = pd.Series([e["timestamp"][:7] for e in events]).value_counts().sort_index().to_dict()
    manifest = {"spec_version": SPEC_VERSION, "seed": seed, "data_origin": "simulated",
                "status_events": len(events), "status_events_by_month": by_month, "work_orders": len(wo),
                "inferred_outage_windows": int(len(outages)),
                "attempt_events_suppressed_inside_outages": suppressed,
                "outage_categories": outages["category"].value_counts().to_dict(),
                "parameters": {"awaiting_parts_hours": AWAITING_PARTS_HOURS, "maintenance_share": MAINTENANCE_SHARE,
                               "fault_codes": FAULT_CODES, "fault_actions": FAULT_ACTIONS}}
    (SIM_DIR / "simulation_manifest.json").write_text(json.dumps(manifest, indent=2))
    log.info("SIMULATE | status_events=%s work_orders=%s outages=%s categories=%s", len(events), len(wo),
             len(outages), manifest["outage_categories"])
    return manifest


if __name__ == "__main__":
    main()
