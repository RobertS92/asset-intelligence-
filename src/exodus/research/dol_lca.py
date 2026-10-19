"""DOL LCA worksites → ZIP → tract (HUD crosswalk) → H-1B exposure index. RESEARCH ONLY."""

from __future__ import annotations

import pandas as pd

from exodus.common.config import load_counties
from exodus.common.storage import research_path, write_parquet

# Public DOL disclosure files / HuggingFace duckdb mirror documented in sources.yaml
DOL_MIRROR_NOTE = "https://huggingface.co/datasets/Nason/dol-visas-database"


def build_exposure_index(
    lca_by_zip: pd.DataFrame,
    zip_tract_crosswalk: pd.DataFrame,
) -> pd.DataFrame:
    """
    Allocate LCA worksite counts from ZIP to tract using HUD crosswalk residential weights.
    Expected columns:
      lca_by_zip: zip, year, lca_count
      zip_tract_crosswalk: zip, tract_geoid, res_ratio
    """
    if lca_by_zip.empty or zip_tract_crosswalk.empty:
        return pd.DataFrame(columns=["tract_geoid", "year", "metric", "value", "source"])

    merged = lca_by_zip.merge(zip_tract_crosswalk, on="zip", how="inner")
    merged["allocated"] = merged["lca_count"].astype(float) * merged["res_ratio"].astype(float)
    grouped = (
        merged.groupby(["tract_geoid", "year"], as_index=False)["allocated"]
        .sum()
        .rename(columns={"allocated": "value"})
    )
    grouped["metric"] = "lca_worksites_allocated"
    grouped["source"] = "dol_lca"
    write_parquet(grouped, research_path("h1b_exposure_index.parquet"))
    return grouped


def pull_lca_stub_for_counties() -> pd.DataFrame:
    """
    Placeholder loader: reads data/research/raw_lca_by_zip.parquet if present.
    Full DOL disclosure download is large; Gate 2 research notebooks complete it.
    """
    path = research_path("raw_lca_by_zip.parquet")
    if path.exists():
        return pd.read_parquet(path)
    # Empty frame with schema
    counties = load_counties()
    _ = counties
    df = pd.DataFrame(columns=["zip", "year", "lca_count"])
    write_parquet(df, research_path("raw_lca_by_zip.parquet"))
    return df
