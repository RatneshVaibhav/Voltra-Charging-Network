"""Refresh the committed source snapshot from the live sources (optional; the pipeline's live mode does this per run).

    python scripts/refresh_source_snapshot.py

Writes data/source_snapshot/{sessions/*.csv, hf_tree_snapshot.json, afdc_stations_snapshot.json}. Every downloaded
file is verified against the Hugging Face tree API (size + git-blob SHA-1) before it replaces the snapshot.
"""
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.config import SNAPSHOT_DIR, Settings  # noqa: E402
from pipeline.extract import extract_afdc, extract_sessions  # noqa: E402

KEEP = ["id", "station_name", "street_address", "city", "state", "zip", "latitude", "longitude", "status_code",
        "ev_network", "ev_network_ids", "ev_dc_fast_num", "ev_level2_evse_num", "date_last_confirmed", "updated_at",
        "open_date", "facility_type"]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    log, s = logging.getLogger("refresh"), Settings.from_env()
    tmp = Path("data/raw/_refresh")
    files, ev = extract_sessions(s, tmp, SNAPSHOT_DIR, offline=False, logger=log)
    if not ev.complete:
        raise SystemExit(f"session download incomplete: {ev.received}/{ev.expected} verified — snapshot NOT replaced")
    stations, ev2 = extract_afdc(s, tmp, SNAPSHOT_DIR, offline=False, logger=log)
    if not ev2.complete:
        raise SystemExit("AFDC response incomplete — snapshot NOT replaced")
    for f in files:
        (SNAPSHOT_DIR / "sessions" / f.name).write_bytes(f.read_bytes())
    (SNAPSHOT_DIR / "hf_tree_snapshot.json").write_text((tmp / "sessions" / "_hf_tree.json").read_text())
    out = {"snapshot_taken_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "total_results": len(stations),
           "note": "Trimmed to the fields this project uses; every station record is kept.",
           "fuel_stations": [{k: st.get(k) for k in KEEP} for st in stations]}
    (SNAPSHOT_DIR / "afdc_stations_snapshot.json").write_text(json.dumps(out, separators=(",", ":")))
    log.info("REFRESH | snapshot replaced: %s files, %s stations", len(files), len(stations))
