"""Inferred charger outages from REAL session data (no status feed needed).

At a multi-charger site, a working charger takes a share p of the site's successful sessions. A run of k
consecutive successful site sessions that all went to OTHER chargers is very unlikely by chance when
(1-p)^k < threshold; such runs are flagged as inferred outage windows. A window is closed on both sides by the
charger's own successes, so it always lies inside the charger's commissioned life.

A run that is still open when the data ends (the charger never succeeds again) is NOT a window: it cannot be told
apart from a decommissioning, so it is never counted as downtime. It is listed by `open_runs_at_data_end` for
on-site verification instead — at the end of the reporting month it is the freshest "go and look" signal we have.
These are INFERRED, not observed — every output is labelled that way.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def infer_outages(attempts: pd.DataFrame, defs: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    rules = defs["outage_inference"]
    life = attempts.groupby("charger_id").agg(first_seen=("session_start", "min"), last_seen=("session_end", "max"))
    per_site = attempts.groupby("site_id")["charger_id"].nunique()
    multi = per_site[per_site >= 2].index
    windows = []
    for site in multi:
        ok = (attempts[(attempts["site_id"] == site) & attempts["is_success"]]
              .sort_values(["session_start", "session_id"]).reset_index(drop=True))
        for charger, share in ok["charger_id"].value_counts(normalize=True).items():
            if share < rules["min_share"]:
                continue
            k_needed = math.ceil(math.log(rules["probability_threshold"]) / math.log(1 - share))
            mine = (ok["charger_id"] == charger).to_numpy()
            run, start = 0, None
            for i, is_mine in enumerate(mine):
                if not is_mine:
                    if run == 0:
                        start = i
                    run += 1
                    continue
                if run >= k_needed and start and start > 0:
                    windows.append({"site_id": site, "charger_id": charger, "share": round(float(share), 4),
                                    "k_run": run, "k_needed": k_needed,
                                    "start": ok["session_end"].iloc[start - 1], "end": ok["session_start"].iloc[i]})
                run = 0
    w = pd.DataFrame(windows, columns=["site_id", "charger_id", "share", "k_run", "k_needed", "start", "end"])
    if len(w):
        w = w.join(life, on="charger_id")
        inside = (w["start"] >= w["first_seen"]) & (w["end"] <= w["last_seen"])
        excluded = int((~inside).sum())          # rule outage_inference.bounded_by: pre-install / post-removal runs
        w = w[inside].drop(columns=["first_seen", "last_seen"])
        w.attrs["excluded_outside_commissioned_life"] = excluded
        w["hours"] = (w["end"] - w["start"]).dt.total_seconds() / 3600
        w = w.sort_values(["charger_id", "start"]).reset_index(drop=True)
        w.insert(0, "outage_id", [f"OUT-{i + 1:04d}" for i in range(len(w))])
    w["basis"] = "inferred"

    chargers = attempts.groupby("charger_id").agg(site_id=("site_id", "first")).join(life)
    chargers["inference_possible"] = chargers["site_id"].isin(multi)
    life_min = (chargers["last_seen"] - chargers["first_seen"]).dt.total_seconds() / 60
    down_min = (w.groupby("charger_id")["hours"].sum() * 60).reindex(chargers.index).fillna(0.0) if len(w) else 0.0
    chargers["inferred_availability"] = np.where(chargers["inference_possible"], 1 - down_min / life_min, np.nan)
    first_attempts = attempts[attempts["attempt_no"] == 1] if "attempt_no" in attempts else attempts
    chargers["first_attempt_success"] = first_attempts.groupby("charger_id")["is_success"].mean()
    chargers["first_attempts"] = first_attempts.groupby("charger_id").size()
    s = rules["silent_charger"]
    chargers["silent_charger"] = (chargers["inferred_availability"] >= s["min_inferred_availability"]) & \
                                 (chargers["first_attempt_success"] < s["max_first_attempt_success"])
    return w, chargers.reset_index()


def open_runs_at_data_end(attempts: pd.DataFrame, defs: dict) -> pd.DataFrame:
    """Chargers whose last success is followed by >= k_needed site successes on other chargers up to the data end."""
    rules = defs["outage_inference"]
    data_end = attempts["session_start"].max()
    per_site = attempts.groupby("site_id")["charger_id"].nunique()
    rows = []
    for site in per_site[per_site >= 2].index:
        ok = (attempts[(attempts["site_id"] == site) & attempts["is_success"]]
              .sort_values(["session_start", "session_id"]).reset_index(drop=True))
        for charger, share in ok["charger_id"].value_counts(normalize=True).items():
            if share < rules["min_share"]:
                continue
            k_needed = math.ceil(math.log(rules["probability_threshold"]) / math.log(1 - share))
            last = int(np.flatnonzero((ok["charger_id"] == charger).to_numpy())[-1])
            trailing = len(ok) - 1 - last
            if trailing < k_needed:
                continue
            mine = attempts[attempts["charger_id"] == charger]
            rows.append({"charger_id": charger, "site_id": site, "share": round(float(share), 4), "k_needed": k_needed,
                         "trailing_site_successes": trailing, "last_success_end": ok["session_end"].iloc[last],
                         "sessions_after_last_success": int((mine["session_start"] > ok["session_start"].iloc[last]).sum()),
                         "days_without_any_session_at_data_end":
                             round((data_end - mine["session_end"].max()).total_seconds() / 86400, 1),
                         "basis": "inferred; open at data end (outage or decommissioning) — verify on site"})
    return pd.DataFrame(rows, columns=["charger_id", "site_id", "share", "k_needed", "trailing_site_successes",
                                       "last_success_end", "sessions_after_last_success",
                                       "days_without_any_session_at_data_end", "basis"])
