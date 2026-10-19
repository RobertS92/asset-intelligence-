"""Parse Harris County Sheriff vehicle auction PDFs (schedule + vehicle rows when present)."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import pdfplumber

from exodus.common.schemas import Listing, make_listing_id

SOURCE = "harris_so_vehicle_auction"
COUNTY_FIPS = "48201"
SOURCE_URL = "https://www.harriscountyso.org/Documents/Frontpage/"

BUYER_RULES = (
    "Cash / vehicle as-is (Harris County Sheriff Ch. 683 auction). "
    "Salvage sold only to licensed salvage dealers. "
    "Buying 5 or more vehicles a year requires a dealer (MVD) license."
)

AUCTION_BLOCK_RE = re.compile(
    r"AUCTION TO BE HELD\s+"
    r"(?P<month>JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)"
    r"\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})\s*[–\-]\s*(?P<time>[^\n]+)\n"
    r"(?P<facility>[^\n]+)\n"
    r"(?P<address>[^\n]+)",
    re.I,
)

MONTHS = {
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

# Vehicle detail line patterns when present in other SO PDFs
VEHICLE_LINE_RE = re.compile(
    r"(?P<year>19\d{2}|20\d{2})\s+(?P<make>[A-Za-z0-9\-]+)\s+(?P<model>[A-Za-z0-9\-]+)"
    r".*?\b(?P<vin>[A-HJ-NPR-Z0-9]{11,17})\b",
    re.I,
)


def _extract_text(path: Path) -> str:
    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if not t.strip():
                # OCR fallback placeholder — callers may swap in pytesseract later
                t = ""
            parts.append(t)
    return "\n".join(parts)


def parse_pdf(
    path: Path,
    *,
    page_url: str = SOURCE_URL,
    fetched_at: datetime | None = None,
) -> list[Listing]:
    text = _extract_text(path)
    if not text.strip():
        # Attempt OCR fallback if available
        text = _ocr_fallback(path)
    fetched = fetched_at or datetime.utcnow()
    listings: list[Listing] = []

    # Prefer per-vehicle rows when VIN-bearing lines exist
    vehicle_rows = list(VEHICLE_LINE_RE.finditer(text))
    if vehicle_rows:
        for i, m in enumerate(vehicle_rows):
            vin = m.group("vin").upper()
            source_key = vin
            listings.append(
                Listing(
                    listing_id=make_listing_id(SOURCE, source_key),
                    source=SOURCE,
                    source_key=source_key,
                    asset_type="vehicle",
                    sale_type="impound_auction",
                    sale_date=None,
                    status="scheduled",
                    county_fips=COUNTY_FIPS,
                    vin=vin,
                    url=page_url,  # type: ignore[arg-type]
                    raw_ref=f"{path}#row{i}",
                    fetched_at=fetched,
                    notes=BUYER_RULES,
                    make=m.group("make"),
                    model=m.group("model"),
                    year=int(m.group("year")),
                )
            )
        return listings

    # Schedule-style PDFs (Jan–Mar 2026 fixture): one listing per auction event
    for i, m in enumerate(AUCTION_BLOCK_RE.finditer(text)):
        sale_date = date(
            int(m.group("year")),
            MONTHS[m.group("month").lower()],
            int(m.group("day")),
        )
        facility = m.group("facility").strip()
        address = m.group("address").strip()
        source_key = f"{sale_date.isoformat()}|{facility}"
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
                url=page_url,  # type: ignore[arg-type]
                raw_ref=f"{path}#auction{i}",
                fetched_at=fetched,
                notes=BUYER_RULES,
                storage_facility=facility,
            )
        )
    return listings


def _ocr_fallback(path: Path) -> str:
    """OCR fallback using pytesseract + pdf2image when available; else empty."""
    try:
        import pytesseract  # type: ignore
        from pdf2image import convert_from_path  # type: ignore
    except ImportError:
        return ""
    texts: list[str] = []
    for img in convert_from_path(str(path)):
        texts.append(pytesseract.image_to_string(img))
    return "\n".join(texts)
