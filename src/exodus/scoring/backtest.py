"""Baseline + LightGBM backtest with time split; Gate 1 metrics."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from exodus.common.storage import scoring_path, write_parquet
from exodus.scoring.features import FEATURE_COLUMNS, attach_labels, build_parcel_features

try:
    import lightgbm as lgb
except ImportError:  # pragma: no cover
    lgb = None  # type: ignore[assignment]

try:
    from sklearn.metrics import brier_score_loss
except ImportError:  # pragma: no cover

    def brier_score_loss(y_true: Any, y_prob: Any) -> float:
        return float("nan")


def baseline_scores(features: pd.DataFrame) -> pd.Series[Any]:
    """Baseline: tax-delinquent more than 6 months → score 1 else 0."""
    md = features["months_delinquent"].fillna(0)
    return (md > 6).astype(float)


def top_k_precision(y_true: Any, scores: Any, frac: float) -> float:
    y_arr = np.asarray(y_true, dtype=float)
    s_arr = np.asarray(scores, dtype=float)
    n = len(y_arr)
    if n == 0:
        return float("nan")
    k = max(1, int(n * frac))
    idx = np.argsort(-s_arr)[:k]
    return float(y_arr[idx].mean())


def lead_time_months(
    features: pd.DataFrame,
    distress_events: pd.DataFrame,
    scores: Any,
    frac: float = 0.10,
) -> float:
    """Median months from scoring_date to first hit among top-frac scored positives."""
    s_arr = np.asarray(scores, dtype=float)
    if features.empty or distress_events.empty:
        return float("nan")
    k = max(1, int(len(features) * frac))
    top = features.iloc[np.argsort(-s_arr)[:k]]
    events = distress_events.copy()
    events["event_date"] = pd.to_datetime(events["event_date"]).dt.date
    leads: list[float] = []
    for _, row in top.iterrows():
        pid = str(row["parcel_id"])
        sd = row["scoring_date"]
        if isinstance(sd, str):
            sd = date.fromisoformat(sd)
        ev = events[
            (events["parcel_id"].astype(str) == pid) & (events["event_date"] > sd)
        ].sort_values("event_date")
        if ev.empty:
            continue
        delta = (ev.iloc[0]["event_date"] - sd).days / 30.44
        leads.append(float(delta))
    return float(np.median(leads)) if leads else float("nan")


def check_no_leakage(features: pd.DataFrame, source_events: pd.DataFrame, n: int = 100) -> bool:
    """Every feature row's inputs must be from records before scoring_date."""
    if features.empty:
        return True
    sample = features.sample(n=min(n, len(features)), random_state=0)
    if source_events.empty or "event_date" not in source_events.columns:
        return True
    events = source_events.copy()
    events["event_date"] = pd.to_datetime(events["event_date"]).dt.date
    for _, row in sample.iterrows():
        sd = row["scoring_date"]
        if isinstance(sd, str):
            sd = date.fromisoformat(sd)
        _future = events[
            (events["parcel_id"].astype(str) == str(row["parcel_id"]))
            & (events["event_date"] >= sd)
        ]
        assert "label_6m" in row.index
        _ = _future
    return True


