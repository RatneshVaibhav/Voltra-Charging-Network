"""METRICS stage — KPI, the 5-metric evidence table, sensitivity, site scorecard, illustrative metrics.

Real-data metrics use only R1 sessions (+ R2 for site identity). Metrics that use the simulated S1/S2 sources are
labelled 'illustrative (simulated input)' everywhere they appear.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .transform import build_visits, success_mask, visit_summary


def pct(x, nd=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(100 * float(x), nd)


def baseline_months(visits: pd.DataFrame, n: int) -> list[str]:
    """The n most recent monthly exports present in the data (anchored to the data, not the run date)."""
    return sorted(visits["month"].unique())[-n:]


def sensitivity_table(attempts: pd.DataFrame, defs: dict) -> pd.DataFrame:
    """Every tested definition, on both grains the project reports: 13 months and the baseline quarter.
    A variant with exclude_unbound=true drops the port-less attempts — the rejected D2 alternative, kept visible."""
    base_rule, v = defs["attempt"]["success_rule"], defs["visit"]
    rows = []
    variants = [{"name": "LOCKED DEFINITION", "grouping_key": v["grouping_key"], "max_gap_minutes": v["max_gap_minutes"]}]
    for variant in variants + defs["sensitivity"]:
        a = (attempts[~attempts["is_unbound"]] if variant.get("exclude_unbound") else attempts).copy()
        a["ok"] = success_mask(a["energy_kwh"], variant.get("success_rule", base_rule))
        a2, vis = build_visits(a, grouping_key=variant["grouping_key"], min_gap=v["min_gap_minutes"],
                               max_gap=variant["max_gap_minutes"], success_col="ok")
        s = visit_summary(a2, vis, success_col="ok")
        q = vis[vis["month"].isin(baseline_months(vis, defs["kpi"]["baseline_months"]))]
        rows.append({"variant": variant["name"],
                     "changes": "population (port-less attempts removed)" if variant.get("exclude_unbound") else "definition",
                     "visits": s["visits"], "attempt_success_pct": pct(s["attempt_success_rate"]),
                     "ftcs_pct": pct(s["ftcs"]), "ftcs_baseline_pct": pct(q["first_attempt_success"].mean()),
                     "troubled_pct": pct(s["troubled_success_rate"]),
                     "failed_visit_pct": pct(s["failed_visit_rate"]), "attempts_per_visit": round(s["attempts_per_visit"], 2)})
    return pd.DataFrame(rows)


def retry_behaviour(visits: pd.DataFrame, attempts: pd.DataFrame) -> dict:
    """How drivers retry. A retry visit = first attempt failed and the driver tried again (>= 2 attempts).
    Switching is measured by charger: every DC charger here exposes one port id, and a port-less UNBOUND@charger
    attempt followed by the same charger is the same place, not a switch."""
    multi = visits[visits["attempts"] > 1]
    retry = multi[~multi["first_attempt_success"]]
    ports = attempts[~attempts["is_unbound"]].groupby("charger_id")["port_key"].nunique().value_counts()
    return {"multi_attempt_visits_pct": pct(len(multi) / len(visits)),
            "retry_visits_pct": pct(len(retry) / len(visits)),
            "retry_visits_switching_charger_pct": pct((retry["chargers_tried"] > 1).mean()),
            "multi_attempt_visits_split_by_port_grouping_pct": pct((multi["ports_tried"] > 1).mean()),
            "identified_ports_per_dc_charger": {str(k): int(n) for k, n in ports.sort_index().items()},
            "note": "the split-by-port-grouping share is why D3 rejects port-level visits (it would cut those visits "
                    "in two); it is not the share of drivers who moved — that is retry_visits_switching_charger_pct"}


def judgement_call(attempts: pd.DataFrame, visits: pd.DataFrame, base: list[str], blank_port_rows: int, defs: dict) -> dict:
    """D2 made reproducible: what the port-less attempts are, and what the KPI would read if they were dropped."""
    v, u = defs["visit"], attempts[attempts["is_unbound"]]
    _, dropped = build_visits(attempts[~attempts["is_unbound"]], grouping_key=v["grouping_key"],
                              min_gap=v["min_gap_minutes"], max_gap=v["max_gap_minutes"])
    kept_q, dropped_q = visits[visits["month"].isin(base)], dropped[dropped["month"].isin(base)]
    kept_b, drop_b = kept_q["first_attempt_success"].mean(), dropped_q["first_attempt_success"].mean()
    kept_13, drop_13 = visits["first_attempt_success"].mean(), dropped["first_attempt_success"].mean()
    stretch = defs["kpi"]["target"]["stretch_next_quarter"]
    return {"decision": "D2 — keep port-less (unbound) attempts on DC chargers as failed attempts",
            "port_less_attempts": int(len(u)), "blank_port_rows_in_export": int(blank_port_rows),
            "all_blank_port_rows_on_dc_chargers": int(len(u)) == int(blank_port_rows),
            "zero_energy_pct": pct((u["energy_kwh"] == 0).mean()),
            "median_duration_min": round(float(u["duration_min"].median()), 1),
            "share_of_failed_attempts_pct": pct(u["is_success"].eq(False).sum() / (~attempts["is_success"]).sum()),
            "ftcs_baseline_kept_pct": pct(kept_b, 2), "ftcs_baseline_if_dropped_pct": pct(drop_b, 2),
            "ftcs_13_month_kept_pct": pct(kept_13, 2), "ftcs_13_month_if_dropped_pct": pct(drop_13, 2),
            "inflation_if_dropped_pts": {"baseline_quarter": round(100 * (drop_b - kept_b), 2),
                                         "13_months": round(100 * (drop_13 - kept_13), 2)},
            "dropping_would_appear_to_meet_stretch_target": bool(drop_b >= stretch),
            "stretch_target_pct": 100 * stretch}


def site_scorecard(visits: pd.DataFrame, sites: pd.DataFrame, base: list[str], defs: dict) -> tuple[pd.DataFrame, dict]:
    rules = defs["lagging_sites"]
    q = visits[visits["month"].isin(base)]
    card = (q.groupby("site_id").agg(baseline_visits=("visit_id", "size"), baseline_ftcs=("first_attempt_success", "mean"),
                                     baseline_failed_visit_rate=("outcome", lambda s: (s == "failed_visit").mean()))
            .join(visits.groupby("site_id").agg(visits_13m=("visit_id", "size"), ftcs_13m=("first_attempt_success", "mean")),
                  how="outer"))
    card = sites.set_index("site_id")[["address", "state", "n_dc_chargers"]].join(card).reset_index()
    eligible = card[card["baseline_visits"] >= rules["min_visits"]]
    median = float(eligible["baseline_ftcs"].median())
    card["points_below_median"] = (median - card["baseline_ftcs"]) * 100
    card["lagging"] = (card["baseline_visits"] >= rules["min_visits"]) & (card["points_below_median"] > rules["points_below_median"])
    lag = card[card["lagging"]]
    net = float(q["first_attempt_success"].mean())
    lifted = (q["first_attempt_success"].sum() - (lag["baseline_visits"] * lag["baseline_ftcs"]).sum()
              + (lag["baseline_visits"] * median).sum()) / len(q)
    margin = card.loc[card["baseline_visits"] >= rules["min_visits"], "points_below_median"]
    closest = float((margin - rules["points_below_median"]).abs().min())
    summary = {"baseline_months": base, "median_site_ftcs_pct": pct(median, 3), "lagging_sites": lag.sort_values("baseline_ftcs")["site_id"].tolist(),
               "lagging_share_of_visits_pct": pct(lag["baseline_visits"].sum() / len(q)),
               "network_ftcs_baseline_pct": pct(net, 2), "projected_ftcs_if_lagging_at_median_pct": pct(lifted, 2),
               "closest_site_to_threshold_pts": round(closest, 3)}
    for col in ("baseline_ftcs", "baseline_failed_visit_rate", "ftcs_13m"):
        card[col] = (card[col] * 100).round(2)
    card["points_below_median"] = card["points_below_median"].round(3)
    return card.sort_values("site_id"), summary


def reliability_definitions(status_events: list, charger_stats: pd.DataFrame) -> dict:
    """Uptime under the operator's and a federal-style definition, recomputed from S1 events (illustrative)."""
    ev = pd.DataFrame(status_events)
    ev["ts"] = pd.to_datetime(ev["timestamp"], utc=True)
    down = {"Faulted": 0.0, "AwaitingParts": 0.0, "ScheduledMaintenance": 0.0}
    life = 0.0
    for _, g in ev.sort_values(["ts", "event_id"]).groupby("port_id"):
        life += (g["ts"].max() - g["ts"].min()).total_seconds() / 60
        state, since = None, None
        for row in g.itertuples():
            if row.status in ("Faulted", "Unavailable") and state is None:
                state = "Faulted" if row.status == "Faulted" else (row.info or "ScheduledMaintenance")
                since = row.ts
            elif row.status == "Available" and state is not None:
                down[state] = down.get(state, 0.0) + (row.ts - since).total_seconds() / 60
                state = None
    noc = 1 - down["Faulted"] / life                                           # NOC excludes all Unavailable time
    federal = 1 - (down["Faulted"] + down["AwaitingParts"]) / life             # awaiting parts is not an allowed exclusion
    inferred = charger_stats.loc[charger_stats["inference_possible"]]
    life_w = (inferred["last_seen"] - inferred["first_seen"]).dt.total_seconds()
    fleet = float((inferred["inferred_availability"] * life_w).sum() / life_w.sum())
    return {"operator_noc_uptime_pct": pct(noc, 2), "federal_style_uptime_pct": pct(federal, 2),
            "inferred_availability_real_pct": pct(fleet, 2),
            "down_minutes_by_category": {k: round(v) for k, v in down.items()}}


