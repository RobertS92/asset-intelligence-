"""Fetch Tarrant Constable Pct. 3 monthly tax-sale listing pages."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from exodus.common.http import PoliteClient
from exodus.extract.tarrant_taxsale import (
    discover_monthly_links,
    select_current_and_next,
)
from exodus.sources import register

SOURCE_KEY = "tarrant_constable3_taxsale"
INDEX_URL = (
    "https://www.tarrantcountytx.gov/en/constables/constable-3/"
    "delinquent-tax-sales/monthly-tax-sales-listings.html"
)


@register(SOURCE_KEY)
def fetch(run_date: date) -> list[Path]:
    """Discover current + next 2 sale pages, fetch raw HTML idempotently."""
    run = run_date.isoformat()
    paths: list[Path] = []
    with PoliteClient() as client:
        index_html, status = client.fetch_text(INDEX_URL)
        index_path = client.save_raw(
            SOURCE_KEY, run, INDEX_URL, index_html.encode(), status, "index.html"
        )
        paths.append(index_path)

        links = discover_monthly_links(index_html)
        selected = select_current_and_next(links, run_date, n=3)
        if not selected:
            raise RuntimeError("No monthly tax-sale listing pages discovered")

        for sale_date, url in selected:
            content, st = client.fetch_bytes(url)
            name = Path(urlparse(url).path).name or f"{sale_date.isoformat()}.html"
            if not name.endswith(".html"):
                name = f"{sale_date.isoformat()}.html"
            paths.append(client.save_raw(SOURCE_KEY, run, url, content, st, name))
    return paths
