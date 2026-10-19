"""Geocode parcels/listings → tract GEOID + H3 resolution-8; link by account then address."""

from __future__ import annotations

from typing import Any

import httpx
import pandas as pd

try:
    import h3
except ImportError:  # pragma: no cover
    h3 = None  # type: ignore

CENSUS_GEOCODER = "https://geocoding.geo.census.gov/geocoder/geographies/address"


def h3_r8(lat: float, lon: float) -> str | None:
    if h3 is None:
        return None
    # h3 v3 vs v4 API
    if hasattr(h3, "latlng_to_cell"):
        return str(h3.latlng_to_cell(lat, lon, 8))
    return str(h3.geo_to_h3(lat, lon, 8))


def geocode_address(
    street: str,
    city: str = "",
    state: str = "TX",
    zipcode: str = "",
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Return {lat, lon, tract_geoid, h3_r8} via Census Geocoder."""
    params = {
        "street": street,
        "city": city,
        "state": state,
        "zip": zipcode,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "format": "json",
    }
    own = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        resp = client.get(CENSUS_GEOCODER, params=params)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if own:
            client.close()

    matches = data.get("result", {}).get("addressMatches", [])
    if not matches:
        return {}
    m0 = matches[0]
    coords = m0.get("coordinates", {})
    lat = float(coords.get("y", 0) or 0)
    lon = float(coords.get("x", 0) or 0)
    geos = m0.get("geographies", {})
    tracts = geos.get("Census Tracts") or geos.get("Census Tracts") or []
    tract_geoid = None
    if tracts:
        tract_geoid = tracts[0].get("GEOID") or tracts[0].get("TRACT")
    return {
        "lat": lat,
        "lon": lon,
        "tract_geoid": tract_geoid,
        "h3_r8": h3_r8(lat, lon) if lat and lon else None,
        "matched_address": m0.get("matchedAddress"),
    }


def link_listings_to_parcels(
    listings: pd.DataFrame,
    parcels: pd.DataFrame,
) -> pd.DataFrame:
    """Link by account_no / parcel_id first, then by normalized address."""
    out = listings.copy()
    if out.empty:
        return out
    out["parcel_id_resolved"] = out.get("parcel_id")

    if not parcels.empty and "account_no" in parcels.columns:
        acct_map = parcels.drop_duplicates("account_no").set_index("account_no")["parcel_id"]
        if "account_no" in out.columns:
            mapped = out["account_no"].map(acct_map)
            out["parcel_id_resolved"] = out["parcel_id_resolved"].fillna(mapped)

    if not parcels.empty and "address_norm" in parcels.columns and "address" in out.columns:
        addr_map = parcels.drop_duplicates("address_norm").set_index("address_norm")["parcel_id"]
        need = out["parcel_id_resolved"].isna()
        norms = out.loc[need, "address"].fillna("").str.upper().str.replace(r"\s+", " ", regex=True)
        out.loc[need, "parcel_id_resolved"] = norms.map(addr_map)

    return out


def geocode_listings(listings: pd.DataFrame, *, limit: int | None = None) -> pd.DataFrame:
    """Add tract_geoid and h3_r8 columns for rows with an address."""
    out = listings.copy()
    if out.empty or "address" not in out.columns:
        return out
    out["tract_geoid"] = None
    out["h3_r8"] = None
    out["lat"] = None
    out["lon"] = None
    rows = out[out["address"].notna()]
    if limit is not None:
        rows = rows.head(limit)
    with httpx.Client(timeout=30.0) as client:
        for idx, row in rows.iterrows():
            addr = str(row["address"])
            # crude split: "123 Main St, City, Texas 76018"
            parts = [p.strip() for p in addr.split(",")]
            street = parts[0] if parts else addr
            city = parts[1] if len(parts) > 1 else ""
            state = "TX"
            zipcode = ""
            if len(parts) > 2:
                tail = parts[-1]
                for tok in tail.split():
                    if tok.isdigit() and len(tok) == 5:
                        zipcode = tok
            try:
                geo = geocode_address(
                    street, city=city, state=state, zipcode=zipcode, client=client
                )
            except Exception:
                geo = {}
            if geo:
                out.at[idx, "tract_geoid"] = geo.get("tract_geoid")
                out.at[idx, "h3_r8"] = geo.get("h3_r8")
                out.at[idx, "lat"] = geo.get("lat")
                out.at[idx, "lon"] = geo.get("lon")
    return out
