# Exodus Asset Signals — web (Vercel)

Public **Auction Finder** UI for Phase 1. Local Streamlit remains in `../app/Home.py`
(AGENTS.md: Streamlit Phase 1; Next.js for hosted).

## Why Next.js here

Streamlit needs a long-lived WebSocket process. Vercel is serverless and cannot host
Streamlit. This Next.js app serves the same filterable listings view from
`public/data/listings.json` (no owner PII).

## Local

```bash
# From repo root — refresh public JSON after normalize
uv run python scripts/export_public_listings.py

cd web
npm ci
npm run dev
```

## Vercel

1. Create a Vercel project with **Root Directory** = `web`.
2. Framework preset: Next.js (see `vercel.json`).
3. No secrets required for the static sample feed.
4. Optional env: `NEXT_PUBLIC_LISTINGS_URL` (absolute URL to a listings JSON feed).

Deploy from CLI (requires `VERCEL_TOKEN` and project/team access):

```bash
cd web
npx vercel@latest pull --yes --environment=production --token "$VERCEL_TOKEN"
npx vercel@latest build --prod --token "$VERCEL_TOKEN"
npx vercel@latest deploy --prebuilt --prod --token "$VERCEL_TOKEN"
```

Or: `npx vercel@latest --cwd web --prod --token "$VERCEL_TOKEN"`.
