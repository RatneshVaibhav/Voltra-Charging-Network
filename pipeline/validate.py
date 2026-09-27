"""VALIDATE stage — the executable version of docs/validation_contract.md.

Each check returns PASS / WARN / FAIL / UNKNOWN with evidence. Any FAIL stops the run (exit code 2) and nothing new
is published. WARN = a known, counted, documented issue that the business rules handle explicitly.
UNKNOWN = the data cannot answer the question (organisational / semantic gaps).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .clean import EXPECTED_COLUMNS

REQUIRED_SESSION_COLUMNS = ["charger_id", "port_id", "evse_name", "session_id", "session_start", "session_end",
                            "session_error", "energy_kwh", "peak_power_kw"]
# columns the TRANSFORM stage adds to R1 sessions; anything else in the KPI inputs is a leak (D4)
DERIVED_ATTEMPT_COLUMNS = {"is_unbound", "port_key", "site_id", "is_success", "duration_min", "gap_to_prev_min",
                           "visit_id", "attempt_no"}
VISIT_OUTCOMES = {"first_time_success", "troubled_success", "failed_visit"}


class ValidationError(ValueError):
    pass


@dataclass
class CheckResult:
    check: str
    stage: str
    status: str
    detail: str
    evidence_count: int | None = None

    def as_dict(self):
        return asdict(self)


def _r(check, stage, status, detail, n=None):
    return CheckResult(check, stage, status, detail, None if n is None else int(n))


# ------------------------------------------------------------------ gate 1: retrieval + raw schema
def check_retrieval(evidence: list) -> list[CheckResult]:
    out = []
    for ev in evidence:
        status = "PASS" if ev.complete else "FAIL"
        out.append(_r(f"retrieval.{ev.source}", "retrieval", status,
                      f"mode={ev.mode}; expected={ev.expected}; received/verified={ev.received}", ev.received))
    return out


def check_raw_sessions(raw: pd.DataFrame, parse_stats: dict, defs: dict) -> list[CheckResult]:
    tol = defs["validation_tolerances"]
    out = []
    missing = [c for c in REQUIRED_SESSION_COLUMNS if c not in raw.columns]
    out.append(_r("sessions.required_columns", "schema", "FAIL" if missing else "PASS",
                  f"missing={missing}" if missing else f"{len(REQUIRED_SESSION_COLUMNS)} required columns present"))
    unexpected = [c for c in raw.columns if c not in EXPECTED_COLUMNS + ["source_file"]]
    if unexpected:
        out.append(_r("sessions.unexpected_columns", "schema", "WARN", f"unexpected={unexpected}", len(unexpected)))
    mismatches = parse_stats["header_mismatches"]
    out.append(_r("sessions.header_consistency", "schema", "FAIL" if mismatches else "PASS",
                  (f"header rows that differ from the first file's header={len(mismatches)} in "
                   f"{sorted({m['file'] for m in mismatches})}: {mismatches[0]['first_difference']} — columns are never "
                   f"re-mapped by guesswork; the export layout changed and must be confirmed with the CPMS vendor")
                  if mismatches else f"all {parse_stats['header_rows_seen']} header rows identical across files",
                  len(mismatches)))
    g = parse_stats["glued_headers_repaired"]
    out.append(_r("sessions.glued_headers", "schema", "WARN" if g else "PASS",
                  f"header glued onto a data row (no newline) repaired {g} times across files", g))
    m = parse_stats["malformed_rows"]
    fail_at = tol["malformed_rows_fail_share"] * max(len(raw), 1)
    out.append(_r("sessions.malformed_rows", "schema", "FAIL" if m > fail_at else ("WARN" if m else "PASS"),
                  f"rows with wrong field count={m}", m))
    return out


def check_simulated_sources(status_events: list, work_orders: pd.DataFrame) -> list[CheckResult]:
    bad_events = sum(1 for e in status_events if e.get("data_origin") != "simulated")
    bad_wo = int((work_orders.get("data_origin", pd.Series(dtype=str)) != "simulated").sum())
    return [
        _r("S1.labelled_simulated", "integrity", "FAIL" if bad_events else "PASS",
           f"status events without data_origin='simulated': {bad_events}", bad_events),
        _r("S2.labelled_simulated", "integrity", "FAIL" if bad_wo else "PASS",
           f"work orders without data_origin='simulated': {bad_wo}", bad_wo),
    ]


# ------------------------------------------------------------------ gate 2: content (after standardisation)
def check_sessions(s: pd.DataFrame, clean_stats: dict, defs: dict, run_date: pd.Timestamp,
                   today: pd.Timestamp) -> list[CheckResult]:
    tol = defs["validation_tolerances"]
    out = []
    n = len(s)
    bad_ts = clean_stats["unparseable_timestamps"]
    out.append(_r("sessions.timestamps_parse", "technical",
                  "FAIL" if bad_ts > tol["unparseable_timestamps_fail_share"] * n else ("WARN" if bad_ts else "PASS"),
                  f"unparseable session_start/end={bad_ts}", bad_ts))
    nn = clean_stats["numeric_nulls"]
    energy_missing = nn["energy_kwh"]["blank"] + nn["energy_kwh"]["unparseable"]
    peak_missing = nn["peak_power_kw"]["blank"] + nn["peak_power_kw"]["unparseable"]
    peak_missing_with_energy = int((s["peak_power_kw"].isna() & (s["energy_kwh"] > 0)).sum())
    out.append(_r("sessions.numeric_parse", "technical",
                  "FAIL" if energy_missing > tol["missing_energy_rows_fail_above"] else ("WARN" if peak_missing else "PASS"),
                  f"energy_kwh missing/unparseable={energy_missing} (FAIL above {tol['missing_energy_rows_fail_above']}: "
                  f"it is the KPI input and a missing value would count as a failed attempt); peak_power_kw "
                  f"blank={nn['peak_power_kw']['blank']} unparseable={nn['peak_power_kw']['unparseable']} "
                  f"({peak_missing_with_energy} of them delivered energy) — peak power is only used for DC classification "
                  f"(max per port, blanks ignored) and the physics check; left missing, never imputed",
                  energy_missing + peak_missing))
    dup_ids = s["session_id"].duplicated(keep=False)
    conflicting = int(s.loc[dup_ids, "session_id"].nunique())
    out.append(_r("sessions.session_id_unique", "technical", "FAIL" if conflicting else "PASS",
                  f"session_ids with conflicting duplicate rows={conflicting}; exact duplicates collapsed="
                  f"{clean_stats['exact_duplicates_collapsed']}", conflicting))
    if clean_stats["exact_duplicates_collapsed"]:
        out.append(_r("sessions.exact_duplicates", "technical", "WARN",
                      f"exact duplicate rows collapsed to one (rule attempt.exact_duplicate_rows)",
                      clean_stats["exact_duplicates_collapsed"]))
    populated = int((s["session_error"] != "").sum())
    out.append(_r("sessions.session_error_semantics", "semantic", "WARN" if populated == 0 else "PASS",
                  f"session_error populated on {populated} of {n} rows. Blank does NOT mean success: failures are "
                  f"inferred from energy delivered", populated))
    for col in ("source_site_id", "source_station_id"):
        if col in s:
            filled = int((s[col] != "").sum())
            out.append(_r(f"sessions.{col}_blank", "semantic", "WARN" if filled == 0 else "PASS",
                          f"{col} blank on {n - filled} of {n} rows; sites are resolved from the AFDC registry instead",
                          n - filled))
    unbound = int((s["port_id"] == "").sum())
    out.append(_r("sessions.blank_port_id", "semantic", "WARN" if unbound else "PASS",
                  f"blank port_id rows={unbound}; KEPT as unbound attempts (D2), never dropped", unbound))
    odd = int(((s["energy_kwh"] > 0) & (s["peak_power_kw"] == 0)).sum())
    out.append(_r("sessions.energy_without_power", "technical", "WARN" if odd else "PASS",
                  f"energy_kwh>0 with peak_power_kw=0 (physically inconsistent) rows={odd}; flagged, not reclassified", odd))
    dur = (s["session_end"] - s["session_start"]).dt.total_seconds() / 60
    neg, long_ = int((dur < 0).sum()), int((dur > 1440).sum())
    out.append(_r("sessions.duration_range", "technical", "WARN" if (neg or long_) else "PASS",
                  f"negative durations={neg}; sessions longer than 24 h={long_}", neg + long_))
    ports = s[s["port_id"] != ""].sort_values(["port_id", "session_start"])
    overlap = int(((ports["session_start"] - ports.groupby("port_id")["session_end"].shift()).dt.total_seconds() < 0).sum())
    out.append(_r("sessions.port_overlaps", "technical", "WARN" if overlap else "PASS",
                  f"sessions starting before the previous session on the same port ended={overlap}", overlap))
    blank_name = int((s["evse_name"] == "").sum())
    renamed = int((s[s["evse_name"] != ""].groupby("charger_id")["evse_name"].nunique() > 1).sum())
    out.append(_r("sessions.evse_name_stability", "semantic", "WARN" if (blank_name or renamed) else "PASS",
                  f"blank evse_name rows={blank_name}; chargers renamed during the period={renamed} "
                  f"(names are not stable identifiers; the '/' prefix is an owner, not a site)", blank_name + renamed))
    # completeness by calendar day (UTC)
    days = s["session_start"].dt.tz_convert("UTC").dt.normalize().drop_duplicates()
    months = pd.period_range(days.min().tz_localize(None), days.max().tz_localize(None), freq="M")
    cov = {}
    for m in months:
        have = int(((days.dt.tz_localize(None) >= m.start_time) & (days.dt.tz_localize(None) <= m.end_time)).sum())
        cov[str(m)] = round(have / m.days_in_month, 3)
    comp = defs["completeness"]
    worst = min(cov.values())
    missing_days = sum(round((1 - v) * pd.Period(k).days_in_month) for k, v in cov.items())
    status = "FAIL" if worst < comp["month_day_coverage_fail_below"] else ("WARN" if worst < comp["month_day_coverage_warn_below"] else "PASS")
    out.append(_r("sessions.day_coverage", "completeness", status,
                  f"calendar days with no sessions={missing_days}"
                  + (" (each monthly export ends one day early, UTC)" if missing_days == len(cov) else "")
                  + f"; worst month coverage={worst}", missing_days))
    # freshness vs the LOGICAL run date
    fr = defs["freshness"]
    month_end = (run_date - pd.Timedelta(days=1)).normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
    latest = s["session_start"].max()
    lag_days = (month_end - latest).total_seconds() / 86400
    status = "FAIL" if lag_days > fr["max_lag_days"] else "PASS"
    out.append(_r("sessions.freshness", "freshness", status,
                  f"reporting month ends {month_end.date()}; latest session_start={latest}; lag={lag_days:.2f} days "
                  f"(allowed {fr['max_lag_days']})", round(lag_days)))
    age = (today - latest).days
    out.append(_r("sessions.wall_clock_age", "freshness", "WARN" if age > tol["wall_clock_age_warn_days"] else "PASS",
                  f"data is {age} days older than today — historical backfill, not live operations", age))
    return out


# ------------------------------------------------------------------ gate 3: model
def check_model(attempts: pd.DataFrame, visits: pd.DataFrame, site_diag: dict, dc_session_rows: int,
                registry_snapshot: str, data_end: pd.Timestamp, client_brief: dict,
                r1_columns: list[str], r1_session_ids: set) -> list[CheckResult]:
    out = []
    out.append(_r("model.site_resolution", "cross-source", "FAIL" if site_diag["unresolved"] else "PASS",
                  f"chargers={site_diag['chargers']} by method={site_diag['by_method']} unresolved={site_diag['unresolved']}",
                  site_diag["unresolved"]))
    merged = site_diag["sites_merged_from_address_variants"]
    out.append(_r("model.address_variants", "cross-source", "WARN" if merged else "PASS",
                  f"{site_diag['address_strings']} registry address strings -> {site_diag['sites']} physical sites "
                  f"(variants merged={merged}; max within-site distance {site_diag['max_within_site_distance_m']} m, "
                  f"nearest other site {site_diag['min_between_site_distance_m']} m)", merged))
    out.append(_r("model.registry_temporal_alignment", "cross-source", "WARN",
                  f"registry snapshot={registry_snapshot}; sessions end {data_end.date()}. Registry status says nothing "
                  f"about 2024 availability — used for identity/location only", None))
    rows_ok = len(attempts) == dc_session_rows
    out.append(_r("model.attempt_row_conservation", "integrity", "PASS" if rows_ok else "FAIL",
                  f"DC session rows={dc_session_rows}; attempts={len(attempts)}", len(attempts)))
    # every attempt sits in exactly one visit, every visit has attempts, outcomes are from the defined set
    with_visit = int(attempts["visit_id"].notna().sum())
    visits_ok = (with_visit == len(attempts) and visits["visit_id"].is_unique
                 and set(attempts["visit_id"].dropna()) == set(visits["visit_id"])
                 and int(visits["attempts"].sum()) == len(attempts) and bool(visits["outcome"].isin(VISIT_OUTCOMES).all()))
    out.append(_r("model.visit_integrity", "integrity", "PASS" if visits_ok else "FAIL",
                  f"visits={len(visits)} (ids unique); attempts assigned to a visit={with_visit}/{len(attempts)}; "
                  f"attempts counted in visits={int(visits['attempts'].sum())}; outcomes within {sorted(VISIT_OUTCOMES)}",
                  len(visits)))
    # checked by content, not by column names: KPI inputs are R1 columns plus the transform's derived columns, and
    # every attempt is a real R1 session
    extra = sorted(set(attempts.columns) - set(r1_columns) - DERIVED_ATTEMPT_COLUMNS)
    foreign = int((~attempts["session_id"].isin(r1_session_ids)).sum())
    leak = bool(extra or foreign)
    out.append(_r("model.no_simulated_fields_in_kpi_inputs", "integrity", "FAIL" if leak else "PASS",
                  f"columns not from R1 or the transform: {extra}; attempts not in R1: {foreign}" if leak else
                  f"KPI inputs = {len(set(attempts.columns) & set(r1_columns))} R1 columns + "
                  f"{len(set(attempts.columns) & DERIVED_ATTEMPT_COLUMNS)} derived columns; all {len(attempts)} "
                  f"attempts are R1 session_ids", len(extra) + foreign))
    owner = (client_brief.get("reporting_facts") or {}).get("kpi_owner")
    out.append(_r("organisational.kpi_owner", "organisational", "UNKNOWN" if not owner else "PASS",
                  "no documented owner of the reliability KPI; four stakeholders define 'reliable' differently "
                  "(client_brief.json) — the definition used here needs sign-off" if not owner else f"owner={owner}"))
    return out


def check_dashboard(pipeline_noc_pct: float, api_noc_pct: float, defs: dict) -> CheckResult:
    diff = abs(pipeline_noc_pct - api_noc_pct)
    tolerance = defs["validation_tolerances"]["dashboard_reproduction_tolerance_pts"]
    return _r("S1.dashboard_reproducible", "semantic", "PASS" if diff <= tolerance else "WARN",
              f"operator dashboard={api_noc_pct}%; recomputed from its own events={pipeline_noc_pct:.2f}% "
              f"(tolerance {tolerance} pts)")


def gate(results: list[CheckResult], stage: str, logger=None, since: int = 0) -> None:
    """Stop the run on any FAIL. On pass, log this stage's counts and every WARN/UNKNOWN (results[since:])."""
    failures = [r for r in results if r.status == "FAIL"]
    if failures:
        raise ValidationError(f"{stage}: " + "; ".join(f"{r.check} -> {r.detail}" for r in failures))
    if logger is not None:
        new = results[since:]
        counts = pd.Series([r.status for r in new], dtype=str).value_counts().to_dict()
        logger.info("VALIDATE | %s PASSED | %s", stage, " ".join(f"{k}={counts[k]}" for k in sorted(counts)))
        for r in new:
            if r.status in ("WARN", "UNKNOWN"):
                logger.warning("VALIDATE | %s %s n=%s | %s", r.status, r.check, r.evidence_count, r.detail)
