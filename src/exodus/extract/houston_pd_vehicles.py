"""Parse Houston PD Vehicles Scheduled For Auction HTML."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup

from exodus.common.schemas import Listing, make_listing_id

SOURCE = "houston_pd_vehicle_auction"
COUNTY_FIPS = "48201"
PAGE_URL = "https://houstontx.gov/police/auto_dealers_detail/Vehicles_Scheduled_For_Auction.htm"

BUYER_RULES = (
    "Cash only; sold as-is at the storage facility. "
    "Salvage sold only to licensed salvage dealers. "
    "Buying 5 or more vehicles a year requires a dealer (MVD) license. "
    "Texas Transportation Code Ch. 683."
)

EXPECTED_HEADERS = (
    "Date Scheduled",
    "Est Time",
    "Storage Lot Name",
    "Storage Lot Address",
    "Year",
    "Make",
    "Model",
    "VIN",
)


class SchemaChangeError(RuntimeError):
    pass


def _parse_year(raw: str) -> int | None:
    raw = raw.strip()
    if not raw:
        return None
    if len(raw) == 2 and raw.isdigit():
        y = int(raw)
        return 2000 + y if y < 80 else 1900 + y
    if len(raw) == 4 and raw.isdigit():
        return int(raw)
    return None


def _parse_sale_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def parse_page(
    html: str,
    *,
    page_url: str = PAGE_URL,
    fetched_at: datetime | None = None,
    raw_ref: str = "",
) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        raise SchemaChangeError("No table found on Houston PD vehicle auction page")

    rows = table.find_all("tr")
    header_row = None
    for tr in rows:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if cells and cells[0] == "Date Scheduled":
            header_row = cells
            break
    if header_row is None:
        raise SchemaChangeError("Header row 'Date Scheduled' not found")
    # Require expected columns present (order may vary slightly)
    for col in EXPECTED_HEADERS:
        if col not in header_row:
            raise SchemaChangeError(f"Missing column {col!r} in {header_row}")

    idx = {name: header_row.index(name) for name in EXPECTED_HEADERS}
    fetched = fetched_at or datetime.utcnow()
    listings: list[Listing] = []
    started = False
    for tr in rows:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if not cells:
            continue
        if cells[0] == "Date Scheduled":
            started = True
            continue
        if not started:
            continue
        if len(cells) <= max(idx.values()):
            continue
        sale_date = _parse_sale_date(cells[idx["Date Scheduled"]])
        vin = cells[idx["VIN"]].strip() or None
        make = cells[idx["Make"]].strip() or None
        model = cells[idx["Model"]].strip() or None
        year = _parse_year(cells[idx["Year"]])
        facility = cells[idx["Storage Lot Name"]].strip() or None
        address = cells[idx["Storage Lot Address"]].strip() or None
        source_key = vin or f"{sale_date}|{facility}|{make}|{model}|{year}"
        listings.append(
            Listing(
                listing_id=make_listing_id(SOURCE, source_key),
                source=SOURCE,
                source_key=source_key,
                asset_type="vehicle",
                sale_type="impound_auction",
                sale_date=sale_date,
                status="scheduled",
                county_fips=COUNTY_FIPS,
                address=address,
                vin=vin,
                url=page_url,  # type: ignore[arg-type]
                raw_ref=raw_ref or page_url,
                fetched_at=fetched,
                notes=BUYER_RULES,
                make=make,
                model=model,
                year=year,
                storage_facility=facility,
            )
        )
    return listings


def parse_page_path(path: Path, page_url: str = PAGE_URL) -> list[Listing]:
    return parse_page(
        path.read_text(encoding="utf-8", errors="replace"), page_url=page_url, raw_ref=str(path)
    )