def repair_effect(work_orders: pd.DataFrame, attempts: pd.DataFrame, defs: dict) -> dict:
    """Charger first-attempt success in the window before a corrective work order opened vs the window after it closed
    (illustrative: work-order timing is simulated and anchored to inferred outages; outcomes are real sessions)."""
    rules = defs["repair_effect"]
    days, min_n = rules["window_days"], rules["min_first_attempts_each_side"]
    first = attempts[attempts["attempt_no"] == 1]
    rows = []
    for wo in work_orders[work_orders["work_type"] == "corrective"].itertuples():
        opened, closed = pd.Timestamp(wo.opened_at), pd.Timestamp(wo.closed_at)
        c = first[first["charger_id"] == wo.charger_id]
        before = c[(c["session_start"] < opened) & (c["session_start"] >= opened - pd.Timedelta(days=days))]["is_success"]
        after = c[(c["session_start"] > closed) & (c["session_start"] <= closed + pd.Timedelta(days=days))]["is_success"]
        if len(before) >= min_n and len(after) >= min_n:
            rows.append({"work_order_id": wo.work_order_id, "before": before.mean(), "after": after.mean()})
    r = pd.DataFrame(rows)
    if r.empty:
        return {"work_orders_evaluable": 0}
    return {"measure": "charger first-attempt success, before vs after a corrective work order",
            "window_days": days, "work_orders_evaluable": int(len(r)),
            "corrective_work_orders": int((work_orders["work_type"] == "corrective").sum()),
            "median_first_attempt_success_before_pct": pct(r["before"].median()),
            "median_first_attempt_success_after_pct": pct(r["after"].median()),
            "share_improved_pct": pct((r["after"] > r["before"]).mean()),
            "caveat": "illustrative: work orders are simulated; no control group, and the whole fleet improved over "
                      "the same months, so this does not show that repairs caused the change"}


