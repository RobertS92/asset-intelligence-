"""Fetch Harris County tax-sale listings (constable/sheriff pages + Linebarger PDFs)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from exodus.common.http import PoliteClient, RobotsBlockedError
from exodus.sources import register

SOURCE_KEY = "harris_taxsale"

# Official-ish public landing pages (updated in sources.yaml as discovered)
HARRIS_CONSTABLE_URLS = [
    # Harris County Tax Office / delinquent tax information
    "https://www.hctax.net/Property/TaxSales",
]

# Linebarger published PDFs only — never taxsales.lgbs.com
LGBS_PDF_PATTERN = (
    "https://taxsalesib.lgbs.com/images/lit_ps_images/ib-emails/"
    "County_Sale_list_HARRIS_{yyyymmdd}.pdf"
)


@register(SOURCE_KEY)
def fetch(run_date: date) -> list[Path]:
    run = run_date.isoformat()
    paths: list[Path] = []
    with PoliteClient() as client:
        for url in HARRIS_CONSTABLE_URLS:
            try:
                content, status = client.fetch_bytes(url)
                name = "hctax_taxsales.html"
                paths.append(client.save_raw(SOURCE_KEY, run, url, content, status, name))
            except (RobotsBlockedError, Exception) as e:
                # Record failure via empty marker for digest footer
                marker = client.save_raw(
                    SOURCE_KEY,
                    run,
                    url,
                    f"FETCH_FAILED: {e}".encode(),
                    0,
                    "hctax_taxsales.FAILED.txt",
                )
                paths.append(marker)

        # Try first-Tuesday PDF for current and next month (best-effort; 404 is OK)
        for offset_months in (0, 1):
            y = run_date.year
            m = run_date.month + offset_months
            if m > 12:
                m -= 12
                y += 1
            # First Tuesday approximation: days 1–7
            for day in range(1, 8):
                try:
                    d = date(y, m, day)
                except ValueError:
                    continue
                if d.weekday() == 1:  # Tuesday
                    yyyymmdd = d.strftime("%Y%m%d")
                    url = LGBS_PDF_PATTERN.format(yyyymmdd=yyyymmdd)
                    try:
                        content, status = client.fetch_bytes(url, check_robots=True)
                        paths.append(
                            client.save_raw(
                                SOURCE_KEY,
                                run,
                                url,
                                content,
                                status,
                                f"County_Sale_list_HARRIS_{yyyymmdd}.pdf",
                            )
                        )
                    except Exception:
                        pass
                    break
    return paths
