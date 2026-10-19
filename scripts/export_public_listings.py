#!/usr/bin/env python3
"""Export Auction Finder listings to web/public/data/listings.json (no owner PII)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "scoring" / "listings.parquet"
DEST = ROOT / "web" / "public" / "data" / "listings.json"

# Public auction-feed fields only. Never include owner name / mailing address.
PUBLIC_COLS = [
    "listing_id",
    "source",
    "source_key",
    "asset_type",
    "sale_type",
    "sale_date",
    "status",
    "county_fips",
    "address",
    "parcel_id",
    "vin",
    "min_bid_usd",
    "redemption_days",
    "url",
    "cause_no",
    "account_no",
    "make",
    "model",
    "year",
    "storage_facility",
    "notes",
    "lat",
    "lon",
]


def main() -> int:
    if not SRC.exists():
        print(f"Missing {SRC}; run `uv run python -m exodus.cli normalize` first.", file=sys.stderr)
        return 1
    df = pd.read_parquet(SRC)
    cols = [c for c in PUBLIC_COLS if c in df.columns]
    records = json.loads(df[cols].to_json(orient="records", date_format="iso", default_handler=str))
    payload = {
        "generated_from": "data/scoring/listings.parquet (owner PII never exported)",
        "count": len(records),
        "listings": records,
    }
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {DEST} ({len(records)} listings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
