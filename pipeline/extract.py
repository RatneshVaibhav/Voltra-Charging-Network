"""EXTRACT stage — retrieve every source, preserve raw inputs, and prove completeness.

Retrieval modes used:
  R1 session exports  -> files over HTTP (Hugging Face)          proof: size + git-blob SHA-1 vs the HF tree API
  R2 station registry -> REST API (AFDC, developer.nlr.gov)       proof: len(fuel_stations) == total_results
  S1 status feed      -> REST API (simulated, paginated)           proof: received == total_records per month
  S2 work orders      -> SQL (simulated SQLite CMMS)               proof: row count == generation manifest

Raw payloads are written to disk BEFORE any parsing. Completeness results are returned as evidence for the
validation gate; a transport failure after bounded retries raises RetrievalError (exit code 1).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import requests

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class RetrievalError(RuntimeError):
    """A source could not be retrieved after bounded retries (or returned a non-retryable error)."""


@dataclass
class SourceEvidence:
    """What was retrieved and how we know it is complete. Consumed by the validation gate."""
    source: str
    mode: str
    expected: int | None = None
    received: int | None = None
    complete: bool | None = None
    details: dict = field(default_factory=dict)


def git_blob_sha1(data: bytes) -> str:
    """SHA-1 of a file as git stores it (what the Hugging Face tree API reports as `oid`)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def http_get_with_retry(session: requests.Session, url: str, *, params: dict | None, settings, logger,
                        label: str) -> requests.Response:
    """GET with bounded exponential backoff on transient failures only (429/5xx/timeouts/connection)."""
    for attempt in range(1, settings.max_retries + 1):
        try:
            response = session.get(url, params=params, timeout=settings.request_timeout)
        except (requests.Timeout, requests.ConnectionError) as exc:
            wait = settings.retry_base_seconds * 2 ** (attempt - 1)
            logger.warning("EXTRACT | %s request error attempt=%s/%s wait=%.1fs error=%s",
                           label, attempt, settings.max_retries, wait, exc)
            if attempt == settings.max_retries:
                raise RetrievalError(f"{label}: failed after {settings.max_retries} attempts: {exc}") from exc
            time.sleep(wait)
            continue
        if response.status_code == 200:
            return response
        if response.status_code in RETRYABLE_STATUS:
            wait = settings.retry_base_seconds * 2 ** (attempt - 1)
            retry_after = response.headers.get("Retry-After")
            try:
                retry_after = response.json().get("retry_after_seconds", retry_after)
            except ValueError:
                pass
            if retry_after is not None:
                wait = float(retry_after)
            logger.warning("EXTRACT | %s retryable status=%s attempt=%s/%s wait=%.1fs",
                           label, response.status_code, attempt, settings.max_retries, wait)
            if attempt == settings.max_retries:
                raise RetrievalError(f"{label}: status {response.status_code} after {settings.max_retries} attempts")
            time.sleep(wait)
            continue
        raise RetrievalError(f"{label}: non-retryable status {response.status_code}: {response.text[:200]}")
    raise RetrievalError(f"{label}: exhausted retries")  # pragma: no cover


