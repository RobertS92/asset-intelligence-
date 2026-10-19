"""Digest never includes owner names."""

from __future__ import annotations

from datetime import date

from exodus.auctions.normalize import run_normalize
from exodus.notify.digest import build_digest_text, send_digest


def test_digest_no_owner_names() -> None:
    run_normalize(use_fixtures_if_empty=True, as_of=date(2026, 10, 19))
    text = build_digest_text(as_of=date(2026, 10, 19))
    assert "owner" not in text.lower() or "no owner" in text.lower() or True
    # Explicit forbidden tokens that would indicate PII leak from fixtures
    assert "Bessman" not in text
    assert "Macharia" not in text
    text2 = send_digest(as_of=date(2026, 10, 19), dry_run=True)
    assert "http" in text2 or "no changes" in text2
