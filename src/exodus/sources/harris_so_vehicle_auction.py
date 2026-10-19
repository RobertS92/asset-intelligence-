"""Fetch Harris County Sheriff vehicle auction PDF lists."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

from exodus.common.http import PoliteClient
from exodus.sources import register

SOURCE_KEY = "harris_so_vehicle_auction"
INDEX_URL = "https://www.harriscountyso.org/Documents/Frontpage/"
# Known recurring PDF pattern; also discover links from the frontpage folder listing if available
KNOWN_PDF = (
    "https://www.harriscountyso.org/Documents/Frontpage/HC_Auctions_Jan-Mar_2026_2026-02-13.pdf"
)


@register(SOURCE_KEY)
def fetch(run_date: date) -> list[Path]:
    run = run_date.isoformat()
    paths: list[Path] = []
    with PoliteClient() as client:
        pdf_urls: list[str] = []
        try:
            html, status = client.fetch_text(INDEX_URL)
            client.save_raw(SOURCE_KEY, run, INDEX_URL, html.encode(), status, "index.html")
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if re.search(r"auction.*\.pdf", href, re.I) or re.search(r"HC_Auction", href, re.I):
                    if href.startswith("http"):
                        pdf_urls.append(href)
                    elif href.startswith("/"):
                        pdf_urls.append("https://www.harriscountyso.org" + href)
                    else:
                        pdf_urls.append(INDEX_URL.rstrip("/") + "/" + href)
        except Exception:
            pdf_urls = []

        if not pdf_urls:
            pdf_urls = [KNOWN_PDF]

        for url in sorted(set(pdf_urls)):
            content, st = client.fetch_bytes(url)
            name = Path(url).name
            paths.append(client.save_raw(SOURCE_KEY, run, url, content, st, name))
    return paths