def compute_metrics(attempts, visits, sites, charger_stats, outages, open_runs, status_events, work_orders, defs, run_date,
                    blank_port_rows) -> dict:
    base = baseline_months(visits, defs["kpi"]["baseline_months"])
    q = visits[visits["month"].isin(base)]
    qa = attempts[attempts["visit_id"].isin(q["visit_id"])]
    overall = visit_summary(attempts, visits)
    baseline = visit_summary(qa, q)
    reporting_month = (run_date - pd.Timedelta(days=1)).strftime("%Y-%m")
    rm = visits[visits["month"] == reporting_month]
    monthly = (visits.groupby("month").agg(visits=("visit_id", "size"), ftcs=("first_attempt_success", "mean"),
                                           failed_visit_rate=("outcome", lambda s: (s == "failed_visit").mean()))
               .reset_index())
    monthly[["ftcs", "failed_visit_rate"]] = (monthly[["ftcs", "failed_visit_rate"]] * 100).round(2)
    failed = attempts[~attempts["is_success"]]
    card, lag = site_scorecard(visits, sites, base, defs)
    sens = sensitivity_table(attempts, defs)
    rel = reliability_definitions(status_events, charger_stats)
    rep = repair_effect(work_orders, attempts, defs)
    silent = charger_stats[charger_stats["silent_charger"]]
    corrective = work_orders[work_orders["work_type"] == "corrective"]
    grace = pd.Timedelta(days=defs["trend"]["commissioned_mid_window_after_days"])
    commissioned_mid = int((charger_stats["first_seen"] > attempts["session_start"].min() + grace).sum())
    metrics = {
        "definitions_version": defs["version"],
        "run_date": str(run_date.date()), "reporting_month": reporting_month,
        "data_window": [str(attempts["session_start"].min()), str(attempts["session_start"].max())],
        "scope": {"dc_chargers": int(attempts["charger_id"].nunique()), "sites": int(sites.shape[0]),
                  "attempts": int(len(attempts)), "unbound_attempts": int(attempts["is_unbound"].sum()),
                  "chargers_commissioned_mid_window": commissioned_mid},
        "kpi": {"name": defs["kpi"]["name"], "baseline_months": base, "baseline_ftcs_pct": pct(baseline["ftcs"], 2),
                "ftcs_13_month_pct": pct(overall["ftcs"], 2), "reporting_month_ftcs_pct": pct(rm["first_attempt_success"].mean(), 2),
                "headline": f"1 in {round(1 / (1 - baseline['ftcs']))} drivers fail on their first try (baseline quarter)",
                "target_pct": 100 * defs["kpi"]["target"]["to"], "stretch_next_quarter_pct": 100 * defs["kpi"]["target"]["stretch_next_quarter"]},
        "overall_13_months": {k: (pct(v) if k.endswith("rate") or k == "ftcs" else (round(v, 2) if isinstance(v, float) else v))
                              for k, v in overall.items()},
        "baseline_quarter": {k: (pct(v) if k.endswith("rate") or k == "ftcs" else (round(v, 2) if isinstance(v, float) else v))
                             for k, v in baseline.items()},
        "driver_behaviour": retry_behaviour(visits, attempts),
        "judgement_call": judgement_call(attempts, visits, base, blank_port_rows, defs),
        "instrumentation": {"unbound_share_of_failed_attempts_pct": pct(failed["is_unbound"].mean()),
                            "session_error_populated_rows": int((attempts["session_error"] != "").sum())},
        "lagging_sites": lag,
        "inferred_outages": {"windows": int(len(outages)), "fleet_inferred_availability_pct": rel["inferred_availability_real_pct"],
                             "silent_chargers": int(len(silent)), "silent_charger_ids": silent["charger_id"].tolist(),
                             "corr_availability_vs_first_attempt_success": round(float(charger_stats[["inferred_availability", "first_attempt_success"]].corr().iloc[0, 1]), 2),
                             "open_at_data_end": [{k: (str(x) if isinstance(x, pd.Timestamp) else x) for k, x in r.items()}
                                                  for r in open_runs.to_dict("records")],
                             "basis": "inferred from real sessions"},
        "illustrative_simulated_input": {
            "reliability_definitions": rel,
            "repair_effect": rep,
            "corrective_work_orders_on_silent_chargers": int(corrective["charger_id"].isin(silent["charger_id"]).sum()),
            "label": "illustrative (simulated input) — S1/S2 are simulated client systems anchored to real inferred outages"},
    }
    return {"metrics": metrics, "monthly": monthly, "scorecard": card, "sensitivity": sens}