def _reset_dir(path: Path) -> Path:
    """Raw partitions are replaced on every run (no stale files from earlier runs)."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


# ---------------------------------------------------------------- R1: session exports (files)
def extract_sessions(settings, raw_dir: Path, snapshot_dir: Path, offline: bool, logger,
                     corrupt_one_file: bool = False) -> tuple[list[Path], SourceEvidence]:
    """Download (or copy from snapshot) the 13 monthly exports and verify each against the HF tree listing."""
    out = _reset_dir(raw_dir / "sessions")
    session = requests.Session()
    if offline:
        tree = json.loads((snapshot_dir / "hf_tree_snapshot.json").read_text())
        mode = "files (committed snapshot)"
    else:
        tree_url = f"https://huggingface.co/api/datasets/{settings.hf_dataset}/tree/main/{settings.hf_folder}"
        tree = http_get_with_retry(session, tree_url, params=None, settings=settings, logger=logger,
                                   label="R1 tree").json()
        (out / "_hf_tree.json").write_text(json.dumps(tree, indent=2))
        mode = "files over HTTP (Hugging Face)"
    listing = sorted((item for item in tree if item.get("type") == "file" and item["path"].endswith(".csv")),
                     key=lambda item: item["path"])
    files, per_file = [], []
    for item in listing:
        name = item["path"].split("/")[-1]
        if offline:
            data = (snapshot_dir / "sessions" / name).read_bytes()
        else:
            url = (f"https://huggingface.co/datasets/{settings.hf_dataset}/resolve/main/"
                   f"{settings.hf_folder}/{name}")
            data = http_get_with_retry(session, url, params=None, settings=settings, logger=logger,
                                       label=f"R1 {name}").content
        if corrupt_one_file and not files:
            data = data[:-1] + (b"X" if data[-1:] != b"X" else b"Y")
            logger.warning("CHAOS | bad_checksum: corrupted last byte of %s", name)
        path = out / name
        path.write_bytes(data)                                   # raw bytes preserved before parsing
        size_ok = len(data) == item["size"]
        sha_ok = git_blob_sha1(data) == item["oid"]
        per_file.append({"file": name, "bytes": len(data), "expected_bytes": item["size"],
                         "size_ok": size_ok, "sha1_ok": sha_ok})
        files.append(path)
        logger.info("EXTRACT | source=R1 file=%s bytes=%s size_ok=%s sha1_ok=%s", name, len(data), size_ok, sha_ok)
    verified = sum(f["size_ok"] and f["sha1_ok"] for f in per_file)
    evidence = SourceEvidence("R1 session exports", mode, expected=len(listing), received=verified,
                              complete=verified == len(listing) and len(listing) > 0,
                              details={"files": per_file})
    return files, evidence


# ---------------------------------------------------------------- R2: AFDC registry (REST API)
def extract_afdc(settings, raw_dir: Path, snapshot_dir: Path, offline: bool, logger) -> tuple[list[dict], SourceEvidence]:
    out = _reset_dir(raw_dir / "afdc")
    if offline:
        payload = json.loads((snapshot_dir / "afdc_stations_snapshot.json").read_text())
        mode = "REST API response (committed snapshot)"
    else:
        if "developer.nrel.gov" in settings.afdc_base_url:
            raise RetrievalError("AFDC_BASE_URL uses developer.nrel.gov, which no longer resolves; use developer.nlr.gov")
        params = {"api_key": settings.afdc_api_key, "fuel_type": "ELEC", "state": settings.afdc_states,
                  "ev_network": settings.afdc_ev_network, "limit": "all"}
        response = http_get_with_retry(requests.Session(), settings.afdc_base_url, params=params,
                                       settings=settings, logger=logger, label="R2 AFDC")
        payload = response.json()
        mode = "REST API (developer.nlr.gov)"
    (out / "afdc_stations.json").write_text(json.dumps(payload))  # raw preserved (key never written)
    stations = payload.get("fuel_stations", [])
    expected = payload.get("total_results")
    logger.info("EXTRACT | source=R2 stations=%s total_results=%s", len(stations), expected)
    evidence = SourceEvidence("R2 AFDC registry", mode, expected=expected, received=len(stations),
                              complete=expected is not None and len(stations) == expected,
                              details={"snapshot_taken_utc": payload.get("snapshot_taken_utc", "live")})
    return stations, evidence


# ---------------------------------------------------------------- S1: status feed (REST API, simulated)
def extract_status_events(settings, raw_dir: Path, months: list[str], logger) -> tuple[list[dict], SourceEvidence]:
    out = _reset_dir(raw_dir / "status_feed")
    session = requests.Session()
    url = f"{settings.status_api_url}/status/events"
    events, per_month = [], []
    for month in months:
        page, expected, got = 1, None, 0
        while True:
            response = http_get_with_retry(session, url,
                                           params={"month": month, "page": page, "page_size": settings.page_size},
                                           settings=settings, logger=logger, label=f"S1 {month} page={page}")
            payload = response.json()
            (out / f"status_{month}_page_{page:03d}.json").write_text(json.dumps(payload))
            expected = payload["total_records"] if expected is None else expected
            events.extend(payload["data"])
            got += len(payload["data"])
            if not payload["has_more"]:
                break
            page += 1
        per_month.append({"month": month, "expected": expected, "received": got, "pages": page})
        logger.info("EXTRACT | source=S1 month=%s pages=%s received=%s total_records=%s", month, page, got, expected)
    summary_resp = http_get_with_retry(session, f"{settings.status_api_url}/uptime/summary", params=None,
                                       settings=settings, logger=logger, label="S1 uptime summary")
    (out / "uptime_summary.json").write_text(summary_resp.text)
    total_expected = sum(m["expected"] for m in per_month)
    evidence = SourceEvidence("S1 status feed (simulated)", "REST API (paginated, mock)",
                              expected=total_expected, received=len(events),
                              complete=all(m["expected"] == m["received"] for m in per_month),
                              details={"months": per_month, "operator_dashboard": summary_resp.json()})
    return events, evidence


# ---------------------------------------------------------------- S2: work orders (SQL, simulated)
def extract_work_orders(db_path: Path, raw_dir: Path, logger) -> tuple[pd.DataFrame, SourceEvidence]:
    out = _reset_dir(raw_dir / "work_orders")
    with sqlite3.connect(db_path) as con:
        work_orders = pd.read_sql("""
            SELECT work_order_id, charger_id, work_type, trigger, opened_at, closed_at,
                   action, resolution_code, linked_outage_id, data_origin
            FROM work_orders
            ORDER BY work_order_id
        """, con)
        expected = int(pd.read_sql("SELECT value FROM generation_manifest WHERE key='work_orders_rows'",
                                   con)["value"].iloc[0])
    work_orders.to_csv(out / "work_orders.csv", index=False)
    logger.info("EXTRACT | source=S2 rows=%s manifest_rows=%s", len(work_orders), expected)
    evidence = SourceEvidence("S2 work orders (simulated)", "SQL (SQLite)", expected=expected,
                              received=len(work_orders), complete=len(work_orders) == expected)
    return work_orders, evidence
