"""CI firewall: scoring must not touch research or demographic columns."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_verify_firewall_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_firewall.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_scoring_package_has_no_research_import() -> None:
    scoring = ROOT / "src" / "exodus" / "scoring"
    if not scoring.exists():
        pytest.skip("scoring package not yet created")
    for path in scoring.rglob("*.py"):
        text = path.read_text()
        assert "exodus.research" not in text
        assert "data/research" not in text
        assert "data\\research" not in text


def test_parcel_features_rejects_demographic_field_names() -> None:
    from exodus.common.schemas import DEMOGRAPHIC_FORBIDDEN, ParcelFeatures

    fields = {n.lower() for n in ParcelFeatures.model_fields}
    overlap = fields & DEMOGRAPHIC_FORBIDDEN
    assert not overlap, f"ParcelFeatures contains forbidden names: {overlap}"