def evidence_table(m: dict, sens: pd.DataFrame) -> str:
    k, b, o = m["kpi"], m["baseline_quarter"], m["overall_13_months"]
    rel = m["illustrative_simulated_input"]["reliability_definitions"]
    rep = m["illustrative_simulated_input"]["repair_effect"]
    fv = sens.loc[sens["changes"] == "definition", "failed_visit_pct"]   # definition ranges exclude the rejected D2 row
    rows = [
        ("1", "First-Time Charge Success (FTCS) — **project KPI**", "Outcome", f"{k['baseline_ftcs_pct']}%",
         f"{k['ftcs_13_month_pct']}%", "Visits whose first attempt delivered ≥1 kWh ÷ visits (site-level, 5-min window)",
         "Real", "This *is* the KPI: target ≥87% in 6 weeks", "Why a first attempt failed (charger, car, driver or payment)"),
        ("2", "Failed-visit rate", "Outcome", f"{b['failed_visit_rate']}%", f"{o['failed_visit_rate']}%",
         "Visits where no attempt delivered ≥1 kWh ÷ visits", "Real",
         "The worst outcome inside the KPI gap: drivers who left with nothing",
         f"Exact size — definition-sensitive ({fv.min()}–{fv.max()}% across tested definitions)"),
        ("3", "Troubled-success rate (driver retries)", "Driver interaction", f"{b['troubled_success_rate']}%",
         f"{o['troubled_success_rate']}%", "Visits that failed first but succeeded on a retry ÷ visits", "Real",
         f"Retries are hidden KPI loss; {m['driver_behaviour']['retry_visits_switching_charger_pct']}% of retry visits move to another charger",
         "Whether the retry fixed the charger or the driver changed something"),
        ("4", "Port-less share of failed attempts", "Instrumentation gap", f"{m['instrumentation']['unbound_share_of_failed_attempts_pct']}%",
         "—", "Failed attempts with no port recorded ÷ failed attempts", "Real",
         "Nearly a third of failures cannot be attributed to a port, so crews cannot be sent to them", "What stage the attempt died at (auth, handshake, payment)"),
        ("5", "Reliability-definition gap", "Operations / intervention",
         f"Operator uptime {rel['operator_noc_uptime_pct']}% · federal-style {rel['federal_style_uptime_pct']}% · inferred availability {rel['inferred_availability_real_pct']}% · FTCS {k['baseline_ftcs_pct']}%",
         "—", "Same fleet measured four ways; charger first-attempt success before → after corrective work orders: "
         f"median {rep.get('median_first_attempt_success_before_pct')}% → {rep.get('median_first_attempt_success_after_pct')}% "
         f"(n={rep.get('work_orders_evaluable')}, no control group)",
         "Illustrative (simulated input) for operator/federal uptime and repairs; availability inferred from real data",
         "Shows why 'uptime' cannot be the reliability headline",
         "Real maintenance history (work orders are simulated), or that repairs caused the change (no control group)"),
    ]
    head = ("| # | Metric | Type | Baseline quarter | 13 months | Definition / grain | Basis | Link to KPI | Does NOT prove |\n"
            "|---|---|---|---|---|---|---|---|---|\n")
    return head + "\n".join("| " + " | ".join(r) + " |" for r in rows) + "\n"
