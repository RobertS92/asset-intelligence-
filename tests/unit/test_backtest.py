"""Backtest leakage check + Gate 1 report path."""

from __future__ import annotations

from exodus.scoring.backtest import check_no_leakage, run_backtest


def test_backtest_runs_on_synthetic() -> None:
    report = run_backtest(synthetic_ok=True)
    assert "gate1" in report
    assert report["gate1"] in {"pass", "fail", "insufficient_data"}
    assert report["leakage_check_passed"] is True
    assert "positives_12m" in report
    assert "model_top10_precision" in report


def test_leakage_sample() -> None:
    from datetime import date

    import pandas as pd

    features = pd.DataFrame(
        {
            "parcel_id": [f"p{i}" for i in range(100)],
            "scoring_date": [date(2025, 7, 1)] * 100,
            "label_6m": [0] * 100,
        }
    )
    events = pd.DataFrame(
        {
            "parcel_id": ["p0"],
            "event_date": [date(2025, 9, 1)],
            "event_type": ["tax_suit"],
        }
    )
    assert check_no_leakage(features, events, n=100) is True
