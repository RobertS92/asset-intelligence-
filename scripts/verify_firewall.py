#!/usr/bin/env python3
"""Fail if scoring/ imports research/ or reads data/research/, or demographic names leak."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCORING = ROOT / "src" / "exodus" / "scoring"
RESEARCH = ROOT / "src" / "exodus" / "research"

# Keep in sync with exodus.common.schemas.DEMOGRAPHIC_FORBIDDEN
FORBIDDEN_NAMES = {
    "race",
    "ethnicity",
    "national_origin",
    "ancestry",
    "language",
    "surname",
    "religion",
    "hispanic",
    "latino",
    "immigration_status",
    "visa_type",
    "country_of_origin",
    "foreign_born",
    "non_citizen",
    "h1b",
    "h_1b",
    "lpr",
    "green_card",
}

IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+(?:exodus\.)?research\b",
    re.MULTILINE,
)
DATA_RE = re.compile(r"data[/\\]research")


def check_imports() -> list[str]:
    errors: list[str] = []
    if not SCORING.exists():
        return errors
    for path in SCORING.rglob("*.py"):
        text = path.read_text()
        if IMPORT_RE.search(text):
            errors.append(f"{path.relative_to(ROOT)}: imports research/")
        if DATA_RE.search(text):
            errors.append(f"{path.relative_to(ROOT)}: references data/research/")
        # AST check for importlib / dynamic paths
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as e:
            errors.append(f"{path}: syntax error {e}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("exodus.research") or node.module == "research":
                    errors.append(f"{path.relative_to(ROOT)}: ImportFrom {node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("exodus.research"):
                        errors.append(f"{path.relative_to(ROOT)}: import {alias.name}")
    return errors


def check_demographic_names() -> list[str]:
    errors: list[str] = []
    if not SCORING.exists():
        return errors
    for path in SCORING.rglob("*.py"):
        text = path.read_text().lower()
        # Skip comments-only mentions in docstrings that say "no X"
        for name in FORBIDDEN_NAMES:
            # Match as identifier-ish column / field assignment
            pattern = re.compile(rf"""['\"]({name})['\"]|{name}\s*=""")
            if pattern.search(text):
                # Allow explicit "must not use" documentation lines
                if f"no {name}" in text or "never" in text and name in text:
                    # Still flag if it looks like a field definition
                    if re.search(rf"^\s*{name}\s*[:=]", text, re.MULTILINE):
                        errors.append(f"{path.relative_to(ROOT)}: demographic field name {name!r}")
                else:
                    errors.append(f"{path.relative_to(ROOT)}: demographic name {name!r} appears")
    return errors


def main() -> int:
    errors = check_imports() + check_demographic_names()
    if errors:
        print("FIREWALL FAIL:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("firewall: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
