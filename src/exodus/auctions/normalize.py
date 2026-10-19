"""Normalize + dedupe listings; track status history → data/scoring/listings.parquet."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from exodus.common.config import DATA_DIR, ensure_data_dirs
from exodus.common.schemas import Listing
from exodus.common.storage import read_parquet, scoring_path, write_parquet
from exodus.extract import collin_taxsale as collin_taxsale
from exodus.extract import harris_so_vehicles as harris_so_vehicles
from exodus.extract import harris_taxsale as harris_taxsale
from exodus.extract import houston_pd_vehicles as houston_pd_vehicles
from exodus.extract import tarrant_taxsale as tarrant_taxsale


def listings_to_frame(listings: list[Listing]) -> pd.DataFrame:
    rows = [li.model_dump(mode="json") for li in listings]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # Ensure url is string
    if "url" in df.columns:
        df["url"] = df["url"].astype(str)
    return df


def collect_from_raw(raw_root: Path | None = None) -> list[Listing]:
    """Parse all known raw artifacts under data/raw (and fall back to fixtures)."""
    ensure_data_dirs()
    root = raw_root or (DATA_DIR / "raw")
    listings: list[Listing] = []

    # Tarrant
    tarrant_dir = root / "tarrant_constable3_taxsale"
    if tarrant_dir.exists():
        for html in tarrant_dir.rglob("*.html"):
            if html.name.startswith("index"):
                continue
            if "FAILED" in html.name:
                continue
            tables, writs = tarrant_taxsale.parse_page_path(
                html,
                page_url=f"{tarrant_taxsale.BASE_URL}{html.name}",
            )
            listings.extend(tables)
            listings.extend(writs)

    # Houston PD
    houston_dir = root / "houston_pd_vehicle_auction"
    if houston_dir.exists():
        for html in houston_dir.rglob("*Scheduled*"):
            if html.suffix.lower() in {".htm", ".html"}:
                listings.extend(houston_pd_vehicles.parse_page_path(html))

    # Harris SO
    harris_so = root / "harris_so_vehicle_auction"
    if harris_so.exists():
        for pdf in harris_so.rglob("*.pdf"):
            listings.extend(harris_so_vehicles.parse_pdf(pdf))

    # Harris tax sale
    harris_tax = root / "harris_taxsale"
    if harris_tax.exists():
        for path in list(harris_tax.rglob("*.html")) + list(harris_tax.rglob("*.pdf")):
            if "FAILED" in path.name:
                continue
            listings.extend(harris_taxsale.parse_path(path, page_url=f"file://{path}"))

    # Collin
    collin = root / "collin_taxsale"
    if collin.exists():
        for path in collin.rglob("*.html"):
            if "FAILED" in path.name:
                continue
            listings.extend(collin_taxsale.parse_path(path, page_url=f"file://{path}"))

    return listings


def collect_from_fixtures(fixtures_root: Path) -> list[Listing]:
    listings: list[Listing] = []
    tarrant = fixtures_root / "tarrant_constable3_taxsale" / "2026-11-03.html"
    if tarrant.exists():
        url = (
            "https://www.tarrantcountytx.gov/en/constables/constable-3/"
            "delinquent-tax-sales/monthly-tax-sales-listings/november-3--2026.html"
        )
        tables, writs = tarrant_taxsale.parse_page_path(tarrant, page_url=url)
        listings.extend(tables)
        listings.extend(writs)

    houston = fixtures_root / "houston_pd_vehicle_auction" / "Vehicles_Scheduled_For_Auction.htm"
    if houston.exists():
        listings.extend(houston_pd_vehicles.parse_page_path(houston))

    harris_pdf = fixtures_root / "harris_so_vehicle_auction" / "HC_Auctions_Jan-Mar_2026.pdf"
    if harris_pdf.exists():
        listings.extend(harris_so_vehicles.parse_pdf(harris_pdf))

    return listings


def merge_status_history(
    previous: pd.DataFrame,
    current: pd.DataFrame,
    as_of: date | None = None,
) -> pd.DataFrame:
    """Return history rows for status changes."""
    as_of = as_of or date.today()
    if previous.empty or current.empty or "listing_id" not in previous.columns:
        return pd.DataFrame(
            columns=["listing_id", "old_status", "new_status", "changed_at", "source"]
        )
    prev = previous.set_index("listing_id")["status"]
    cur = current.set_index("listing_id")["status"]
    common = prev.index.intersection(cur.index)
    rows = []
    for lid in common:
        old, new = prev.loc[lid], cur.loc[lid]
        if old != new:
            src = current.set_index("listing_id").loc[lid, "source"]
            if isinstance(src, pd.Series):
                src = src.iloc[0]
            rows.append(
                {
                    "listing_id": lid,
                    "old_status": old,
                    "new_status": new,
                    "changed_at": as_of.isoformat(),
                    "source": src,
                }
            )
    return pd.DataFrame(rows)


def dedupe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    # Prefer latest fetched_at per listing_id
    if "fetched_at" in df.columns:
        df = df.sort_values("fetched_at")
    out = df.drop_duplicates(subset=["listing_id"], keep="last").reset_index(drop=True)
    return out


def run_normalize(
    *,
    use_fixtures_if_empty: bool = True,
    fixtures_root: Path | None = None,
    as_of: date | None = None,
) -> Path:
    ensure_data_dirs()
    listings = collect_from_raw()
    if not listings and use_fixtures_if_empty:
        root = fixtures_root or Path(__file__).resolve().parents[3] / "tests" / "fixtures"
        listings = collect_from_fixtures(root)

    current = dedupe(listings_to_frame(listings))
    out = scoring_path("listings.parquet")
    hist_path = scoring_path("listing_status_history.parquet")

    previous = read_parquet(out)
    hist_new = merge_status_history(previous, current, as_of=as_of)
    if hist_path.exists():
        hist_old = read_parquet(hist_path)
        hist = pd.concat([hist_old, hist_new], ignore_index=True)
    else:
        hist = hist_new
    if not hist.empty:
        write_parquet(hist, hist_path)

    # Idempotent write: if identical content, still rewrite but stable ids preserved
    write_parquet(current, out)
    # Also stamp a run marker
    marker = scoring_path("listings_normalized_at.txt")
    marker.write_text(datetime.now(UTC).isoformat())
    return out
