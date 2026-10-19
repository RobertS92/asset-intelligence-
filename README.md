# Exodus Asset Signals

Risk Map + Auction Finder for distressed assets in eight Texas counties
(Collin, Denton, Dallas, Tarrant, Fort Bend, Harris, Travis, Williamson).

- **Risk Map** ranks parcels likely to hit tax suit, foreclosure posting, or
  long-term vacancy in the next 6–12 months (property-level features only).
- **Auction Finder** normalizes tax sales, trustee sales, and Ch. 683 vehicle
  auctions into one feed and joins them to the Risk Map.

Read `AGENTS.md` before contributing. Demographic and visa-exposure data stay
in `research/` and never enter the scoring pipeline.

## Setup

```bash
uv sync --all-extras
cp .env.example .env   # set EXODUS_CONTACT_EMAIL
```

## Commands

```bash
make check                          # ruff + mypy + pytest + firewall
uv run python -m exodus.cli fetch tarrant_constable3_taxsale
uv run python -m exodus.cli normalize
uv run python -m exodus.cli digest
uv run streamlit run app/Home.py --server.port 8505
uv run python scripts/export_public_listings.py   # refresh web/public sample JSON
cd web && npm ci && npm run dev                   # hosted Auction Finder (Vercel)
```

## Hosted UI (Vercel)

Phase 1 local UI is Streamlit (`app/`). The public Auction Finder is Next.js under
`web/` (Streamlit cannot run on Vercel serverless). See `web/README.md`.

Deploy needs `VERCEL_TOKEN` plus a Vercel project with **Root Directory** = `web`.

## Layout

See `AGENTS.md` §4. Raw fetches land in `data/raw/` (gitignored). Normalized
listings live in `data/scoring/listings.parquet`. Public sample JSON for the web
app is `web/public/data/listings.json` (no owner PII).
