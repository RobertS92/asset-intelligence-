"""Parquet / DuckDB helpers for data/ paths."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from exodus.common.config import DATA_DIR, ensure_data_dirs


def raw_dir(source_key: str, run_date: str) -> Path:
    ensure_data_dirs()
    path = DATA_DIR / "raw" / source_key / run_date
    path.mkdir(parents=True, exist_ok=True)
    return path


def manifest_path(source_key: str) -> Path:
    ensure_data_dirs()
    d = DATA_DIR / "raw" / source_key
    d.mkdir(parents=True, exist_ok=True)
    return d / "manifest.jsonl"


def scoring_path(name: str) -> Path:
    ensure_data_dirs()
    return DATA_DIR / "scoring" / name


def research_path(name: str) -> Path:
    ensure_data_dirs()
    return DATA_DIR / "research" / name


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def duckdb_query(sql: str, **frames: pd.DataFrame) -> pd.DataFrame:
    con = duckdb.connect()
    try:
        for name, frame in frames.items():
            con.register(name, frame)
        return con.execute(sql).df()
    finally:
        con.close()
