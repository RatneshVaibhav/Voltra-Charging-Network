"""CLEAN stage — representation repairs only. Every repair is counted and logged; no business row is dropped.

Repairs applied (all safe, representation-level):
  1. Glued header: some exports append the next file's header onto the last data row with no newline
     (`...*2provider_id,station_id,...`). A newline is inserted before any header not at line start.
  2. Repeated header rows (from concatenated exports) are removed — they are not data. Every header row must be
     identical to the first one; a reordered or renamed header is recorded for the gate to FAIL, never re-mapped.
  3. Whitespace is stripped from text fields; timestamps parsed to UTC; numbers to floats. Values that do not parse
     are left missing (never imputed) and counted per column for the gate.
  4. The export's blank `site_id`/`station_id` columns are renamed `source_site_id`/`source_station_id`.
  5. Exact duplicate rows (every column identical) are collapsed to one — counted and logged.
     Conflicting duplicates (same session_id, different values) are left in place for the gate to FAIL.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = ["provider_id", "station_id", "site_id", "charger_id", "evse_id", "evse_name", "port_id",
                    "connector_id", "session_id", "session_start", "session_end", "session_error", "energy_kwh",
                    "peak_power_kw", "payment_method", "payment_other", "eMI3 Port id"]
HEADER_START = "provider_id,station_id"
GLUED_HEADER = re.compile(r"(?<!\n)provider_id,station_id")


def parse_session_files(files: list[Path], logger) -> tuple[pd.DataFrame, dict]:
    """Repair glued headers and parse all monthly exports into one table (strings, no type coercion yet)."""
    rows, header, stats = [], None, {"glued_headers_repaired": 0, "header_rows_seen": 0, "header_rows_removed": 0,
                                     "header_mismatches": [], "malformed_rows": 0, "per_file": {}}
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        glued = len(GLUED_HEADER.findall(text)) - (1 if text.startswith(HEADER_START) else 0)
        text = GLUED_HEADER.sub("\n" + HEADER_START, text)
        file_rows = malformed = headers = 0
        for record in csv.reader(io.StringIO(text)):
            if not record:
                continue
            if record[0] == "provider_id":
                if header is None:
                    header = record
                elif record != header:
                    # same field count but different order/names would silently mis-assign every value below it
                    diff = next((i for i, (a, b) in enumerate(zip(header, record)) if a != b), min(len(header), len(record)))
                    stats["header_mismatches"].append({
                        "file": path.name, "columns_expected": len(header), "columns_found": len(record),
                        "first_difference": f"position {diff}: expected "
                                            f"{header[diff] if diff < len(header) else None!r}, "
                                            f"found {record[diff] if diff < len(record) else None!r}"})
                    logger.warning("CLEAN | file=%s header differs from the first file's header (%s)", path.name,
                                   stats["header_mismatches"][-1]["first_difference"])
                headers += 1
                continue
            if len(record) != len(header or EXPECTED_COLUMNS):
                malformed += 1
                continue
            rows.append(record + [path.name])
            file_rows += 1
        stats["glued_headers_repaired"] += glued
        stats["header_rows_seen"] += headers
        stats["header_rows_removed"] += max(headers - 1, 0)
        stats["malformed_rows"] += malformed
        stats["per_file"][path.name] = {"rows": file_rows, "glued_headers": glued, "malformed": malformed}
        logger.info("CLEAN | file=%s rows=%s glued_headers_repaired=%s malformed=%s", path.name, file_rows, glued, malformed)
    df = pd.DataFrame(rows, columns=(header or EXPECTED_COLUMNS) + ["source_file"])
    logger.info("CLEAN | parsed rows=%s glued_headers_repaired=%s repeated_headers_removed=%s malformed=%s",
                len(df), stats["glued_headers_repaired"], stats["header_rows_removed"], stats["malformed_rows"])
    return df, stats


def standardise_sessions(df: pd.DataFrame, logger) -> tuple[pd.DataFrame, dict]:
    """Types, whitespace, UTC timestamps, exact-duplicate collapse. Returns the table plus repair counts."""
    out = df.copy()
    # the export's own site_id / station_id columns are always blank; keep them under unambiguous names so they
    # can never be confused with the site_id this pipeline resolves from the registry
    out = out.rename(columns={"site_id": "source_site_id", "station_id": "source_station_id"})
    for col in out.columns:
        # pandas >= 3 reads text as the 'str' dtype, not object — check both so the strip is never skipped silently
        if out[col].dtype == object or pd.api.types.is_string_dtype(out[col].dtype):
            out[col] = out[col].str.strip()
    # the retrieval/schema gate has already FAILed any run missing these columns, so no column is skipped here
    numeric_nulls = {}
    for col in ("energy_kwh", "peak_power_kw"):
        parsed = pd.to_numeric(out[col], errors="coerce")
        blank = out[col].eq("")
        numeric_nulls[col] = {"blank": int((parsed.isna() & blank).sum()),
                              "unparseable": int((parsed.isna() & ~blank).sum())}
        out[col] = parsed
    for col in ("session_start", "session_end"):
        out[col] = pd.to_datetime(out[col], utc=True, errors="coerce")
    compare_cols = [c for c in out.columns if c != "source_file"]
    exact_dupes = int(out.duplicated(subset=compare_cols).sum())
    if exact_dupes:
        out = out.drop_duplicates(subset=compare_cols).copy()
        logger.warning("CLEAN | exact duplicate rows collapsed=%s (rule: attempt.exact_duplicate_rows)", exact_dupes)
    stats = {
        "exact_duplicates_collapsed": exact_dupes,
        "unparseable_timestamps": int(out[["session_start", "session_end"]].isna().any(axis=1).sum()),
        "numeric_nulls": numeric_nulls,
    }
    logger.info("CLEAN | standardised rows=%s exact_duplicates_collapsed=%s unparseable_timestamps=%s",
                len(out), exact_dupes, stats["unparseable_timestamps"])
    logger.info("CLEAN | numeric fields left missing (never imputed): %s",
                "; ".join(f"{c} blank={v['blank']} unparseable={v['unparseable']}" for c, v in numeric_nulls.items()))
    return out.reset_index(drop=True), stats
