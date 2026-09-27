"""SAVE stage — publish the whole run partition atomically.

All outputs are written to a temporary directory next to the target, then swapped in: an existing partition for
the same run date is moved aside and deleted only after the new one is in place. A rerun for the same run date
therefore replaces (never appends to) the previous output, and a crash mid-write never leaves a half partition.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pandas as pd


def _write(path: Path, obj) -> None:
    if isinstance(obj, pd.DataFrame):
        obj.to_csv(path, index=False)
    elif isinstance(obj, (dict, list)):
        path.write_text(json.dumps(obj, indent=2, default=str))
    else:
        path.write_text(str(obj))


def publish_partition(processed_dir: Path, run_date: str, outputs: dict, logger) -> Path:
    processed_dir.mkdir(parents=True, exist_ok=True)
    target = processed_dir / f"run_date={run_date}"
    tmp = Path(tempfile.mkdtemp(prefix=f".tmp_run_date={run_date}_", dir=processed_dir))
    try:
        for name, obj in outputs.items():
            _write(tmp / name, obj)
        backup = None
        if target.exists():
            backup = processed_dir / f".old_run_date={run_date}"
            if backup.exists():
                shutil.rmtree(backup)
            target.rename(backup)
        tmp.rename(target)
        if backup is not None:
            shutil.rmtree(backup)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    logger.info("SAVE | published partition=%s files=%s (atomic swap)", target, len(outputs))
    return target
