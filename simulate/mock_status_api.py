"""S1 — SIMULATED charger status feed (the operator's back office), served as a paginated REST API.

Endpoints
  GET /health
  GET /status/events?month=YYYY-MM&page=1&page_size=1000   -> {data, page, page_size, has_more, total_records}
  GET /uptime/summary                                       -> the operator dashboard number ("99% uptime")

Deliberate behaviour (FlashEats pattern): the first request for page 3 returns HTTP 500 and the first request for
page 5 returns HTTP 429 with retry_after_seconds — clients must retry. Set MOCK_API_OUTAGE=1 to make every
events request fail (chaos demo). Run standalone:  python simulate/mock_status_api.py  (port 8001)
"""
from __future__ import annotations

import gzip
import json
import os
from collections import defaultdict
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request

DATA = Path(__file__).resolve().parents[1] / "data" / "simulated_client_systems" / "status_events.json.gz"
app = Flask(__name__)
EVENTS = json.loads(gzip.decompress(DATA.read_bytes()))
BY_MONTH: dict[str, list] = defaultdict(list)
for event in EVENTS:
    BY_MONTH[event["timestamp"][:7]].append(event)
FIRST_HITS: set[int] = set()


def _operator_dashboard() -> dict:
    """NOC definition: a port is 'up' unless Faulted; Unavailable periods (maintenance, awaiting parts) are excluded."""
    df = pd.DataFrame(EVENTS)
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True)
    faulted = life = 0.0
    for _, g in df.sort_values("ts").groupby("port_id"):
        life += (g["ts"].max() - g["ts"].min()).total_seconds() / 60
        start = None
        for row in g.itertuples():
            if row.status == "Faulted" and start is None:
                start = row.ts
            elif row.status == "Available" and start is not None:
                faulted += (row.ts - start).total_seconds() / 60
                start = None
    return {"definition": "port online and not Faulted; scheduled maintenance and awaiting-parts time excluded",
            "network_uptime_pct": round(100 * (1 - faulted / life), 2), "ports": int(df["port_id"].nunique()),
            "data_origin": "simulated"}


DASHBOARD = _operator_dashboard()


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "voltra-status-feed (simulated)"})


@app.get("/status/events")
def events():
    if os.getenv("MOCK_API_OUTAGE") == "1":
        return jsonify({"error": "status feed unavailable", "retryable": True}), 503
    month = request.args.get("month", "")
    page = max(1, int(request.args.get("page", 1)))
    page_size = min(5000, max(1, int(request.args.get("page_size", 1000))))
    if page in (3, 5) and page not in FIRST_HITS:
        FIRST_HITS.add(page)
        if page == 3:
            return jsonify({"error": "temporary upstream failure", "retryable": True}), 500
        return jsonify({"error": "rate limit exceeded", "retry_after_seconds": 1}), 429
    rows = BY_MONTH.get(month, [])
    start, end = (page - 1) * page_size, page * page_size
    return jsonify({"data": rows[start:end], "page": page, "page_size": page_size,
                    "has_more": end < len(rows), "total_records": len(rows)})


@app.get("/uptime/summary")
def uptime_summary():
    return jsonify(DASHBOARD)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("MOCK_API_PORT", "8001")), debug=False)
