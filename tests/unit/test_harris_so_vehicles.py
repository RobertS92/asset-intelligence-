"""Harris County Sheriff auction PDF parser."""

from __future__ import annotations

from pathlib import Path

from exodus.extract.harris_so_vehicles import BUYER_RULES, parse_pdf

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "harris_so_vehicle_auction"
    / "HC_Auctions_Jan-Mar_2026.pdf"
)


def test_parse_harris_so_schedule_pdf() -> None:
    listings = parse_pdf(FIXTURE)
    assert len(listings) >= 10
    for li in listings:
        assert li.asset_type == "vehicle"
        assert li.notes and "dealer" in li.notes.lower()
        assert BUYER_RULES in (li.notes or "")
        assert li.sale_date is not None or li.vin is not None
        assert li.storage_facility or li.vin
