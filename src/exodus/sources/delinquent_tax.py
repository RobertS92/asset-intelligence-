"""Load delinquent tax rolls / tax-suit lists for Collin, Tarrant, Harris."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from exodus.common.config import DATA_DIR, ensure_data_dirs
from exodus.common.storage import scoring_path, write_parquet
from exodus.sources import register

SOURCE_KEY = "delinquent_tax"


@register(SOURCE_KEY)
def fetch(run_date: date) -> list[Path]:
    ensure_data_dirs()
    root = DATA_DIR / "raw" / SOURCE_KEY
    root.mkdir(parents=True, exist_ok=True)
    found = list(root.rglob("*.csv")) + list(root.rglob("*.parquet"))
    note_dir = root / run_date.isoformat()
    note_dir.mkdir(parents=True, exist_ok=True)
    note = note_dir / "ACCESS.txt"
    note.write_text(
        "Drop delinquent tax / tax-suit exports for Collin, Tarrant, Harris here.\n"
        f"Files found: {len(found)}\n"
    )
    return [note, *found]


def load_delinquencies() -> pd.DataFrame:
    root = DATA_DIR / "raw" / SOURCE_KEY
    frames: list[pd.DataFrame] = []
    if root.exists():
        for path in list(root.rglob("*.csv")) + list(root.rglob("*.parquet")):
            df = pd.read_csv(path) if path.suffix == ".csv" else pd.read_parquet(path)
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    write_parquet(out, scoring_path("delinquencies.parquet"))

    # Also emit DistressEvent rows for tax_delinquent / tax_suit when present
    events = []
    if "event_type" in out.columns and "event_date" in out.columns:
        events = out[["parcel_id", "event_type", "event_date"]].copy()
        events["source"] = SOURCE_KEY
        events["raw_ref"] = "delinquent_tax"
        write_parquet(events, scoring_path("distress_events.parquet"))
    return out
