"""Parse Collin County tax-sale listings."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup

from exodus.common.schemas import Listing, make_listing_id, map_status

SOURCE = "collin_taxsale"
COUNTY_FIPS = "48085"
DEFAULT_REDEMPTION_DAYS = 180


def parse_html(
    html: str,
    *,
    page_url: str,
    sale_date: date | None = None,
    fetched_at: datetime | None = None,
    raw_ref: str = "",
) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    fetched = fetched_at or datetime.utcnow()
    listings: list[Listing] = []
    for table in soup.find_all("table"):
        headers = [
            c.get_text(strip=True).lower()
            for c in (table.find("tr").find_all(["td", "th"]) if table.find("tr") else [])
        ]
        if not any("account" in h or "cause" in h or "property" in h for h in headers):
            continue
        colmap: dict[str, int] = {}
        for i, h in enumerate(headers):
            if "cause" in h:
                colmap["cause"] = i
            elif "account" in h or "prop" in h or "pid" in h:
                colmap["account"] = i
            elif "status" in h:
                colmap["status"] = i
            elif "address" in h or "situs" in h:
                colmap["address"] = i
        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            account = cells[colmap.get("account", 0)]
            if not account or account.lower() in headers:
                continue
            cause = cells[colmap["cause"]] if "cause" in colmap else None
            status_raw = cells[colmap["status"]] if "status" in colmap else "For Sale"
            try:
                status = map_status(status_raw)
            except ValueError:
                status = "for_sale"
            address = cells[colmap["address"]] if "address" in colmap else None
            source_key = f"{cause or ''}|{account}"
            listings.append(
                Listing(
                    listing_id=make_listing_id(SOURCE, source_key),
                    source=SOURCE,
                    source_key=source_key,
                    asset_type="real_property",
                    sale_type="tax_sale",
                    sale_date=sale_date,
                    status=status,
                    county_fips=COUNTY_FIPS,
                    address=address,
                    parcel_id=account,
                    url=page_url,  # type: ignore[arg-type]
                    raw_ref=raw_ref or page_url,
                    fetched_at=fetched,
                    cause_no=cause,
                    account_no=account,
                    redemption_days=DEFAULT_REDEMPTION_DAYS,
                )
            )
    return listings


def parse_path(path: Path, page_url: str) -> list[Listing]:
    return parse_html(
        path.read_text(encoding="utf-8", errors="replace"), page_url=page_url, raw_ref=str(path)
    )
