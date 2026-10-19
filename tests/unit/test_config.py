"""Config loader validation."""

from __future__ import annotations

from exodus.common.config import load_counties, load_sources


def test_load_counties() -> None:
    cfg = load_counties()
    assert len(cfg.counties) == 8
    fips = {c.fips for c in cfg.counties}
    assert "48439" in fips  # Tarrant
    assert "48201" in fips  # Harris
    assert "48085" in fips  # Collin
    assert set(cfg.phase1_auction_counties) == {"48439", "48201", "48085"}


def test_load_sources() -> None:
    cfg = load_sources()
    keys = {s.key for s in cfg.sources}
    assert "tarrant_constable3_taxsale" in keys
    assert "houston_pd_vehicle_auction" in keys
    blocked = cfg.by_key("lgbs_taxsales_search")
    assert blocked.access == "blocked"
