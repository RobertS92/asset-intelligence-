"""Houston PD vehicle auction parser."""

from __future__ import annotations

from pathlib import Path

from exodus.extract.houston_pd_vehicles import BUYER_RULES, parse_page_path

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "houston_pd_vehicle_auction"
    / "Vehicles_Scheduled_For_Auction.htm"
)


def test_parse_houston_vehicles() -> None:
    listings = parse_page_path(FIXTURE)
    assert len(listings) >= 50
    sample = listings[0]
    assert sample.asset_type == "vehicle"
    assert sample.sale_type == "impound_auction"
    assert sample.make
    assert sample.year is not None
    assert sample.storage_facility
    assert sample.sale_date is not None
    assert BUYER_RULES in (sample.notes or "")
    # VIN present on most rows
    with_vin = [li for li in listings if li.vin]
    assert len(with_vin) >= 40
