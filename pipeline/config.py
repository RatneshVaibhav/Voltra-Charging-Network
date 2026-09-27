"""Configuration.

Two kinds of configuration are deliberately kept apart:
- Environment settings (WHERE/HOW the pipeline runs): URLs, API key, retries, page size. From env / `.env`.
- Business definitions (WHAT the KPI means): `config/kpi_definitions.json`, versioned. Never read from env.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KPI_DEFINITIONS_PATH = PROJECT_ROOT / "config" / "kpi_definitions.json"
SNAPSHOT_DIR = PROJECT_ROOT / "data" / "source_snapshot"
SIM_DIR = PROJECT_ROOT / "data" / "simulated_client_systems"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
LOG_DIR = PROJECT_ROOT / "logs"


def load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    """Minimal `.env` loader (KEY=VALUE per line). Variables already set in the environment win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    afdc_api_key: str
    afdc_base_url: str
    afdc_states: str
    afdc_ev_network: str
    hf_dataset: str
    hf_folder: str
    status_api_url: str
    start_mock_api: bool
    max_retries: int
    retry_base_seconds: float
    request_timeout: float
    page_size: int
    sim_seed: int
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            afdc_api_key=os.getenv("AFDC_API_KEY", "DEMO_KEY"),
            afdc_base_url=os.getenv("AFDC_BASE_URL", "https://developer.nlr.gov/api/alt-fuel-stations/v1.json"),
            afdc_states=os.getenv("AFDC_STATES", "TN,AL,KY,MS,GA,VA,NC"),
            afdc_ev_network=os.getenv("AFDC_EV_NETWORK", "ChargePoint Network"),
            hf_dataset=os.getenv("HF_DATASET", "shadenn/EV_Charging_demand"),
            hf_folder=os.getenv("HF_FOLDER", "raw_charging_stations"),
            status_api_url=os.getenv("STATUS_API_URL", "http://127.0.0.1:8001"),
            start_mock_api=_as_bool(os.getenv("START_MOCK_API"), True),
            max_retries=int(os.getenv("MAX_RETRIES", "4")),
            retry_base_seconds=float(os.getenv("RETRY_BASE_SECONDS", "1")),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
            page_size=int(os.getenv("PAGE_SIZE", "1000")),
            sim_seed=int(os.getenv("SIM_SEED", "42")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


def load_kpi_definitions(path: Path = KPI_DEFINITIONS_PATH) -> dict:
    """Load the versioned business definitions. These are never overridden by environment variables."""
    with open(path) as fh:
        return json.load(fh)
