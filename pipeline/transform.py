"""TRANSFORM stage — build the business model: sites -> chargers -> ports -> attempts -> visits.

Every rule below is read from config/kpi_definitions.json. Row counts in == row counts out for attempts:
nothing is filtered except non-DC chargers (an explicit, logged scope rule).
"""
from __future__ import annotations

import difflib
import math
import re

import numpy as np
import pandas as pd


def success_mask(energy: pd.Series, rule: dict) -> pd.Series:
    ops = {">=": energy.ge, ">": energy.gt}
    return ops[rule["operator"]](rule["value"])


def normalise_name(text: str) -> str:
    text = re.sub(r"[^A-Z0-9 ]", " ", (text or "").upper())
    return re.sub(r"\s+", " ", text).strip()


def classify_dc_chargers(sessions: pd.DataFrame, defs: dict, logger) -> set[str]:
    """DC classification at CHARGER level: failed attempts report peak power 0, so per-port rules misclassify."""
    threshold = defs["dc_charger"]["peak_power_threshold_kw"]
    identified = sessions[sessions["port_id"] != ""]
    dc_ports = identified.groupby("port_id")["peak_power_kw"].max()
    dc_ports = set(dc_ports[dc_ports > threshold].index)
    dc_chargers = set(identified.loc[identified["port_id"].isin(dc_ports), "charger_id"])
    logger.info("TRANSFORM | DC chargers=%s DC ports=%s (threshold %s kW, charger-level)", len(dc_chargers),
                len(dc_ports), threshold)
    return dc_chargers


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def resolve_sites(dc_sessions: pd.DataFrame, stations: list[dict], defs: dict, logger):
    """Charger -> AFDC record (port id, else fuzzy name) -> 150 m distance clusters = physical sites."""
    rules = defs["site_resolution"]
    post_to_station = {str(p): s for s in stations for p in (s.get("ev_network_ids") or {}).get("posts", [])}
    name_to_station = {normalise_name(s.get("station_name")): s for s in stations}
    records = []
    for charger_id, g in dc_sessions.groupby("charger_id"):
        ports = [p for p in g["port_id"].unique() if p]
        hit = next((post_to_station[p] for p in ports if p in post_to_station), None)
        method = "port_id"
        if hit is None:
            names = g.loc[g["evse_name"] != "", "evse_name"].value_counts().index.tolist()
            method = "unresolved"
            for name in names:
                match = difflib.get_close_matches(normalise_name(name.replace("/", " ")), list(name_to_station),
                                                  n=1, cutoff=rules["fuzzy_match_cutoff"])
                if match:
                    hit, method = name_to_station[match[0]], "name_match"
                    break
        records.append({
            "charger_id": charger_id, "resolution_method": method,
            "afdc_station_id": hit["id"] if hit else None,
            "afdc_station_name": hit["station_name"] if hit else None,
            "address": (f"{(hit.get('street_address') or '').upper().strip()}|{(hit.get('city') or '').upper()}"
                        if hit else None),
            "state": hit.get("state") if hit else None,
            "lat": hit.get("latitude") if hit else None, "lon": hit.get("longitude") if hit else None,
            "evse_name_latest": g.sort_values("session_start")["evse_name"].replace("", np.nan).dropna().iloc[-1]
            if (g["evse_name"] != "").any() else "",
            "evse_names_seen": int(g.loc[g["evse_name"] != "", "evse_name"].nunique()),
        })
    chargers = pd.DataFrame(records)
    resolved = chargers.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    # single-linkage clustering within max_distance_m (union-find)
    parent = list(range(len(resolved)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    coords = list(zip(resolved["lat"], resolved["lon"]))
    within, between = [0.0], []
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            d = _haversine_m(coords[i], coords[j])
            if d <= rules["max_distance_m"]:
                parent[root(i)] = root(j)
    resolved["cluster"] = [root(i) for i in range(len(resolved))]
    for _, g in resolved.groupby("cluster"):
        pts = list(zip(g["lat"], g["lon"]))
        within += [_haversine_m(a, b) for a in pts for b in pts]
    reps = resolved.groupby("cluster")["address"].agg(lambda s: s.value_counts().index[0])
    order = sorted(reps.index, key=lambda c: reps[c])
    site_code = {c: f"S{i + 1:02d}" for i, c in enumerate(order)}
    resolved["site_id"] = resolved["cluster"].map(site_code)
    centroids = resolved.groupby("cluster")[["lat", "lon"]].mean()
    cl = list(centroids.index)
    for i in range(len(cl)):
        for j in range(i + 1, len(cl)):
            between.append(_haversine_m(tuple(centroids.loc[cl[i]]), tuple(centroids.loc[cl[j]])))
    chargers = chargers.merge(resolved[["charger_id", "site_id"]], on="charger_id", how="left")
    sites = (resolved.groupby("site_id")
             .agg(address=("address", lambda s: s.value_counts().index[0]),
                  address_variants=("address", "nunique"), state=("state", "first"),
                  lat=("lat", "mean"), lon=("lon", "mean"), n_dc_chargers=("charger_id", "nunique"))
             .reset_index())
    diagnostics = {
        "chargers": len(chargers),
        "by_method": chargers["resolution_method"].value_counts().to_dict(),
        "unresolved": int(chargers["site_id"].isna().sum()),
        "sites": int(sites.shape[0]),
        "address_strings": int(resolved["address"].nunique()),
        "sites_merged_from_address_variants": int((sites["address_variants"] > 1).sum()),
        "max_within_site_distance_m": round(max(within), 1),
        "min_between_site_distance_m": round(min(between), 1) if between else None,
    }
    logger.info("TRANSFORM | sites=%s from address strings=%s (merged variants=%s) methods=%s unresolved=%s "
                "max_within_m=%s min_between_m=%s", diagnostics["sites"], diagnostics["address_strings"],
                diagnostics["sites_merged_from_address_variants"], diagnostics["by_method"],
                diagnostics["unresolved"], diagnostics["max_within_site_distance_m"],
                diagnostics["min_between_site_distance_m"])
    return sites, chargers, diagnostics


def build_attempts(sessions: pd.DataFrame, dc_chargers: set[str], chargers: pd.DataFrame, defs: dict, logger) -> pd.DataFrame:
    """One row per DC session (including unbound). Adds site, port_key, success flag. No rows dropped."""
    dc = sessions[sessions["charger_id"].isin(dc_chargers)].copy()
    logger.info("TRANSFORM | scope rule: kept DC sessions=%s of %s (non-DC chargers out of scope: %s rows)",
                len(dc), len(sessions), len(sessions) - len(dc))
    dc["is_unbound"] = dc["port_id"] == ""
    tmpl = defs["attempt"]["unbound_attempts"]["port_key_template"]
    dc["port_key"] = np.where(dc["is_unbound"], dc["charger_id"].map(lambda c: tmpl.format(charger_id=c)), dc["port_id"])
    dc = dc.merge(chargers[["charger_id", "site_id"]], on="charger_id", how="left", validate="many_to_one")
    dc["is_success"] = success_mask(dc["energy_kwh"], defs["attempt"]["success_rule"])
    dc["duration_min"] = (dc["session_end"] - dc["session_start"]).dt.total_seconds() / 60
    logger.info("TRANSFORM | attempts=%s unbound=%s successful=%s", len(dc), int(dc["is_unbound"].sum()),
                int(dc["is_success"].sum()))
    return dc.reset_index(drop=True)


def build_visits(attempts: pd.DataFrame, *, grouping_key: str, min_gap: float, max_gap: float,
                 success_col: str = "is_success") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Group consecutive attempts at the same key into visits; return (attempts with visit ids, visits)."""
    order = [grouping_key, "session_start", "session_end", "session_id"]
    a = attempts.sort_values(order).copy()
    prev_end = a.groupby(grouping_key)["session_end"].shift()
    gap = (a["session_start"] - prev_end).dt.total_seconds() / 60
    a["gap_to_prev_min"] = gap
    a["visit_seq"] = (~gap.between(min_gap, max_gap)).cumsum()
    a["visit_id"] = "V" + a["visit_seq"].astype(str).str.zfill(6)
    a["attempt_no"] = a.groupby("visit_id").cumcount() + 1
    visits = (a.groupby("visit_id")
              .agg(site_id=("site_id", "first"), first_charger_id=("charger_id", "first"),
                   visit_start=("session_start", "first"), visit_end=("session_end", "max"),
                   attempts=(success_col, "size"), first_attempt_success=(success_col, "first"),
                   any_success=(success_col, "max"), ports_tried=("port_key", "nunique"),
                   chargers_tried=("charger_id", "nunique"),
                   unbound_attempts=("is_unbound", "sum"), energy_kwh=("energy_kwh", "sum"))
              .reset_index())
    visits["outcome"] = np.select(
        [visits["first_attempt_success"], visits["any_success"]],
        ["first_time_success", "troubled_success"], default="failed_visit")
    visits["month"] = visits["visit_start"].dt.strftime("%Y-%m")
    return a.drop(columns=["visit_seq"]), visits


def visit_summary(attempts: pd.DataFrame, visits: pd.DataFrame, success_col: str = "is_success") -> dict:
    n = len(visits)
    return {
        "attempts": int(len(attempts)), "visits": int(n),
        "attempt_success_rate": float(attempts[success_col].mean()) if len(attempts) else None,
        "ftcs": float(visits["first_attempt_success"].mean()) if n else None,
        "troubled_success_rate": float((visits["outcome"] == "troubled_success").mean()) if n else None,
        "failed_visit_rate": float((visits["outcome"] == "failed_visit").mean()) if n else None,
        "attempts_per_visit": float(visits["attempts"].mean()) if n else None,
    }
