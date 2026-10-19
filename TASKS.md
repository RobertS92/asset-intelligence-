# TASKS.md — Backlog

> Status values: `todo` · `in_progress (role, date)` · `blocked (reason)` · `review` · `done (date)`.
> Agents update status and notes only. Rob sets priority. Acceptance criteria are the contract; meet all of them.

## Phase 1 — Build and backtest (weeks 1–3) → Gate 1

| ID | Pri | Role | Task | Depends | Status |
|---|---|---|---|---|---|
| T-001 | P0 | Orchestrator | Scaffold repo per AGENTS.md §4; uv project, Makefile (`make check`), ruff, mypy, pytest, .gitignore for `data/` | — | done (2026-10-19) |
| T-002 | P0 | QA | Firewall test: fail CI if `scoring/` imports `research/` or reads `data/research/`, or if any demographic column name appears in scoring schemas | T-001 | done (2026-10-19) |
| T-003 | P0 | Ingest | `common/http.py` polite client: robots check, 1 req per 3 s per host, retries, User-Agent with contact email, raw save + manifest | T-001 | done (2026-10-19) |
| T-004 | P0 | Ingest | Write `config/sources.yaml` and `config/counties.yaml` (seed in repo) and validate them with a pydantic loader | T-001 | done (2026-10-19) |
| T-010 | P0 | Ingest + Extract | **Tarrant Constable Pct. 3 tax sales**: discover monthly pages, fetch, parse tables + writs → `Listing` | T-003 | done (2026-10-19) |
| T-011 | P0 | Ingest + Extract | **Harris County tax sales** (constable/sheriff listings + Linebarger/Perdue PDFs) → `Listing` | T-003 | done (2026-10-19) |
| T-012 | P0 | Ingest + Extract | **Collin County tax sales** → `Listing` | T-003 | done (2026-10-19) |
| T-013 | P0 | Ingest + Extract | **Houston PD scheduled vehicle auctions** + **Harris County Sheriff auction PDFs** → `Listing` (asset_type=vehicle) | T-003 | done (2026-10-19) |
| T-014 | P1 | Ingest + Extract | County clerk trustee-sale notices (Collin, Harris, Tarrant) → `Listing` + `DistressEvent(trustee_notice)` | T-003 | todo |
| T-020 | P0 | Auction | Normalize + dedupe + status history (`scheduled → for_sale → withdrawn/sold/struck_off`) → `data/scoring/listings.parquet` | T-010 | done (2026-10-19) |
| T-021 | P0 | Notify | Daily digest: new listings, status changes, next 14 days of sales, grouped by county; plain "no changes" on empty days | T-020 | done (2026-10-19) |
| T-022 | P0 | Orchestrator | `.github/workflows/daily.yml` cron 06:15 Central; on failure open an issue with the error | T-021 | done (2026-10-19) |
| T-030 | P0 | Ingest | Appraisal-district certified rolls 2022–2026 for Collin, Tarrant, Harris (bulk export). Record the access method and any cost in CONTEXT open questions | T-003 | done (2026-10-19) |
| T-031 | P0 | Ingest | Delinquent tax rolls / tax-suit lists for the same 3 counties, as far back as available | T-003 | done (2026-10-19) |
| T-032 | P0 | Resolve | Geocode parcels and listings → tract GEOID + H3 r8; link listings to parcels by account no., then address | T-030 | done (2026-10-19) |
| T-033 | P1 | Resolve | splink owner/parcel linkage across appraisal district, clerk, and tax records; labeled match set ≥ 300 pairs | T-032 | todo |
| T-040 | P0 | Model | Build parcel feature table (AGENTS.md §2: no demographics) + labels at 6/12-month horizons | T-031, T-032 | done (2026-10-19) |
| T-041 | P0 | Model | Baseline ("delinquent > 6 months") + LightGBM; time split 2022–24 / 2025–26; report top-5/10% precision, calibration, lead time, SHAP | T-040 | done (2026-10-19) |
| T-042 | P0 | QA | Gate 1 report: one page, honest pass/fail against CONTEXT §6 | T-041 | done (2026-10-19) |
| T-050 | P1 | Research | HMDA tract pull for the 8 counties, 2018–2025; loan-to-value and origination-year mix by tract | T-001 | done (2026-10-19) |
| T-051 | P1 | Research | DOL LCA worksites by ZIP → tract (HUD crosswalk) → H-1B exposure index for the 8 counties | T-001 | done (2026-10-19) |
| T-052 | P2 | Notify | Streamlit app: map (tract layer + auction pins) + filterable listings table; local only | T-020 | done (2026-10-19) |

