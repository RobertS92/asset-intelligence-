"""Schema helpers."""

from __future__ import annotations

import pytest

from exodus.common.schemas import make_listing_id, map_status


def test_listing_id_stable() -> None:
    a = make_listing_id("src", "key-1")
    b = make_listing_id("src", "key-1")
    c = make_listing_id("src", "key-2")
    assert a == b
    assert a != c
    assert len(a) == 40


def test_map_status() -> None:
    assert map_status("For Sale") == "for_sale"
    assert map_status("Withdrawn") == "withdrawn"
    assert map_status("Withdrawn Prior to DC") == "withdrawn"
    with pytest.raises(ValueError):
        map_status("Mystery Status")
