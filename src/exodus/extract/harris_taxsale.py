"""Parse Harris County tax-sale HTML/PDF listings (constable/sheriff + firm PDFs)."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup

from exodus.common.schemas import Listing, make_listing_id, map_status

SOURCE = "harris_taxsale"
COUNTY_FIPS = "48201"
DEFAULT_REDEMPTION_DAYS = 180


def parse_html_table(
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
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if not headers:
            # use first row
            first = table.find("tr")
            if first:
                headers = [c.get_text(strip=True).lower() for c in first.find_all(["td", "th"])]
        header_join = " ".join(headers)
        if "account" not in header_join and "cause" not in header_join:
            continue
        # map columns
        colmap: dict[str, int] = {}
        for i, h in enumerate(headers):
            if "cause" in h:
                colmap["cause"] = i
            elif "account" in h or "tax id" in h or "property id" in h:
                colmap["account"] = i
            elif "status" in h:
                colmap["status"] = i
            elif "address" in h:
                colmap["address"] = i
        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            cause = cells[colmap["cause"]] if "cause" in colmap else None
            account = cells[colmap["account"]] if "account" in colmap else cells[0]
            if not account or account.lower().startswith("account"):
                continue
            status_raw = cells[colmap["status"]] if "status" in colmap else "For Sale"
            try:
                status = map_status(status_raw)
            except ValueError:
                status = "for_sale" if "withdraw" not in status_raw.lower() else "withdrawn"
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


def parse_lgbs_pdf_text(
    text: str,
    *,
    page_url: str,
    sale_date: date | None = None,
    fetched_at: datetime | None = None,
    raw_ref: str = "",
    source: str = "lgbs_county_sale_pdfs",
) -> list[Listing]:
    """Best-effort parse of Linebarger County_Sale_list PDF text."""
    fetched = fetched_at or datetime.utcnow()
    listings: list[Listing] = []
    # Typical: account number patterns (Harris-style 13-digit or dashed)
    for i, line in enumerate(text.splitlines()):
        m = re.search(
            r"(?P<cause>[A-Z]?\d[\w-]{4,})\s+(?P<account>\d{7,15})\s+(?P<rest>.+)",
            line,
        )
        if not m:
            continue
        account = m.group("account")
        cause = m.group("cause")
        source_key = f"{cause}|{account}"
        listings.append(
            Listing(
                listing_id=make_listing_id(source, source_key),
                source=source,
                source_key=source_key,
                asset_type="real_property",
                sale_type="tax_sale",
                sale_date=sale_date,
                status="for_sale",
                county_fips=COUNTY_FIPS,
                parcel_id=account,
                url=page_url,  # type: ignore[arg-type]
                raw_ref=raw_ref or f"{page_url}#L{i}",
                fetched_at=fetched,
                cause_no=cause,
                account_no=account,
                redemption_days=DEFAULT_REDEMPTION_DAYS,
            )
        )
    return listings


def parse_path(path: Path, page_url: str) -> list[Listing]:
    if path.suffix.lower() == ".pdf":
        import pdfplumber

        parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return parse_lgbs_pdf_text("\n".join(parts), page_url=page_url, raw_ref=str(path))
    return parse_html_table(
        path.read_text(encoding="utf-8", errors="replace"), page_url=page_url, raw_ref=str(path)
    )
