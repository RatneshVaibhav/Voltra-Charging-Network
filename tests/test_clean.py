from pipeline.clean import EXPECTED_COLUMNS, parse_session_files, standardise_sessions

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
