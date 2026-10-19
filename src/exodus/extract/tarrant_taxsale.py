"""Parse Tarrant Constable Pct. 3 monthly tax-sale HTML pages."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup

from exodus.common.schemas import Listing, make_listing_id, map_status

SOURCE = "tarrant_constable3_taxsale"
COUNTY_FIPS = "48439"
EXPECTED_HEADERS = ("CAUSE NUMBER", "ACCOUNT NUMBER", "STATUS")
BASE_URL = (
    "https://www.tarrantcountytx.gov/en/constables/constable-3/"
    "delinquent-tax-sales/monthly-tax-sales-listings/"
)

# Homestead/ag redemption is 730 days; unknown at listing time → use 180 default for tax sales
DEFAULT_REDEMPTION_DAYS = 180


class SchemaChangeError(RuntimeError):
    """Raised when table headers differ from the expected set."""


def parse_sale_date_from_url_or_title(url: str, html: str) -> date | None:
    # november-3--2026.html
    m = re.search(
        r"(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)-(\d+)--(\d{4})",
        url,
        re.I,
    )
    if m:
        months = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }
        return date(int(m.group(3)), months[m.group(1).lower()], int(m.group(2)))
    m2 = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2}),?\s+(\d{4})",
        html,
    )
    if m2:
        return datetime.strptime(f"{m2.group(1)} {m2.group(2)} {m2.group(3)}", "%B %d %Y").date()
    return None


def _normalize_status(raw: str) -> str:
    # "For Sale RoyaltyInterest only" → treat as For Sale
    cleaned = raw.replace("\xa0", " ").strip()
    lower = cleaned.lower()
    if lower.startswith("for sale"):
        return "For Sale"
    if lower.startswith("withdrawn"):
        # keep full known variants that map_status knows
        if "prior to dc" in lower:
            return "Withdrawn Prior to DC"
        if "prior to sale" in lower:
            return "Withdrawn Prior to Sale"
        return "Withdrawn"
    return cleaned


def parse_tables(
    soup: BeautifulSoup,
    *,
    page_url: str,
    sale_date: date | None,
    fetched_at: datetime,
    raw_ref: str,
) -> list[Listing]:
    listings: list[Listing] = []
    for table in soup.find_all("table"):
        headers = [
            th.get_text(strip=True).upper()
            for th in table.find_all("th")
            if th.get_text(strip=True)
        ]
        if not headers:
            continue
        if tuple(headers[:3]) != EXPECTED_HEADERS:
            # Allow extra empty header cells but first three must match
            if not (
                len(headers) >= 3
                and headers[0] == "CAUSE NUMBER"
                and headers[1] == "ACCOUNT NUMBER"
                and headers[2] == "STATUS"
            ):
                raise SchemaChangeError(
                    f"Unexpected table headers {headers!r}; expected {EXPECTED_HEADERS}"
                )
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True).replace("\xa0", " ") for td in tr.find_all("td")]
            if len(cells) < 3:
                continue
            cause, account, status_raw = cells[0], cells[1], cells[2]
            if not cause or not account:
                continue
            if cause.upper() == "CAUSE NUMBER":
                continue
            status = map_status(_normalize_status(status_raw))
            source_key = f"{cause}|{account}"
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
                    address=None,
                    parcel_id=account,
                    url=page_url,  # type: ignore[arg-type]
                    raw_ref=raw_ref,
                    fetched_at=fetched_at,
                    cause_no=cause,
                    account_no=account,
                    redemption_days=DEFAULT_REDEMPTION_DAYS,
                )
            )
    return listings


def parse_writs(
    soup: BeautifulSoup,
    *,
    page_url: str,
    sale_date: date | None,
    fetched_at: datetime,
    raw_ref: str,
) -> list[Listing]:
    """Parse WRITS OF EXECUTION block: caption, address, legal description."""
    full = soup.get_text("\n")
    parts = re.split(r"WRITS OF EXECUTION", full, flags=re.I)
    if len(parts) < 2:
        return []
    block = parts[1]
    listings: list[Listing] = []
    matches = list(
        re.finditer(
            r"(?P<cause>(?:JP\d+[-\dA-Za-z]+|\d{2,3}-\d{4,}-\d{2,4}|\d{3}-\d{5,}-\d{2}))"
            r".{0,500}?"
            r"PROPERTY ADDRESS:\s*(?P<address>[^\n]+)"
            r".{0,50}?"
            r"(?P<legal>LOT\b.+?|BEING\b.+?)(?=\n\s*\n\s*\n|\n\s*(?:JP\d+|\d{2,3}-\d)|\Z)",
            block,
            flags=re.I | re.S,
        )
    )
    if not matches:
        # Fallback: just addresses
        for m in re.finditer(r"PROPERTY ADDRESS:\s*(?P<address>[^\n]+)", block, flags=re.I):
            address = m.group("address").strip()
            source_key = f"writ|{address}"
            listings.append(
                Listing(
                    listing_id=make_listing_id(SOURCE, source_key),
                    source=SOURCE,
                    source_key=source_key,
                    asset_type="real_property",
                    sale_type="tax_sale",
                    sale_date=sale_date,
                    status="for_sale",
                    county_fips=COUNTY_FIPS,
                    address=address,
                    url=page_url,  # type: ignore[arg-type]
                    raw_ref=raw_ref,
                    fetched_at=fetched_at,
                    notes="writ_of_execution",
                    redemption_days=DEFAULT_REDEMPTION_DAYS,
                )
            )
        return listings

    for m in matches:
        cause = m.group("cause").strip()
        address = m.group("address").strip()
        legal = re.sub(r"\s+", " ", m.group("legal")).strip()
        source_key = f"writ|{cause}"
        listings.append(
            Listing(
                listing_id=make_listing_id(SOURCE, source_key),
                source=SOURCE,
                source_key=source_key,
                asset_type="real_property",
                sale_type="tax_sale",
                sale_date=sale_date,
                status="for_sale",
                county_fips=COUNTY_FIPS,
                address=address,
                url=page_url,  # type: ignore[arg-type]
                raw_ref=raw_ref,
                fetched_at=fetched_at,
                cause_no=cause,
                legal_description=legal[:2000],
                notes="writ_of_execution",
                redemption_days=DEFAULT_REDEMPTION_DAYS,
            )
        )
    return listings


def parse_page(
    html: str,
    *,
    page_url: str,
    fetched_at: datetime | None = None,
    raw_ref: str = "",
) -> tuple[list[Listing], list[Listing]]:
    """Return (table_listings, writ_listings)."""
    soup = BeautifulSoup(html, "lxml")
    sale_date = parse_sale_date_from_url_or_title(page_url, html)
    fetched = fetched_at or datetime.utcnow()
    tables = parse_tables(
        soup,
        page_url=page_url,
        sale_date=sale_date,
        fetched_at=fetched,
        raw_ref=raw_ref or page_url,
    )
    writs = parse_writs(
        soup,
        page_url=page_url,
        sale_date=sale_date,
        fetched_at=fetched,
        raw_ref=raw_ref or page_url,
    )
    return tables, writs


def parse_page_path(path: Path, page_url: str | None = None) -> tuple[list[Listing], list[Listing]]:
    html = path.read_text(encoding="utf-8", errors="replace")
    url = page_url or f"{BASE_URL}{path.stem}.html"
    return parse_page(html, page_url=url, raw_ref=str(path))


def discover_monthly_links(index_html: str, base: str = BASE_URL) -> list[tuple[date, str]]:
    """Return (sale_date, absolute_url) for monthly listing pages."""
    soup = BeautifulSoup(index_html, "lxml")
    found: list[tuple[date, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "monthly-tax-sales-listings/" not in href:
            continue
        if href.rstrip("/").endswith("monthly-tax-sales-listings"):
            continue
        if href.startswith("/"):
            abs_url = "https://www.tarrantcountytx.gov" + href
        elif href.startswith("http"):
            abs_url = href
        else:
            abs_url = base.rstrip("/") + "/" + href.lstrip("/")
        sale_date = parse_sale_date_from_url_or_title(abs_url, a.get_text(" ", strip=True))
        if sale_date:
            found.append((sale_date, abs_url))
    # unique by url
    seen: set[str] = set()
    out: list[tuple[date, str]] = []
    for d, u in sorted(found, key=lambda x: x[0]):
        if u not in seen:
            seen.add(u)
            out.append((d, u))
    return out


def select_current_and_next(
    links: list[tuple[date, str]], as_of: date, n: int = 3
) -> list[tuple[date, str]]:
    """Current (latest on/before as_of, or next upcoming) plus next n-1 future sales."""
    upcoming = [(d, u) for d, u in links if d >= as_of]
    if len(upcoming) >= n:
        return upcoming[:n]
    # include recent past if needed to fill
    past = [(d, u) for d, u in links if d < as_of]
    combined = past[-(n - len(upcoming)) :] + upcoming if upcoming else past[-n:]
    return combined[-n:] if len(combined) > n else combined
