import logging
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.config import load_kpi_definitions  # noqa: E402


@pytest.fixture
def log():
    return logging.getLogger("tests")


@pytest.fixture
def defs():
    return load_kpi_definitions()


def session(sid, charger, port, start, minutes, kwh, peak=60.0, name="ORG / STATION 1"):
    s = pd.Timestamp(start, tz="UTC")
    return {"provider_id": "ChargePoint Network", "source_station_id": "", "source_site_id": "", "charger_id": charger,
            "evse_id": charger, "evse_name": name, "port_id": port, "connector_id": "1", "session_id": sid,
            "session_start": s, "session_end": s + pd.Timedelta(minutes=minutes), "session_error": "",
            "energy_kwh": kwh, "peak_power_kw": peak, "payment_method": "membership", "payment_other": "",
            "eMI3 Port id": "", "source_file": "t.csv"}
