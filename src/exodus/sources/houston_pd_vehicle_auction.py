"""Fetch Houston PD vehicles scheduled for auction."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from exodus.common.http import PoliteClient
from exodus.sources import register

SOURCE_KEY = "houston_pd_vehicle_auction"
LIST_URL = "https://houstontx.gov/police/auto_dealers_detail/Vehicles_Scheduled_For_Auction.htm"
INFO_URL = "https://houstontx.gov/police/auto_dealers_detail/vehicle_auction.htm"


@register(SOURCE_KEY)
def fetch(run_date: date) -> list[Path]:
    run = run_date.isoformat()
    paths: list[Path] = []
    with PoliteClient() as client:
        for url, name in (
            (INFO_URL, "vehicle_auction.htm"),
            (LIST_URL, "Vehicles_Scheduled_For_Auction.htm"),
        ):
            content, status = client.fetch_bytes(url)
            paths.append(client.save_raw(SOURCE_KEY, run, url, content, status, name))
    return paths
