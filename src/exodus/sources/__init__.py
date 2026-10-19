"""One module per source: fetch(run_date) -> list[Path]."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

FetchFn = Callable[[date], list[Path]]

REGISTRY: dict[str, FetchFn] = {}


def register(key: str) -> Callable[[FetchFn], FetchFn]:
    def deco(fn: FetchFn) -> FetchFn:
        REGISTRY[key] = fn
        return fn

    return deco


def get_fetcher(key: str) -> FetchFn:
    if key not in REGISTRY:
        # Import known modules to populate registry
        from exodus.sources import (  # noqa: F401
            cad_rolls,
            collin_taxsale,
            delinquent_tax,
            harris_so_vehicle_auction,
            harris_taxsale,
            houston_pd_vehicle_auction,
            tarrant_constable3_taxsale,
        )

    if key not in REGISTRY:
        raise KeyError(f"No fetcher registered for {key}")
    return REGISTRY[key]