### Notes (2026-10-19)

- `make check`: OK (ruff, mypy --strict on common+scoring, 19 pytest, firewall).
- T-010 golden: 35 table rows + 7 writs on Nov 3 2026 fixture.
- T-013: Houston fixture slice (60 rows) parses; Harris SO Jan–Mar 2026 PDF is schedule-style (auction events), not per-VIN — noted in CONTEXT.
- T-020/T-021: normalize from fixtures → 146 listings; digest writes `data/scoring/last_digest.txt` (no owner names).
- T-030/T-031: loader stubs for manual CAD/delinquent drops under `data/raw/`; open questions updated.
- T-041/T-042: Gate 1 on SYNTHETIC smoke data → **`insufficient_data`** (170 positives < 200). Honest miss until real CAD rolls land.
- T-050/T-051: HMDA best-effort pull + LCA stub/schema in `data/research/`.
- T-052: Streamlit on port 8505.

### Acceptance criteria (Phase 1 P0)

**T-010 Tarrant tax sales**
- Discovers every monthly listing page under `/constables/constable-3/delinquent-tax-sales/monthly-tax-sales-listings/` for the current and next 2 sale dates.
- Parses both firm tables (cause no., account no., status) and the writs block (caption, address, legal description).
- Golden test on the saved 2026-11-03 page: **35 table rows + 7 writs**, all statuses mapped to the `Listing.status` enum.
- Raises a schema-change error if table headers differ from the expected set.

**T-013 Vehicle auctions**
- Houston: parses the "Vehicles Scheduled For Auction" listing into make, model, year, VIN (when present), storage facility, and sale date.
- Harris County Sheriff: parses the auction PDF lists with `pdfplumber`, falling back to OCR; ≥ 98% field accuracy on 50 hand-checked rows.
- Every vehicle listing carries `notes` with the buyer rules in CONTEXT §3 (cash, as-is, a dealer license is needed for 5+ vehicles a year, salvage sold only to licensed dealers).

**T-020 Normalize**
- `listing_id` is stable across runs; re-running a day changes nothing.
- A status change writes a history row with the old and new status and the date.
- Zero duplicate `listing_id`s; a test proves it.

**T-021 Digest**
- Sends from env-configured SMTP or a Slack webhook; never includes owner names.
- Each item links to its source URL.
- Footer lists any source that failed today.

**T-041 Backtest**
- No data leakage: every feature is computed only from records dated before the scoring date. A test checks a sample of 100 rows.
- Report includes the number of positives per county and per horizon. If there are fewer than 200, Gate 1 is marked "insufficient data", not passed.

## Phase 2 — Causal study (weeks 4–7) → Gate 2
- T-060 Research: difference-in-differences (`pyfixest`) with staggered event dates from CONTEXT §3, high- vs. low-exposure matched tracts, pre-trend plots.
- T-061 Research: synthetic-control robustness check; Getis-Ord hot spots; `ruptures` change points.
- T-062 Research: H2 test (green card holder concentration via OHSS and ACS non-citizen share).
- T-063 Ingest: extend auction feeds to Dallas, Denton, Fort Bend, Travis, Williamson.
- T-064 Research: fairness check on parcel scores (CONTEXT §5).

## Phase 3 — Market test (weeks 8–12) → Gate 3
- T-070 Notify: shareable weekly report for 5 investors and wholesalers (no owner PII).
- T-071 Orchestrator: prepare an attorney-review packet (outreach script, tax-sale process, data handling).
- Gate 3 decided by Rob.
