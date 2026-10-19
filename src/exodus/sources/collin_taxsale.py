"""Fetch Collin County tax-sale listings."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from exodus.common.http import PoliteClient
from exodus.sources import register

SOURCE_KEY = "collin_taxsale"

# Collin County Tax Assessor / Constable tax sale pages (public)
COLLIN_URLS = [
    "https://www.collincountytx.gov/tax_assessor/Pages/tax-sales.aspx",
    "https://www.collincountytx.gov/constable/Pages/tax-sales.aspx",
]


@register(SOURCE_KEY)
def fetch(run_date: date) -> list[Path]:
    run = run_date.isoformat()
    paths: list[Path] = []
    with PoliteClient() as client:
        for i, url in enumerate(COLLIN_URLS):
            try:
                content, status = client.fetch_bytes(url)
                paths.append(
                    client.save_raw(
                        SOURCE_KEY, run, url, content, status, f"collin_taxsale_{i}.html"
                    )
                )
            except Exception as e:
                paths.append(
                    client.save_raw(
                        SOURCE_KEY,
                        run,
                        url,
                        f"FETCH_FAILED: {e}".encode(),
                        0,
                        f"collin_taxsale_{i}.FAILED.txt",
                    )
                )
    return paths