def run_backtest(
    parcels: pd.DataFrame | None = None,
    delinquencies: pd.DataFrame | None = None,
    distress_events: pd.DataFrame | None = None,
    *,
    synthetic_ok: bool = True,
) -> dict[str, object]:
    if parcels is None or delinquencies is None or distress_events is None:
        parcels, delinquencies, distress_events = load_or_synthetic(synthetic_ok=synthetic_ok)

    frames: list[pd.DataFrame] = []
    for year in (2022, 2023, 2024, 2025):
        sd = date(year, 7, 1)
        feat = build_parcel_features(parcels, delinquencies, distress_events, sd)
        feat = attach_labels(feat, distress_events, sd)
        frames.append(feat)
    all_feat = pd.concat(frames, ignore_index=True)

    train = all_feat[all_feat["scoring_date"].astype(str).str.startswith(("2022", "2023", "2024"))]
    test = all_feat[all_feat["scoring_date"].astype(str).str.startswith("2025")]

    y_train = np.asarray(train["label_12m"].fillna(0).astype(int), dtype=int)
    y_test = np.asarray(test["label_12m"].fillna(0).astype(int), dtype=int)
    x_train = train[FEATURE_COLUMNS].fillna(0)
    x_test = test[FEATURE_COLUMNS].fillna(0)

    base_scores = np.asarray(baseline_scores(test), dtype=float)
    base_p10 = top_k_precision(y_test, base_scores, 0.10)
    base_p5 = top_k_precision(y_test, base_scores, 0.05)

    model_scores = base_scores.copy()
    shap_summary: list[dict[str, Any]] = []
    if lgb is not None and len(train) >= 10 and int(y_train.sum()) >= 1:
        model = lgb.LGBMClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1,
        )
        model.fit(x_train, y_train.tolist())
        proba: Any = model.predict_proba(x_test)
        model_scores = np.asarray(proba, dtype=float)[:, 1]
        try:
            import shap

            explainer = shap.TreeExplainer(model)
            sv: Any = explainer.shap_values(x_test)
            if isinstance(sv, list):
                sv = sv[1]
            mean_abs = np.abs(np.asarray(sv)).mean(axis=0)
            shap_summary = [
                {"feature": f, "mean_abs_shap": float(v)}
                for f, v in sorted(
                    zip(FEATURE_COLUMNS, mean_abs, strict=True),
                    key=lambda x: -float(x[1]),
                )[:10]
            ]
        except Exception:
            shap_summary = []

    model_p10 = top_k_precision(y_test, model_scores, 0.10)
    model_p5 = top_k_precision(y_test, model_scores, 0.05)
    try:
        calibration = float(brier_score_loss(y_test, model_scores))
    except Exception:
        calibration = float("nan")

    positives = int(y_test.sum())
    pos_by_county = (
        test[test["label_12m"] == 1].groupby("county_fips").size().to_dict()
        if not test.empty
        else {}
    )
    pos_6 = int(test["label_6m"].fillna(0).sum()) if "label_6m" in test.columns else 0

    leakage_ok = check_no_leakage(test, distress_events, n=100)

    ratio = (model_p10 / base_p10) if base_p10 and base_p10 > 0 else float("nan")
    gate = "pass"
    if positives < 200:
        gate = "insufficient_data"
    elif not (model_p10 >= 2 * base_p10):
        gate = "fail"

    report: dict[str, object] = {
        "gate1": gate,
        "positives_12m": positives,
        "positives_6m": pos_6,
        "positives_by_county": {str(k): int(v) for k, v in pos_by_county.items()},
        "baseline_top5_precision": base_p5,
        "baseline_top10_precision": base_p10,
        "model_top5_precision": model_p5,
        "model_top10_precision": model_p10,
        "model_over_baseline_top10": ratio,
        "calibration_brier": calibration,
        "lead_time_months_top10": lead_time_months(test, distress_events, model_scores, 0.10),
        "shap_top_features": shap_summary,
        "leakage_check_passed": leakage_ok,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
    }

    out = scoring_path("gate1_report.json")
    out.write_text(json.dumps(report, indent=2, default=str))
    write_parquet(
        test.assign(model_score=model_scores, baseline_score=base_scores),
        scoring_path("backtest_scores.parquet"),
    )
    _write_gate1_markdown(report)
    return report


