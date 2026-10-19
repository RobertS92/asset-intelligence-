"""CLI entrypoints for fetch / normalize / digest / backtest."""

from __future__ import annotations

import argparse
import sys
from datetime import date


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="exodus", description="Exodus Asset Signals")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch", help="Fetch a source by key")
    p_fetch.add_argument("source_key")
    p_fetch.add_argument("--date", default=None, help="Run date YYYY-MM-DD (default: today)")

    sub.add_parser("normalize", help="Normalize + dedupe listings → parquet")
    sub.add_parser("digest", help="Send daily digest")
    sub.add_parser("backtest", help="Run parcel model backtest (Gate 1)")
    sub.add_parser("list-sources", help="List configured source keys")

    args = parser.parse_args(argv)

    if args.cmd == "list-sources":
        from exodus.common.config import load_sources

        for s in load_sources().sources:
            print(f"{s.key}\t{s.access}\t{s.name}")
        return

    if args.cmd == "fetch":
        from exodus.sources import get_fetcher

        run_date = date.fromisoformat(args.date) if args.date else date.today()
        paths = get_fetcher(args.source_key)(run_date)
        for p in paths:
            print(p)
        return

    if args.cmd == "normalize":
        from exodus.auctions.normalize import run_normalize

        out = run_normalize()
        print(out)
        return

    if args.cmd == "digest":
        from exodus.notify.digest import send_digest

        send_digest()
        return

    if args.cmd == "backtest":
        from exodus.scoring.backtest import run_backtest

        report = run_backtest()
        print(report)
        return

    parser.error(f"Unknown command {args.cmd}")
    sys.exit(1)


if __name__ == "__main__":
    main()
