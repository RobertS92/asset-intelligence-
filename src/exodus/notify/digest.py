"""Daily digest: new listings, status changes, next 14 days — no owner names."""

from __future__ import annotations

import json
import os
import smtplib
import urllib.request
from datetime import date, timedelta
from email.message import EmailMessage

import pandas as pd

from exodus.common.config import DATA_DIR, ensure_data_dirs, load_counties
from exodus.common.storage import read_parquet, scoring_path


def _county_name(fips: str | None) -> str:
    if not fips:
        return "Unknown"
    for c in load_counties().counties:
        if c.fips == fips:
            return c.name
    return fips


def _failed_sources(as_of: date) -> list[str]:
    raw = DATA_DIR / "raw"
    failed: list[str] = []
    if not raw.exists():
        return failed
    day = as_of.isoformat()
    for source_dir in raw.iterdir():
        if not source_dir.is_dir():
            continue
        day_dir = source_dir / day
        if day_dir.exists() and any("FAILED" in p.name for p in day_dir.iterdir()):
            failed.append(source_dir.name)
    return failed


def build_digest_text(as_of: date | None = None) -> str:
    ensure_data_dirs()
    as_of = as_of or date.today()
    listings = read_parquet(scoring_path("listings.parquet"))
    history = read_parquet(scoring_path("listing_status_history.parquet"))

    lines: list[str] = [f"Exodus Asset Signals — daily digest {as_of.isoformat()}", ""]

    if listings.empty:
        lines.append("no changes")
        lines.append("")
        failed = _failed_sources(as_of)
        if failed:
            lines.append("Sources that failed today: " + ", ".join(failed))
        return "\n".join(lines)

    # Never include owner names — listings schema has none; belt-and-suspenders drop
    for col in ("owner", "owner_name", "mailing_address", "defendant", "plaintiff"):
        if col in listings.columns:
            listings = listings.drop(columns=[col])

    horizon = as_of + timedelta(days=14)
    # Upcoming
    if "sale_date" in listings.columns:
        sd = pd.to_datetime(listings["sale_date"], errors="coerce").dt.date
        upcoming = listings[(sd >= as_of) & (sd <= horizon)].copy()
    else:
        upcoming = listings.iloc[0:0]

    # Status changes today
    changes = pd.DataFrame()
    if not history.empty and "changed_at" in history.columns:
        changes = history[history["changed_at"].astype(str) == as_of.isoformat()]

    # New listings: those whose fetched_at date == as_of
    new_df = pd.DataFrame()
    if "fetched_at" in listings.columns:
        fetched = pd.to_datetime(listings["fetched_at"], errors="coerce", utc=True)
        new_df = listings[fetched.dt.date == as_of]

    def _section(title: str, df: pd.DataFrame) -> None:
        lines.append(title)
        if df.empty:
            lines.append("  (none)")
            lines.append("")
            return
        for county_fips, group in df.groupby(
            df.get("county_fips", pd.Series(["Unknown"] * len(df)))
        ):
            lines.append(
                f"  {_county_name(str(county_fips) if county_fips == county_fips else None)}:"
            )
            for _, row in group.iterrows():
                url = row.get("url", "")
                sale = row.get("sale_date", "")
                status = row.get("status", "")
                key = row.get("source_key", row.get("listing_id", ""))
                asset = row.get("asset_type", "")
                lines.append(f"    - [{status}] {asset} {key} sale={sale} {url}")
        lines.append("")

    if new_df.empty and changes.empty and upcoming.empty:
        lines.append("no changes")
        lines.append("")
    else:
        _section("New listings", new_df)
        if not changes.empty:
            lines.append("Status changes")
            for _, row in changes.iterrows():
                lines.append(f"  - {row['listing_id']}: {row['old_status']} → {row['new_status']}")
            lines.append("")
        _section(f"Sales in next 14 days (through {horizon.isoformat()})", upcoming)

    failed = _failed_sources(as_of)
    lines.append("Sources that failed today: " + (", ".join(failed) if failed else "none"))
    return "\n".join(lines)


def _send_slack(text: str, webhook: str) -> None:
    data = json.dumps({"text": text}).encode()
    req = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def _send_smtp(text: str) -> None:
    host = os.environ["EXODUS_SMTP_HOST"]
    port = int(os.environ.get("EXODUS_SMTP_PORT", "587"))
    user = os.environ.get("EXODUS_SMTP_USER", "")
    password = os.environ.get("EXODUS_SMTP_PASSWORD", "")
    to_addr = os.environ["EXODUS_DIGEST_TO"]
    from_addr = os.environ.get("EXODUS_DIGEST_FROM", user or "exodus@localhost")

    msg = EmailMessage()
    msg["Subject"] = f"Exodus digest {date.today().isoformat()}"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(text)

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)


def send_digest(as_of: date | None = None, *, dry_run: bool = False) -> str:
    text = build_digest_text(as_of=as_of)
    out_path = scoring_path("last_digest.txt")
    out_path.write_text(text)

    if dry_run:
        return text

    webhook = os.environ.get("EXODUS_SLACK_WEBHOOK_URL", "").strip()
    if webhook:
        _send_slack(text, webhook)
        return text

    if os.environ.get("EXODUS_SMTP_HOST"):
        _send_smtp(text)
        return text

    # No transport configured — write only
    return text
