#!/usr/bin/env python3
"""Best-effort HMDA + DOL LCA research pulls (firewalled)."""

from __future__ import annotations

from exodus.research.dol_lca import pull_lca_stub_for_counties
from exodus.research.hmda import pull_hmda_tracts


def main() -> None:
    hmda = pull_hmda_tracts(years=[2023, 2024])
    print(f"HMDA rows: {len(hmda)}")
    lca = pull_lca_stub_for_counties()
    print(f"LCA zip rows: {len(lca)}")


if __name__ == "__main__":
    main()
