"""Pydantic loaders for config/sources.yaml and config/counties.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

Access = Literal["open", "pdf_only", "api", "blocked", "manual"]
Layer = Literal["exposure", "trigger", "departure", "distress", "acquisition", "geo"]
CountyTier = Literal["texas_core", "houston", "austin"]

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"


class County(BaseModel):
    name: str
    fips: str
    tier: CountyTier

    @field_validator("fips")
    @classmethod
    def five_digit_fips(cls, v: str) -> str:
        if len(v) != 5 or not v.isdigit():
            raise ValueError(f"FIPS must be 5 digits, got {v!r}")
        return v


class CountiesConfig(BaseModel):
    counties: list[County]
    phase1_auction_counties: list[str]


class Source(BaseModel):
    key: str
    name: str
    url: str | None = None
    layer: Layer | None = None
    asset_types: list[str] = Field(default_factory=list)
    sale_type: str | None = None
    county_fips: str | None = None
    cadence: str | None = None
    access: Access
    robots_checked: str | None = None
    terms_url: str | None = None
    notes: str | None = None
    research_only: bool = False
    mirror: str | None = None
    owner: str | None = None

    @field_validator("robots_checked", mode="before")
    @classmethod
    def robots_as_str(cls, v: object) -> str | None:
        if v is None:
            return None
        return str(v)


class SourcesConfig(BaseModel):
    sources: list[Source]

    def by_key(self, key: str) -> Source:
        for s in self.sources:
            if s.key == key:
                return s
        raise KeyError(f"Unknown source key: {key}")


def load_counties(path: Path | None = None) -> CountiesConfig:
    p = path or CONFIG_DIR / "counties.yaml"
    with p.open() as f:
        raw = yaml.safe_load(f)
    return CountiesConfig.model_validate(raw)


def load_sources(path: Path | None = None) -> SourcesConfig:
    p = path or CONFIG_DIR / "sources.yaml"
    with p.open() as f:
        raw = yaml.safe_load(f)
    return SourcesConfig.model_validate(raw)


def ensure_data_dirs() -> None:
    for sub in ("raw", "interim", "research", "scoring"):
        (DATA_DIR / sub).mkdir(parents=True, exist_ok=True)
