"""Golden test: Tarrant Nov 3 2026 page → 35 table rows + 7 writs."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from exodus.extract.tarrant_taxsale import (
    SchemaChangeError,
    discover_monthly_links,
    parse_page,
    select_current_and_next,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "tarrant_constable3_taxsale"
PAGE_URL = (
    "https://www.tarrantcountytx.gov/en/constables/constable-3/"
    "delinquent-tax-sales/monthly-tax-sales-listings/november-3--2026.html"
)


def test_golden_nov_2026() -> None:
    html = (FIXTURES / "2026-11-03.html").read_text()
    tables, writs = parse_page(html, page_url=PAGE_URL)
    assert len(tables) == 35, f"expected 35 table rows, got {len(tables)}"
    assert len(writs) == 7, f"expected 7 writs, got {len(writs)}"
    statuses = {t.status for t in tables}
    assert statuses <= {"scheduled", "for_sale", "withdrawn", "sold", "struck_off", "unknown"}
    assert any(t.status == "for_sale" for t in tables)
    assert any(t.status == "withdrawn" for t in tables)
    for w in writs:
        assert w.address
        assert w.notes == "writ_of_execution"


def test_schema_change_raises() -> None:
    bad = """
    <html><body><table>
      <tr><th>FOO</th><th>BAR</th><th>BAZ</th></tr>
      <tr><td>1</td><td>2</td><td>3</td></tr>
    </table></body></html>
    """
    with pytest.raises(SchemaChangeError):
        parse_page(bad, page_url=PAGE_URL)


def test_discover_and_select() -> None:
    index = (FIXTURES / "index.html").read_text()
    links = discover_monthly_links(index)
    assert len(links) >= 3
    selected = select_current_and_next(links, date(2026, 10, 19), n=3)
    assert len(selected) == 3
    assert selected[0][0] <= selected[-1][0]
