import pandas as pd

from pipeline.inference import infer_outages, open_runs_at_data_end
from pipeline.metrics import baseline_months, judgement_call, retry_behaviour, site_scorecard
from pipeline.transform import build_visits


def _attempts(rows):
    """rows: (site, charger, port_key, start_minute, duration_minutes, kwh)"""
    t0 = pd.Timestamp("2024-01-01 10:00", tz="UTC")
    out = []
    for i, (site, charger, port_key, start, dur, kwh) in enumerate(rows):
        s = t0 + pd.Timedelta(minutes=start)
        out.append({"session_id": str(i), "site_id": site, "charger_id": charger, "port_key": port_key,
                    "is_unbound": port_key.startswith("UNBOUND@"), "energy_kwh": kwh, "is_success": kwh >= 1,
                    "session_start": s, "session_end": s + pd.Timedelta(minutes=dur), "duration_min": float(dur)})
    return build_visits(pd.DataFrame(out), grouping_key="site_id", min_gap=-2, max_gap=5)


def test_retry_switch_counts_chargers_not_unbound_port_keys():
    a, v = _attempts([("S01", "C1", "UNBOUND@C1", 0, 2, 0.0), ("S01", "C1", "P1", 3, 30, 20.0),   # stayed on C1
                      ("S02", "C2", "P2", 0, 2, 0.0), ("S02", "C3", "P3", 3, 30, 20.0)])          # moved to C3
    b = retry_behaviour(v, a)
    assert b["retry_visits_pct"] == 100.0
    assert b["multi_attempt_visits_split_by_port_grouping_pct"] == 100.0   # port-level grouping would split both
    assert b["retry_visits_switching_charger_pct"] == 50.0                 # but only one driver actually moved


def test_dropping_port_less_attempts_is_measured_not_applied(defs):
    a, v = _attempts([("S01", "C1", "UNBOUND@C1", 0, 2, 0.0), ("S01", "C1", "P1", 3, 30, 20.0),   # driver 1 retries
                      ("S01", "C1", "P1", 120, 30, 20.0)])                                        # driver 2
    j = judgement_call(a, v, ["2024-01"], blank_port_rows=1, defs=defs)
    assert j["ftcs_13_month_kept_pct"] == 50.0 and j["ftcs_13_month_if_dropped_pct"] == 100.0
    assert j["inflation_if_dropped_pts"]["13_months"] == 50.0 and j["all_blank_port_rows_on_dc_chargers"]
    assert len(v) == 2 and a["is_unbound"].sum() == 1                      # the model itself still keeps the attempt


def test_open_run_at_data_end_is_listed_not_counted_as_downtime(defs):
    rows = [("S01", ("C1" if i % 2 == 0 else "C2") if i < 40 else "C2", "", i * 60, 30, 20.0) for i in range(80)]
    rows = [(s, c, "P" + c[1], t, d, k) for s, c, _, t, d, k in rows]      # C1 goes silent after session 38
    a, _ = _attempts(rows)
    windows, stats = infer_outages(a, defs)
    listed = open_runs_at_data_end(a, defs)
    assert list(listed["charger_id"]) == ["C1"] and len(windows) == 0
    assert stats.set_index("charger_id").loc["C1", "inferred_availability"] == 1.0


def _site(site_id, n, ok):
    return pd.DataFrame({"site_id": site_id, "visit_id": [f"{site_id}-{i}" for i in range(n)],
                         "first_attempt_success": [i < ok for i in range(n)],
                         "outcome": ["first_time_success" if i < ok else "failed_visit" for i in range(n)],
                         "month": "2025-01"})


def test_lagging_rule_compares_unrounded_values(defs):
    # median of the eligible sites is 90%. S03 is 5.004 pts below it (84.996% would round to "exactly 5.00"),
    # S05 is 4.996 pts below. Only S03 is strictly more than 5.0 pts below.
    v = pd.concat([_site("S01", 1000, 900), _site("S02", 1000, 900), _site("S03", 25000, 21249),
                   _site("S04", 1000, 950), _site("S05", 25000, 21251)], ignore_index=True)
    sites = pd.DataFrame({"site_id": [f"S0{i}" for i in range(1, 6)], "address": "x", "state": "TN", "n_dc_chargers": 2})
    _, summary = site_scorecard(v, sites, ["2025-01"], defs)
    assert summary["lagging_sites"] == ["S03"]


def test_baseline_is_the_last_n_months_present_in_the_data():
    v = pd.DataFrame({"month": ["2024-09", "2024-10", "2024-11", "2025-01", "2025-01"]})
    assert baseline_months(v, 3) == ["2024-10", "2024-11", "2025-01"]    # anchored to the data, not the calendar