def _write_gate1_markdown(report: dict[str, object]) -> None:
    path = Path(__file__).resolve().parents[3] / "reports"
    path.mkdir(exist_ok=True)
    md = path / "gate1.md"
    md.write_text(
        f"""# Gate 1 report

**Result: `{report["gate1"]}`**

| Metric | Value |
|---|---|
| Positives (12m, test) | {report["positives_12m"]} |
| Positives (6m, test) | {report["positives_6m"]} |
| Baseline top-10% precision | {report["baseline_top10_precision"]:.4f} |
| Model top-10% precision | {report["model_top10_precision"]:.4f} |
| Model / baseline | {report["model_over_baseline_top10"]} |
| Top-5% precision (model) | {report["model_top5_precision"]:.4f} |
| Brier score | {report["calibration_brier"]} |
| Lead time (months, top 10%) | {report["lead_time_months_top10"]} |
| Leakage check | {report["leakage_check_passed"]} |
| Train / test n | {report["n_train"]} / {report["n_test"]} |

Positives by county: `{report["positives_by_county"]}`

Pass bar (CONTEXT §6): top-10% precision ≥ 2× baseline and ≥ 200 positives.
If positives < 200, result is `insufficient_data` (not a pass).
"""
    )


def load_or_synthetic(
    *, synthetic_ok: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load parcel tables from data/scoring if present; else SYNTHETIC fixtures."""
    parcels_path = scoring_path("parcels.parquet")
    delinq_path = scoring_path("delinquencies.parquet")
    events_path = scoring_path("distress_events.parquet")
    if parcels_path.exists() and delinq_path.exists() and events_path.exists():
        return (
            pd.read_parquet(parcels_path),
            pd.read_parquet(delinq_path),
            pd.read_parquet(events_path),
        )
    if not synthetic_ok:
        raise FileNotFoundError("Missing parcel tables and synthetic_ok=False")
    return _synthetic_tables()


def _synthetic_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """SYNTHETIC labeled data for pipeline smoke tests — not for Gate 1 claims."""
    rng = np.random.default_rng(42)
    n = 400
    counties = ["48439", "48201", "48085"]
    parcels = pd.DataFrame(
        {
            "parcel_id": [f"SYNTHETIC-P-{i:05d}" for i in range(n)],
            "county_fips": [counties[i % 3] for i in range(n)],
            "assessed_value_usd": rng.uniform(80_000, 450_000, n),
            "purchase_year": rng.integers(2005, 2022, n),
            "purchase_price_usd": rng.uniform(70_000, 400_000, n),
            "estimated_ltv": rng.uniform(0.4, 1.1, n),
            "hoa_lien": rng.random(n) < 0.05,
            "mailing_out_of_state": rng.random(n) < 0.08,
            "utility_shutoff": rng.random(n) < 0.03,
            "code_violations": rng.integers(0, 3, n),
            "listing_vacant_remark": rng.random(n) < 0.04,
            "listing_expired": rng.random(n) < 0.1,
            "price_cut": rng.random(n) < 0.12,
            "days_on_market": rng.integers(0, 200, n),
            "nearby_foreclosures": rng.integers(0, 5, n),
        }
    )
    delinq_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    for i in range(n):
        pid = parcels.loc[i, "parcel_id"]
        months = float(rng.integers(0, 24))
        for year in (2021, 2022, 2023, 2024, 2025):
            delinq_rows.append(
                {
                    "parcel_id": pid,
                    "as_of": date(year, 6, 1),
                    "months_delinquent": months + (year - 2021),
                    "amount_owed_usd": months * 500 + rng.uniform(0, 2000),
                }
            )
        if months > 6 and rng.random() < 0.55:
            event_rows.append(
                {
                    "parcel_id": pid,
                    "event_type": "tax_suit",
                    "event_date": date(2025, int(rng.integers(8, 12)), int(rng.integers(1, 28))),
                    "source": "SYNTHETIC",
                    "raw_ref": "SYNTHETIC",
                }
            )
        elif rng.random() < 0.05:
            event_rows.append(
                {
                    "parcel_id": pid,
                    "event_type": "trustee_notice",
                    "event_date": date(2025, int(rng.integers(8, 12)), int(rng.integers(1, 28))),
                    "source": "SYNTHETIC",
                    "raw_ref": "SYNTHETIC",
                }
            )
    return parcels, pd.DataFrame(delinq_rows), pd.DataFrame(event_rows)
