"""Parcel feature table — property-level only (AGENTS.md §2)."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from exodus.common.schemas import ParcelFeatures


def build_parcel_features(
    parcels: pd.DataFrame,
    delinquencies: pd.DataFrame,
    distress_events: pd.DataFrame,
    scoring_date: date,
    *,
    horizons_months: tuple[int, ...] = (6, 12),
) -> pd.DataFrame:
    """
    Build feature rows as of scoring_date.
    Every feature uses only records dated strictly before scoring_date.
    """
    rows: list[dict[str, object]] = []
    if parcels.empty:
        return pd.DataFrame()

    delinq = delinquencies.copy() if not delinquencies.empty else pd.DataFrame()
    events = distress_events.copy() if not distress_events.empty else pd.DataFrame()

    if not delinq.empty and "as_of" in delinq.columns:
        delinq["as_of"] = pd.to_datetime(delinq["as_of"]).dt.date
        delinq = delinq[delinq["as_of"] < scoring_date]
    if not events.empty and "event_date" in events.columns:
        events["event_date"] = pd.to_datetime(events["event_date"]).dt.date
        events = events[events["event_date"] < scoring_date]

    for _, p in parcels.iterrows():
        pid = str(p["parcel_id"])
        county = str(p.get("county_fips", ""))
        d = delinq[delinq["parcel_id"].astype(str) == pid] if not delinq.empty else pd.DataFrame()
        e = events[events["parcel_id"].astype(str) == pid] if not events.empty else pd.DataFrame()

        months_delinquent = None
        amount_owed = None
        prior = False
        if not d.empty:
            latest = d.sort_values("as_of").iloc[-1]
            months_delinquent = float(latest.get("months_delinquent", 0) or 0)
            amount_owed = (
                float(latest.get("amount_owed_usd", 0) or 0)
                if "amount_owed_usd" in latest
                else None
            )
            prior = len(d) > 1

        assessed = float(p["assessed_value_usd"]) if pd.notna(p.get("assessed_value_usd")) else None
        ratio = None
        if amount_owed is not None and assessed and assessed > 0:
            ratio = amount_owed / assessed

        # Labels attached later via attach_labels() using future events only.
        _ = horizons_months
        feat = ParcelFeatures(
            parcel_id=pid,
            county_fips=county,
            scoring_date=scoring_date,
            months_delinquent=months_delinquent,
            amount_owed_usd=amount_owed,
            assessed_value_usd=assessed,
            owed_to_value_ratio=ratio,
            prior_delinquency=prior,
            purchase_year=int(p["purchase_year"]) if pd.notna(p.get("purchase_year")) else None,
            purchase_price_usd=(
                float(p["purchase_price_usd"]) if pd.notna(p.get("purchase_price_usd")) else None
            ),
            estimated_ltv=float(p["estimated_ltv"]) if pd.notna(p.get("estimated_ltv")) else None,
            hoa_lien=bool(p.get("hoa_lien", False)),
            mailing_out_of_state=bool(p.get("mailing_out_of_state", False)),
            utility_shutoff=bool(p.get("utility_shutoff", False)),
            code_violations=int(p.get("code_violations", 0) or 0),
            listing_vacant_remark=bool(p.get("listing_vacant_remark", False)),
            listing_expired=bool(p.get("listing_expired", False)),
            price_cut=bool(p.get("price_cut", False)),
            days_on_market=float(p["days_on_market"])
            if pd.notna(p.get("days_on_market"))
            else None,
            nearby_foreclosures=int(p.get("nearby_foreclosures", 0) or 0),
            label_6m=0,
            label_12m=0,
        )
        if not e.empty:
            types = set(e["event_type"].astype(str))
            if "mailing_moved_out_of_state" in types:
                feat.mailing_out_of_state = True
            if "hoa_lien" in types:
                feat.hoa_lien = True
            if "code_violation" in types:
                n_viol = int((e["event_type"] == "code_violation").sum())
                feat.code_violations = max(feat.code_violations, n_viol)
        rows.append(feat.model_dump(mode="json"))

    return pd.DataFrame(rows)


def attach_labels(
    features: pd.DataFrame,
    distress_events: pd.DataFrame,
    scoring_date: date,
) -> pd.DataFrame:
    """Set label_6m / label_12m from future distress events (post scoring_date)."""
    out = features.copy()
    if out.empty:
        return out
    events = distress_events.copy()
    if events.empty:
        out["label_6m"] = 0
        out["label_12m"] = 0
        return out
    events["event_date"] = pd.to_datetime(events["event_date"]).dt.date
    hit_types = {"tax_suit", "trustee_notice", "usps_vacant", "homestead_removed"}

    def _label(pid: str, months: int) -> int:
        end = scoring_date + timedelta(days=int(months * 30.44))
        ev = events[
            (events["parcel_id"].astype(str) == pid)
            & (events["event_date"] > scoring_date)
            & (events["event_date"] <= end)
            & (events["event_type"].isin(hit_types))
        ]
        return int(len(ev) > 0)

    out["label_6m"] = out["parcel_id"].astype(str).map(lambda p: _label(p, 6))
    out["label_12m"] = out["parcel_id"].astype(str).map(lambda p: _label(p, 12))
    return out


FEATURE_COLUMNS = [
    "months_delinquent",
    "amount_owed_usd",
    "assessed_value_usd",
    "owed_to_value_ratio",
    "prior_delinquency",
    "purchase_year",
    "purchase_price_usd",
    "estimated_ltv",
    "hoa_lien",
    "mailing_out_of_state",
    "utility_shutoff",
    "code_violations",
    "listing_vacant_remark",
    "listing_expired",
    "price_cut",
    "days_on_market",
    "nearby_foreclosures",
]
