"""Voltra charging-reliability pipeline — one command, raw inputs to published metrics.

    python run_pipeline.py                         # live sources (HF files + AFDC API) + local S1/S2
    python run_pipeline.py --offline               # same flow from the committed source snapshot
    python run_pipeline.py --run-date 2025-02-01   # logical run date (reporting month = previous month)
    python run_pipeline.py --offline --chaos missing_column|duplicate_rows|stale_data|api_outage|bad_checksum

Stages: EXTRACT -> VALIDATE(retrieval+schema) -> CLEAN -> VALIDATE(content) -> TRANSFORM -> VALIDATE(model)
        -> METRICS -> SAVE (atomic partition). Exit codes: 0 success · 2 validation gate stopped (nothing published)
        · 1 unexpected/retrieval failure.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from pipeline import clean, extract, inference, metrics as metrics_mod, save, transform, validate
from pipeline.config import (LOG_DIR, PROCESSED_DIR, PROJECT_ROOT, RAW_DIR, SIM_DIR, SNAPSHOT_DIR, Settings,
                             load_kpi_definitions)
from pipeline.logging_utils import build_logger

CHAOS = ["none", "missing_column", "duplicate_rows", "stale_data", "api_outage", "bad_checksum"]


def healthy(url: str, timeout: float = 1.0) -> bool:
    try:
        return requests.get(f"{url}/health", timeout=timeout).status_code == 200
    except requests.RequestException:
        return False


def start_mock_api(settings: Settings, logger, outage: bool):
    """Start the simulated status feed locally (a fresh process per run so its retry behaviour is exercised)."""
    if not (SIM_DIR / "status_events.json.gz").exists():
        raise FileNotFoundError("Simulated systems missing — run: python -m simulate.build_client_systems")
    port = settings.status_api_url.rsplit(":", 1)[-1]
    if healthy(settings.status_api_url):
        raise RuntimeError(f"Port {port} already serves an API; stop it or set START_MOCK_API=false and reuse it")
    env = dict(os.environ, MOCK_API_PORT=port, MOCK_API_OUTAGE="1" if outage else "0")
    proc = subprocess.Popen([sys.executable, str(PROJECT_ROOT / "simulate" / "mock_status_api.py")], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 30
    while time.time() < deadline:
        if healthy(settings.status_api_url):
            logger.info("SETUP | mock status API healthy at %s (outage=%s)", settings.status_api_url, outage)
            return proc
        time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("Mock status API did not become healthy within 30 s")


def run(run_date: pd.Timestamp, offline: bool, chaos: str) -> int:
    settings = Settings.from_env()
    if chaos == "api_outage":
        settings = dataclasses.replace(settings, max_retries=3, retry_base_seconds=0.2)
    defs = load_kpi_definitions()
    rd = str(run_date.date())
    logger = build_logger(LOG_DIR / f"pipeline_{rd}.log", settings.log_level)
    logger.info("START | run_date=%s offline=%s chaos=%s definitions=v%s", rd, offline, chaos, defs["version"])
    results: list[validate.CheckResult] = []
    api = None
    try:
        if settings.start_mock_api:
            api = start_mock_api(settings, logger, outage=chaos == "api_outage")
        raw = RAW_DIR / f"run_date={rd}"
        # ---------------- EXTRACT
        files, ev_r1 = extract.extract_sessions(settings, raw, SNAPSHOT_DIR, offline, logger,
                                                corrupt_one_file=chaos == "bad_checksum")
        stations, ev_r2 = extract.extract_afdc(settings, raw, SNAPSHOT_DIR, offline, logger)
        sessions_raw, parse_stats = clean.parse_session_files(files, logger)
        if chaos == "missing_column":
            logger.warning("CHAOS | missing_column: dropping energy_kwh to simulate an upstream schema change")
            sessions_raw = sessions_raw.drop(columns=["energy_kwh"])
        months = [str(p) for p in pd.period_range(pd.to_datetime(sessions_raw["session_start"].min()).strftime("%Y-%m"),
                                                  (run_date - pd.Timedelta(days=1)).strftime("%Y-%m"), freq="M")]
        status_events, ev_s1 = extract.extract_status_events(settings, raw, months, logger)
        work_orders, ev_s2 = extract.extract_work_orders(SIM_DIR / "sim_cmms.db", raw, logger)
        evidence = [ev_r1, ev_r2, ev_s1, ev_s2]
        # ---------------- VALIDATE 1: retrieval + raw schema + simulation labels
        results += validate.check_retrieval(evidence)
        results += validate.check_raw_sessions(sessions_raw, parse_stats, defs)
        results += validate.check_simulated_sources(status_events, work_orders)
        validate.gate(results, "retrieval/schema gate", logger)
        # ---------------- CLEAN
        if chaos == "duplicate_rows":
            logger.warning("CHAOS | duplicate_rows: re-appending 50 exact copies of existing rows")
            sessions_raw = pd.concat([sessions_raw, sessions_raw.sample(50, random_state=1)], ignore_index=True)
        sessions, clean_stats = clean.standardise_sessions(sessions_raw, logger)
        if chaos == "stale_data":
            logger.warning("CHAOS | stale_data: shifting all session timestamps 120 days into the past")
            sessions[["session_start", "session_end"]] -= pd.Timedelta(days=120)
        # ---------------- VALIDATE 2: content
        today = pd.Timestamp.now(tz="UTC")
        since = len(results)
        results += validate.check_sessions(sessions, clean_stats, defs, run_date, today)
        validate.gate(results, "content gate", logger, since)
        # ---------------- TRANSFORM
        dc = transform.classify_dc_chargers(sessions, defs, logger)
        dc_sessions = sessions[sessions["charger_id"].isin(dc)]
        sites, chargers, site_diag = transform.resolve_sites(dc_sessions, stations, defs, logger)
        attempts = transform.build_attempts(sessions, dc, chargers, defs, logger)
        v = defs["visit"]
        attempts, visits = transform.build_visits(attempts, grouping_key=v["grouping_key"],
                                                  min_gap=v["min_gap_minutes"], max_gap=v["max_gap_minutes"])
        outages, charger_stats = inference.infer_outages(attempts, defs)
        open_runs = inference.open_runs_at_data_end(attempts, defs)
        logger.info("TRANSFORM | visits=%s inferred outage windows=%s silent chargers=%s open at data end=%s %s",
                    len(visits), len(outages), int(charger_stats["silent_charger"].sum()), len(open_runs),
                    open_runs[["site_id", "charger_id"]].values.tolist())
        # ---------------- VALIDATE 3: model
        brief = json.loads((SIM_DIR / "client_brief.json").read_text())
        snapshot_label = ev_r2.details.get("snapshot_taken_utc", "live")
        since = len(results)
        results += validate.check_model(attempts, visits, site_diag, len(dc_sessions), snapshot_label,
                                        sessions["session_start"].max(), brief,
                                        r1_columns=list(sessions.columns), r1_session_ids=set(sessions["session_id"]),
                                        open_runs=open_runs)
        # ---------------- METRICS
        out = metrics_mod.compute_metrics(attempts, visits, sites, charger_stats, outages, open_runs, status_events,
                                          work_orders, defs, run_date,
                                          blank_port_rows=int((sessions["port_id"] == "").sum()))
        m = out["metrics"]
        results.append(validate.check_dashboard(m["illustrative_simulated_input"]["reliability_definitions"]["operator_noc_uptime_pct"],
                                                ev_s1.details["operator_dashboard"]["network_uptime_pct"], defs))
        validate.gate(results, "model gate", logger, since)
        m["validation_summary"] = pd.Series([r.status for r in results]).value_counts().to_dict()
        # ---------------- SAVE
        charger_out = chargers.merge(charger_stats.drop(columns=["site_id"]), on="charger_id", how="left",
                                     validate="one_to_one")
        charger_out["open_run_at_data_end"] = charger_out["charger_id"].isin(open_runs["charger_id"])
        attempt_cols = ["session_id", "visit_id", "attempt_no", "site_id", "charger_id", "port_key", "is_unbound",
                        "session_start", "session_end", "duration_min", "energy_kwh", "peak_power_kw", "is_success",
                        "gap_to_prev_min", "payment_method", "evse_name", "source_file"]
        manifest = {"run_date": rd, "offline": offline, "chaos": chaos, "definitions_version": defs["version"],
                    "started_utc": str(today), "sources": [dataclasses.asdict(e) for e in evidence],
                    "parse_stats": parse_stats, "clean_stats": clean_stats, "site_resolution": site_diag}
        outputs = {
            "metrics.json": m, "evidence_table.md": metrics_mod.evidence_table(m, out["sensitivity"]),
            "validation_report.json": [r.as_dict() for r in results], "run_manifest.json": manifest,
            "site_scorecard.csv": out["scorecard"], "monthly_kpi.csv": out["monthly"], "sensitivity.csv": out["sensitivity"],
            "sites.csv": sites, "chargers.csv": charger_out, "outage_windows_inferred.csv": outages,
            "open_outages_at_data_end.csv": open_runs,
            "visits.csv": visits, "attempts.csv": attempts[attempt_cols],
        }
        target = save.publish_partition(PROCESSED_DIR, rd, outputs, logger)
        logger.info("DONE | published=%s FTCS baseline=%s%% 13m=%s%% validation=%s", target,
                    m["kpi"]["baseline_ftcs_pct"], m["kpi"]["ftcs_13_month_pct"], m["validation_summary"])
        print("\nPIPELINE SUCCESS")
        print(json.dumps({"kpi": m["kpi"], "validation": m["validation_summary"], "output": str(target)}, indent=2))
        return 0
    except validate.ValidationError as exc:
        (LOG_DIR / f"validation_{rd}.json").write_text(json.dumps([r.as_dict() for r in results], indent=2))
        logger.error("GATE | pipeline stopped | %s | no processed output published | see logs/validation_%s.json", exc, rd)
        print(f"\nPIPELINE STOPPED AT VALIDATION GATE (exit 2): {exc}")
        return 2
    except extract.RetrievalError as exc:
        logger.error("EXTRACT | retrieval failed | %s | no processed output published", exc)
        print(f"\nPIPELINE FAILED — retrieval (exit 1): {exc}\nTip: rerun with --offline to use the committed snapshot.")
        return 1
    except Exception as exc:  # noqa: BLE001 — top-level boundary: log with traceback and exit 1
        logger.exception("FAILED | unexpected error | %s", exc)
        print(f"\nPIPELINE FAILED (exit 1): {exc}")
        return 1
    finally:
        if api is not None:
            api.terminate()
            try:
                api.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api.kill()


def main() -> int:
    p = argparse.ArgumentParser(description="Voltra charging-reliability pipeline")
    p.add_argument("--run-date", default="2025-02-01", help="logical run date YYYY-MM-DD (reporting month = previous month)")
    p.add_argument("--offline", action="store_true", help="read R1/R2 from the committed source snapshot")
    p.add_argument("--chaos", default="none", choices=CHAOS, help="controlled failure demo")
    a = p.parse_args()
    try:
        run_date = pd.Timestamp(date.fromisoformat(a.run_date), tz="UTC")
    except ValueError:
        raise SystemExit("--run-date must be YYYY-MM-DD")
    return run(run_date, a.offline, a.chaos)


if __name__ == "__main__":
    raise SystemExit(main())
