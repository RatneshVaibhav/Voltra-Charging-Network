import pytest

from pipeline.clean import EXPECTED_COLUMNS, parse_session_files, standardise_sessions
from pipeline.validate import ValidationError, check_raw_sessions, gate

HEADER = ",".join(EXPECTED_COLUMNS)
ROW = "ChargePoint Network,,,111,111,ORG / S1,222,247,{sid},2024-01-01T10:00:00Z,2024-01-01T10:30:00Z,,12.5,60.0,membership,,X*1"


def test_glued_header_is_repaired_and_counted(tmp_path, log):
    f = tmp_path / "Se_01_2024.csv"
    f.write_text(HEADER + "\n" + ROW.format(sid="1") + HEADER + "\n" + ROW.format(sid="2") + "\n")
    df, stats = parse_session_files([f], log)
    assert list(df["session_id"]) == ["1", "2"]
    assert stats["glued_headers_repaired"] == 1


def test_exact_duplicates_collapsed_and_site_columns_renamed(tmp_path, log):
    f = tmp_path / "Se_01_2024.csv"
    f.write_text(HEADER + "\n" + ROW.format(sid="1") + "\n" + ROW.format(sid="1") + "\n")
    df, _ = parse_session_files([f], log)
    out, stats = standardise_sessions(df, log)
    assert len(out) == 1 and stats["exact_duplicates_collapsed"] == 1
    assert "source_site_id" in out and "site_id" not in out


def test_reordered_header_in_a_later_file_fails_the_schema_gate(tmp_path, log, defs):
    swapped = EXPECTED_COLUMNS.copy()
    i, j = swapped.index("energy_kwh"), swapped.index("peak_power_kw")
    swapped[i], swapped[j] = swapped[j], swapped[i]
    a, b = tmp_path / "Se_01_2024.csv", tmp_path / "Se_02_2024.csv"
    a.write_text(HEADER + "\n" + ROW.format(sid="1") + "\n")
    b.write_text(",".join(swapped) + "\n" + ROW.format(sid="2") + "\n")
    df, stats = parse_session_files([a, b], log)
    assert [m["file"] for m in stats["header_mismatches"]] == ["Se_02_2024.csv"]
    results = {r.check: r for r in check_raw_sessions(df, stats, defs)}
    assert results["sessions.header_consistency"].status == "FAIL"   # never re-mapped silently
    with pytest.raises(ValidationError):
        gate(list(results.values()), "schema")


def test_identical_headers_pass_and_are_counted(tmp_path, log, defs):
    f = tmp_path / "Se_01_2024.csv"
    f.write_text(HEADER + "\n" + ROW.format(sid="1") + HEADER + "\n" + ROW.format(sid="2") + "\n")
    df, stats = parse_session_files([f], log)
    check = {r.check: r for r in check_raw_sessions(df, stats, defs)}["sessions.header_consistency"]
    assert check.status == "PASS" and stats["header_rows_seen"] == 2


def test_whitespace_is_stripped_whatever_the_text_dtype(tmp_path, log):
    f = tmp_path / "Se_01_2024.csv"
    f.write_text(HEADER + "\n" + ROW.format(sid="1").replace(",222,", ", ,") + "\n")   # port_id is a lone space
    out, _ = standardise_sessions(parse_session_files([f], log)[0], log)
    assert out.loc[0, "port_id"] == ""                               # so it is treated as unbound, not as a port " "


def test_missing_numbers_are_counted_not_imputed(tmp_path, log):
    f = tmp_path / "Se_01_2024.csv"
    f.write_text(HEADER + "\n" + ROW.format(sid="1").replace(",60.0,", ",,") + "\n"
                 + ROW.format(sid="2").replace(",12.5,", ",n/a,") + "\n")
    out, stats = standardise_sessions(parse_session_files([f], log)[0], log)
    assert stats["numeric_nulls"] == {"energy_kwh": {"blank": 0, "unparseable": 1},
                                      "peak_power_kw": {"blank": 1, "unparseable": 0}}
    assert out["peak_power_kw"].isna().sum() == 1
