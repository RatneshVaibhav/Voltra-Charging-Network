import pandas as pd
import pytest
from conftest import session

from pipeline.save import publish_partition
from pipeline.validate import ValidationError, check_raw_sessions, check_sessions, gate

STATS = {"unparseable_timestamps": 0, "exact_duplicates_collapsed": 0}


def test_missing_required_column_fails_the_gate():
    raw = pd.DataFrame(columns=["charger_id", "port_id", "session_id"])
    results = check_raw_sessions(raw, {"glued_headers_repaired": 0, "malformed_rows": 0})
    with pytest.raises(ValidationError):
        gate(results, "schema")


def _sessions(last_start):
    rows = [session(str(i), "C1", "" if i == 0 else "P1", d, 30, 20.0)
            for i, d in enumerate(pd.date_range("2025-01-01", last_start, freq="D"))]
    return pd.DataFrame(rows)


def test_freshness_is_judged_against_the_logical_run_date(defs):
    run_date, today = pd.Timestamp("2025-02-01", tz="UTC"), pd.Timestamp("2026-09-27", tz="UTC")
    fresh = {r.check: r.status for r in check_sessions(_sessions("2025-01-30"), STATS, defs, run_date, today)}
    stale = {r.check: r.status for r in check_sessions(_sessions("2025-01-20"), STATS, defs, run_date, today)}
    assert fresh["sessions.freshness"] == "PASS" and stale["sessions.freshness"] == "FAIL"
    assert fresh["sessions.wall_clock_age"] == "WARN"          # old vs today is a warning, never a failure
    assert fresh["sessions.blank_port_id"] == "WARN"           # blank port ids are kept, flagged


def test_publish_replaces_partition_atomically(tmp_path, log):
    publish_partition(tmp_path, "2025-02-01", {"a.csv": pd.DataFrame({"x": [1, 2]})}, log)
    publish_partition(tmp_path, "2025-02-01", {"a.csv": pd.DataFrame({"x": [1, 2]})}, log)
    target = tmp_path / "run_date=2025-02-01"
    assert len(pd.read_csv(target / "a.csv")) == 2              # replaced, not appended
    assert sorted(p.name for p in tmp_path.iterdir()) == ["run_date=2025-02-01"]   # no temp/backup left behind
