import pandas as pd
from conftest import session

from pipeline.transform import build_attempts, build_visits, classify_dc_chargers, resolve_sites


def _stations():
    return [
        {"id": 1, "station_name": "ORG STATION 1", "street_address": "1 Main St", "city": "A", "state": "TN",
         "latitude": 36.0, "longitude": -86.0, "ev_network_ids": {"posts": ["P1"]}},
        {"id": 2, "station_name": "ORG STATION 2", "street_address": "1 MAIN STREET", "city": "A", "state": "TN",
         "latitude": 36.0001, "longitude": -86.0001, "ev_network_ids": {"posts": ["P2"]}},      # ~14 m away, other spelling
        {"id": 3, "station_name": "FAR STATION", "street_address": "9 Far Rd", "city": "B", "state": "TN",
         "latitude": 35.0, "longitude": -85.0, "ev_network_ids": {"posts": ["P3"]}},
    ]


def test_dc_is_classified_per_charger_and_unbound_rows_are_kept(defs, log):
    rows = [session("1", "C1", "P1", "2024-01-01 10:00", 30, 20.0, peak=100),
            session("2", "C1", "", "2024-01-01 11:00", 2, 0.0, peak=0),           # unbound failed attempt
            session("3", "C9", "P9", "2024-01-01 12:00", 60, 5.0, peak=7)]        # Level 2 -> out of scope
    s = pd.DataFrame(rows)
    dc = classify_dc_chargers(s, defs, log)
    assert dc == {"C1"}
    _, chargers, _ = resolve_sites(s[s.charger_id.isin(dc)], _stations(), defs, log)
    a = build_attempts(s, dc, chargers, defs, log)
    assert len(a) == 2 and a["is_unbound"].sum() == 1
    assert set(a["port_key"]) == {"P1", "UNBOUND@C1"}


def test_address_variants_within_150m_merge_and_far_sites_stay_apart(defs, log):
    s = pd.DataFrame([session("1", "C1", "P1", "2024-01-01", 30, 20), session("2", "C2", "P2", "2024-01-01", 30, 20),
                      session("3", "C3", "P3", "2024-01-01", 30, 20)])
    sites, chargers, diag = resolve_sites(s, _stations(), defs, log)
    assert diag["sites"] == 2 and diag["sites_merged_from_address_variants"] == 1
    assert chargers.set_index("charger_id").loc["C1", "site_id"] == chargers.set_index("charger_id").loc["C2", "site_id"]


def test_name_match_fallback_when_port_unknown(defs, log):
    s = pd.DataFrame([session("1", "C7", "PX", "2024-01-01", 30, 20, name="FAR / STATION")])
    _, chargers, diag = resolve_sites(s, _stations(), defs, log)
    assert diag["by_method"] == {"name_match": 1} and diag["unresolved"] == 0


def _visits_for_gap(gap_minutes):
    t0 = pd.Timestamp("2024-01-01 10:00", tz="UTC")
    a = pd.DataFrame({
        "site_id": ["S01", "S01"], "session_id": ["1", "2"], "charger_id": ["C1", "C2"], "port_key": ["P1", "P2"],
        "is_unbound": [False, False], "energy_kwh": [0.0, 20.0], "is_success": [False, True],
        "session_start": [t0, t0 + pd.Timedelta(minutes=2 + gap_minutes)],
        "session_end": [t0 + pd.Timedelta(minutes=2), t0 + pd.Timedelta(minutes=40 + gap_minutes)]})
    return build_visits(a, grouping_key="site_id", min_gap=-2, max_gap=5)[1]


def test_visit_window_boundaries():
    assert len(_visits_for_gap(5)) == 1                       # exactly 5 min -> same visit (troubled success)
    assert _visits_for_gap(5)["outcome"].iloc[0] == "troubled_success"
    assert len(_visits_for_gap(5.01)) == 2                    # just over -> new visit
    assert len(_visits_for_gap(-2)) == 1                      # small overlap tolerated
    assert len(_visits_for_gap(-2.01)) == 2


def _model_checks(s, defs, log, tamper=None):
    from pipeline.validate import check_model
    dc = set(s["charger_id"])
    _, chargers, diag = resolve_sites(s, _stations(), defs, log)
    a, v = build_visits(build_attempts(s, dc, chargers, defs, log), grouping_key="site_id", min_gap=-2, max_gap=5)
    if tamper:
        a = tamper(a)
    no_open = pd.DataFrame(columns=["site_id", "charger_id", "days_without_any_session_at_data_end",
                                    "trailing_site_successes"])
    return {r.check: r.status for r in check_model(a, v, diag, len(s), "snapshot", s["session_start"].max(), {},
                                                   r1_columns=list(s.columns), r1_session_ids=set(s["session_id"]),
                                                   open_runs=no_open)}


def test_unresolved_charger_fails_the_model_gate(defs, log):
    s = pd.DataFrame([session("1", "C8", "PX", "2024-01-01", 30, 20, name="NOWHERE / UNKNOWN")])
    assert _model_checks(s, defs, log)["model.site_resolution"] == "FAIL"


def test_simulated_or_foreign_rows_in_kpi_inputs_fail(defs, log):
    s = pd.DataFrame([session("1", "C1", "P1", "2024-01-01", 30, 20)])
    assert _model_checks(s, defs, log)["model.no_simulated_fields_in_kpi_inputs"] == "PASS"
    assert _model_checks(s, defs, log, lambda a: a.assign(error_code="InternalError"))[
        "model.no_simulated_fields_in_kpi_inputs"] == "FAIL"                     # a simulated column leaked in
    assert _model_checks(s, defs, log, lambda a: a.assign(session_id="S1-EV-0001"))[
        "model.no_simulated_fields_in_kpi_inputs"] == "FAIL"                     # a row that is not an R1 session
