"""Load appraisal-district certified rolls (manual bulk export path).

Access is manual per config/sources.yaml. This module documents the expected
schema and loads local exports dropped into data/raw/cad_rolls/<county>/.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from exodus.common.config import DATA_DIR, ensure_data_dirs
from exodus.common.storage import scoring_path, write_parquet
from exodus.sources import register

SOURCE_KEY = "cad_rolls"

# Expected columns after county-specific adapters normalize
PARCEL_COLUMNS = [
    "parcel_id",
    "account_no",
    "county_fips",
    "address",
    "assessed_value_usd",
    "purchase_year",
    "purchase_price_usd",
    "owner_name",  # PII — never leave data/
    "mailing_address",  # PII
]


@register(SOURCE_KEY)
def fetch(run_date: date) -> list[Path]:
    """
    CAD rolls are not scraped. Place bulk exports under:
      data/raw/cad_rolls/collin|tarrant|harris/<year>.csv
    This fetch verifies presence and copies a manifest entry.
    """
    ensure_data_dirs()
    root = DATA_DIR / "raw" / SOURCE_KEY
    root.mkdir(parents=True, exist_ok=True)
    found = list(root.rglob("*.csv")) + list(root.rglob("*.parquet"))
    manifest = root / run_date.isoformat()
    manifest.mkdir(parents=True, exist_ok=True)
    note = manifest / "ACCESS.txt"
    note.write_text(
        "CAD certified rolls require bulk export / open-records request.\n"
        "Collin / Tarrant / Harris 2022–2026: drop normalized CSV/Parquet here.\n"
        "See CONTEXT.md open questions for access method and cost.\n"
        f"Files found: {len(found)}\n"
    )
    return [note, *found]


def load_rolls() -> pd.DataFrame:
    root = DATA_DIR / "raw" / SOURCE_KEY
    frames: list[pd.DataFrame] = []
    if not root.exists():
        return pd.DataFrame()
    for path in list(root.rglob("*.csv")) + list(root.rglob("*.parquet")):
        df = pd.read_csv(path, dtype=str) if path.suffix == ".csv" else pd.read_parquet(path)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    # Strip PII before writing to scoring
    scoring = out.drop(columns=[c for c in ("owner_name", "mailing_address") if c in out.columns])
    write_parquet(scoring, scoring_path("parcels.parquet"))
    return scoring
