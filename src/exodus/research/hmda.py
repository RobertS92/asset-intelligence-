"""HMDA tract pull for the 8 counties — RESEARCH ONLY."""

from __future__ import annotations

import httpx
import pandas as pd

from exodus.common.config import load_counties
from exodus.common.storage import research_path, write_parquet

# FFIEC HMDA data browser / filing APIs — aggregate tract summaries
HMDA_DATA_BROWSER = "https://ffiec.cfpb.gov/v2/data-browser-api/view/aggregations"


def pull_hmda_tracts(
    years: range | list[int] | None = None,
    *,
    client: httpx.Client | None = None,
) -> pd.DataFrame:
    """
    Pull tract-level origination counts and LTV proxies for the 8 counties.
    Writes to data/research/hmda_tracts.parquet.
    """
    years = list(years or range(2018, 2026))
    counties = load_counties()
    fips_list = [c.fips for c in counties.counties]
    rows: list[dict[str, object]] = []
    own = client is None
    client = client or httpx.Client(timeout=60.0, headers={"User-Agent": "ExodusAssetSignals/0.1"})
    try:
        for year in years:
            for fips in fips_list:
                # Best-effort public aggregation; on failure record a stub for the year/county
                try:
                    params = {
                        "years": str(year),
                        "counties": fips,
                        "actions_taken": "1",  # originated
                    }
                    resp = client.get(HMDA_DATA_BROWSER, params=params)
                    if resp.status_code != 200:
                        rows.append(
                            {
                                "year": year,
                                "county_fips": fips,
                                "tract_geoid": None,
                                "originations": None,
                                "status": f"http_{resp.status_code}",
                                "source": "hmda",
                            }
                        )
                        continue
                    data = resp.json()
                    aggregations = (
                        data
                        if isinstance(data, list)
                        else data.get("aggregations", data.get("results", []))
                    )
                    if isinstance(aggregations, dict):
                        aggregations = [aggregations]
                    for agg in aggregations or []:
                        rows.append(
                            {
                                "year": year,
                                "county_fips": fips,
                                "tract_geoid": agg.get("tract") or agg.get("census_tract"),
                                "originations": agg.get("count") or agg.get("originations"),
                                "loan_amount_sum": agg.get("sum") or agg.get("loan_amount"),
                                "status": "ok",
                                "source": "hmda",
                            }
                        )
                except Exception as e:
                    rows.append(
                        {
                            "year": year,
                            "county_fips": fips,
                            "tract_geoid": None,
                            "originations": None,
                            "status": f"error:{type(e).__name__}",
                            "source": "hmda",
                        }
                    )
    finally:
        if own:
            client.close()

    df = pd.DataFrame(rows)
    write_parquet(df, research_path("hmda_tracts.parquet"))
    return df
