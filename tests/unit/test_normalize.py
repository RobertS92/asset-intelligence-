"""Normalize + dedupe + status history."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from exodus.auctions.normalize import dedupe, merge_status_history, run_normalize
from exodus.common.storage import read_parquet


def test_normalize_idempotent_and_no_dupes(tmp_path: Path, monkeypatch: object) -> None:
    # Run against fixtures
    out1 = run_normalize(use_fixtures_if_empty=True, as_of=date(2026, 10, 19))
    df1 = read_parquet(out1)
    assert not df1.empty
    assert df1["listing_id"].duplicated().sum() == 0

    out2 = run_normalize(use_fixtures_if_empty=True, as_of=date(2026, 10, 19))
    df2 = read_parquet(out2)
    assert set(df1["listing_id"]) == set(df2["listing_id"])
    assert len(df1) == len(df2)


def test_status_history_on_change() -> None:
    prev = pd.DataFrame(
        {
            "listing_id": ["a", "b"],
            "status": ["for_sale", "for_sale"],
            "source": ["s", "s"],
        }
    )
    cur = pd.DataFrame(
        {
            "listing_id": ["a", "b"],
            "status": ["withdrawn", "for_sale"],
            "source": ["s", "s"],
        }
    )
    hist = merge_status_history(prev, cur, as_of=date(2026, 10, 19))
    assert len(hist) == 1
    assert hist.iloc[0]["old_status"] == "for_sale"
    assert hist.iloc[0]["new_status"] == "withdrawn"


def test_dedupe_keeps_latest() -> None:
    df = pd.DataFrame(
        {
            "listing_id": ["x", "x"],
            "status": ["scheduled", "for_sale"],
            "fetched_at": ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"],
        }
    )
    out = dedupe(df)
    assert len(out) == 1
    assert out.iloc[0]["status"] == "for_sale"
