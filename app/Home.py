"""Exodus Asset Signals — local Streamlit map + listings table."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
LISTINGS = ROOT / "data" / "scoring" / "listings.parquet"

st.set_page_config(page_title="Exodus Asset Signals", layout="wide")
st.title("Exodus Asset Signals")
st.caption("Auction Finder · Risk Map (local). Demographic data never enters this view.")

if not LISTINGS.exists():
    st.warning(
        "No listings yet. Run `uv run python -m exodus.cli normalize` "
        "(uses fixtures if raw data is empty)."
    )
    st.stop()

df = pd.read_parquet(LISTINGS)

# Filters
counties = sorted({c for c in df.get("county_fips", pd.Series(dtype=str)).dropna().unique()})
county = st.sidebar.multiselect("County FIPS", counties, default=counties)
asset_types = sorted({a for a in df.get("asset_type", pd.Series(dtype=str)).dropna().unique()})
assets = st.sidebar.multiselect("Asset type", asset_types, default=asset_types)
statuses = sorted({s for s in df.get("status", pd.Series(dtype=str)).dropna().unique()})
status = st.sidebar.multiselect("Status", statuses, default=statuses)

view = df.copy()
if county:
    view = view[view["county_fips"].isin(county)]
if assets:
    view = view[view["asset_type"].isin(assets)]
if status:
    view = view[view["status"].isin(status)]

st.subheader("Listings")
st.metric("Count", len(view))

# Map pins when lat/lon present; otherwise show address-only table
if {"lat", "lon"}.issubset(view.columns) and view[["lat", "lon"]].notna().any().any():
    map_df = view.dropna(subset=["lat", "lon"])[["lat", "lon"]].rename(
        columns={"lat": "latitude", "lon": "longitude"}
    )
    st.map(map_df)
else:
    st.info("No geocoded coordinates yet. Showing table only. Run resolve/geocode after CAD rolls load.")

cols = [
    c
    for c in [
        "sale_date",
        "status",
        "asset_type",
        "sale_type",
        "county_fips",
        "address",
        "account_no",
        "cause_no",
        "vin",
        "make",
        "model",
        "year",
        "storage_facility",
        "url",
        "source",
    ]
    if c in view.columns
]
st.dataframe(view[cols].sort_values(by="sale_date", ascending=True, na_position="last"), use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("Hard rules: no owner PII in digests; no demographics in scoring.")
