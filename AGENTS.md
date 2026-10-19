# AGENTS.md — Exodus Asset Signals

> **Source of truth for every agent working in this repo.** Read this file fully before any work.
> If anything elsewhere (code comments, issues, chat, other docs) conflicts with this file, this file wins.
> Only the human owner (Rob) changes the Hard Rules section.

## 0. Document hierarchy

| Order | File | Purpose | Who may edit |
|---|---|---|---|
| 1 | `AGENTS.md` | Rules, roles, contracts, workflow | Rob; agents may propose edits via PR, never merge them alone |
| 2 | `CONTEXT.md` | Why the project exists, verified facts, decisions, open questions | Any agent, with a dated entry in the Decision Log |
| 3 | `TASKS.md` | Backlog, status, acceptance criteria | Any agent (status and notes only) |
| 4 | `config/sources.yaml` | Machine-readable registry of every data source | Ingest and Auction agents |
| 5 | Code and tests | Implementation | Owning agent per Section 3 |

## 1. What we are building (one paragraph)

Two connected tools for 8 Texas counties. **Risk Map**: estimates where (tract) and which parcels are likely to hit tax suit, foreclosure posting, or long-term vacancy in the next 6–12 months. **Auction Finder**: one normalized feed of every legal sale where distressed assets surface (tax sales, trustee sales, impound and abandoned-vehicle auctions, government surplus, equipment, bankruptcy). The Risk Map ranks the auctions. The system runs on a **daily schedule**, not 24/7, and sends a digest. Full context: `CONTEXT.md`.

## 2. Hard rules (non-negotiable)

1. **No demographic data in scoring.** Race, ethnicity, national origin, ancestry, language, surname, religion, or any proxy built from them must never enter `src/exodus/scoring/`, `data/scoring/`, or any outreach or contact list. Demographic and visa-exposure data live only in `src/exodus/research/` and `data/research/`. CI enforces this (`tests/test_firewall.py`). Never weaken that test.
2. **No immigration-status inference.** No feature, model, field, or heuristic may estimate any individual's immigration status, visa type, or country of origin. Aggregate tract-level counts from public statistics are allowed only in `research/`.
3. **No fabricated data.** Never invent records, listings, numbers, sources, or test results. Test fixtures are real downloaded samples (stored in `tests/fixtures/` with their source URL and fetch date) or are clearly marked `SYNTHETIC` in the filename and header.
4. **Respect access rules.** Check `robots.txt` and the site's terms before writing any scraper. If either disallows automated access, **do not scrape**. Mark the source `access: blocked` in `config/sources.yaml` and use its official PDF, email alert, bulk export, or API instead. Known block: `taxsales.lgbs.com` (robots disallows). Default rate limit: 1 request per 3 seconds per host, with an identifying User-Agent that includes a contact email from env `EXODUS_CONTACT_EMAIL`.
5. **No acquisition actions.** Agents never bid, register for auctions, submit forms, contact property owners, or send outreach. Agents only collect, analyze, and notify Rob.
6. **Vehicles:** the system only lists vehicles from Texas Transportation Code Ch. 683 auctions, licensed storage facilities, and government or surplus sales. It never suggests towing or taking vehicles.
7. **PII handling.** Owner names and mailing addresses from appraisal-district and clerk records are PII. Store them only in `data/` (gitignored), never in logs, fixtures, issues, or commit messages. Fixtures must have owner fields redacted to `REDACTED`.
8. **Don't claim success without verification.** A task is done only when its acceptance criteria in `TASKS.md` pass, tests are green, and you've pasted the verification output into the task's notes.
9. **Escalate instead of guessing** on: legal ambiguity, a blocked or changed source, paid data or any spend, schema changes to contracts in Section 5, or any change that would touch the firewall. Open an issue labeled `needs-rob` and stop that thread of work.

## 3. Agent roles

Each agent owns specific directories. Don't edit another agent's directories except through a PR that the owner (or the Orchestrator) reviews.

| Agent | Owns | Inputs | Outputs | Done means |
|---|---|---|---|---|
| **Orchestrator** | `TASKS.md`, `.github/workflows/` | This file, `CONTEXT.md` | Task assignments, schedule config, merged PRs | Backlog current; daily pipeline green |
| **Ingest** | `src/exodus/sources/`, `config/sources.yaml` | Source registry | Raw files in `data/raw/<source>/<date>/` plus `manifest.jsonl` | Fetcher is idempotent, polite, tested on a real fixture |
| **Extract** | `src/exodus/extract/` | Raw HTML, PDF, and text | Validated `pydantic` records (Section 5) | ≥ 98% field accuracy on a hand-labeled sample of ≥ 50 records per source |
| **Resolve** | `src/exodus/resolve/` | Extracted records | `parcel_id` and `owner_id` links; tract GEOID and H3 cell (res 8) | Precision ≥ 0.98 and recall ≥ 0.90 on a labeled match set |
| **Auction** | `src/exodus/auctions/` | Resolved listings | `data/scoring/listings.parquet`; status-change history | All Phase 1 sources live; zero duplicate listings |
| **Research** | `src/exodus/research/`, `notebooks/research/` | Public aggregate data (HMDA, ACS, DOL LCA, USCIS, OHSS, WARN) | Tract exposure index; difference-in-differences results | Reproducible notebook plus a written result with confidence intervals |
| **Model** | `src/exodus/scoring/` | Parcel features (no demographics) | Parcel scores, SHAP reasons, backtest report | Backtest report meets or misses Gate 1 honestly |
| **Notify** | `src/exodus/notify/`, `app/` | Listings and scores | Daily digest (email or Slack); Streamlit app | Digest sends on schedule; empty days say "no changes" |
| **QA** | `tests/`, `scripts/verify_*.py` | Everything | Test suite, firewall test, data-quality checks | CI green; data-quality report attached to each PR |

One agent may hold several roles. When a session starts, state which role(s) you're acting as.

## 4. Repo layout

```
exodus-signals/
├── AGENTS.md  CONTEXT.md  TASKS.md  CLAUDE.md  README.md
├── config/
│   ├── sources.yaml          # registry of every source (see Section 6)
│   └── counties.yaml         # target counties + FIPS
├── src/exodus/
│   ├── sources/              # one module per source: fetch()
│   ├── extract/              # parsers: HTML, PDF, OCR, LLM-assisted
│   ├── resolve/              # linkage (splink), geocoding, tract/H3
│   ├── auctions/             # normalization, dedupe, status history
│   ├── research/             # FIREWALLED: demographic + exposure analysis
│   ├── scoring/              # parcel features + models (no demographics)
│   ├── notify/               # digest + alerts
│   └── common/               # schemas.py, http.py (polite client), storage.py
├── app/                      # Streamlit (Phase 1); Next.js later
├── notebooks/{research,scoring}/
├── tests/{fixtures,unit,integration}/  test_firewall.py
├── scripts/                  # one-off + verification scripts
├── data/                     # GITIGNORED: raw/, interim/, research/, scoring/
└── .github/workflows/daily.yml
```

## 5. Data contracts (in `src/exodus/common/schemas.py`)

Changing a contract requires a `needs-rob` issue first.

```python
class Listing(BaseModel):            # one auction/sale item
    listing_id: str                  # sha1(source + source_key)
    source: str                      # key in config/sources.yaml
    source_key: str                  # cause no., account no., lot no., VIN
    asset_type: Literal["real_property","vehicle","equipment","business","contents","other"]
    sale_type: Literal["tax_sale","trustee_sale","reo","impound_auction","gov_surplus",
                       "federal_seizure","equipment_auction","bankruptcy_sale","storage_lien"]
    sale_date: date | None
    status: Literal["scheduled","for_sale","withdrawn","sold","struck_off","unknown"]
    county_fips: str | None
    address: str | None
    parcel_id: str | None            # filled by Resolve
    vin: str | None
    min_bid_usd: Decimal | None
    redemption_days: int | None      # 730 homestead/ag tax sale, 180 other, None if N/A
    url: HttpUrl
    raw_ref: str                     # path to raw file + byte offset/page
    fetched_at: datetime

class DistressEvent(BaseModel):      # labels + features for parcels
    parcel_id: str
    event_type: Literal["tax_delinquent","tax_suit","trustee_notice","hoa_lien",
                        "code_violation","usps_vacant","homestead_removed","mailing_moved_out_of_state"]
    event_date: date
    source: str
    raw_ref: str

class TractExposure(BaseModel):      # RESEARCH ONLY — never imported by scoring/
    tract_geoid: str
    period: str                      # e.g. "2026Q2"
    metric: str                      # e.g. "lca_worksites_per_1k_hh"
    value: float
    source: str
```

## 6. Source module contract

Every source in `src/exodus/sources/<key>.py` must:

1. Have an entry in `config/sources.yaml` with `key, name, url, owner, asset_types, cadence, access (open|pdf_only|api|blocked), robots_checked (date), terms_url, notes`.
2. Expose `fetch(run_date) -> list[Path]`. It saves raw bytes unchanged under `data/raw/<key>/<run_date>/` and appends to `manifest.jsonl` with `url, sha256, fetched_at, http_status`.
3. Be **idempotent**: re-running the same day doesn't duplicate files.
4. Use `common/http.py`, the polite client. Never call `requests` or `httpx` directly.
5. Fail loudly when the page structure changes (a schema validation error raises an alert), never silently return zero rows.
6. Have at least one integration test using a real, redacted fixture.

## 7. Workflow for every task

1. Pick the highest-priority `todo` task in `TASKS.md` that matches your role. Set it to `in_progress` with your role and the date.
2. Read the task's acceptance criteria and every file it references.
3. Write or update tests first, using real fixtures.
4. Implement in the smallest change that passes.
5. Run `make check`, which runs `ruff`, `mypy`, `pytest`, and `scripts/verify_firewall.py`.
6. Paste the verification output into the task's notes in `TASKS.md`.
7. Open a PR titled `[T-xxx] <summary>`, describing what changed, how it was verified, and known gaps.
8. If you learned a durable fact (a source changed format, a law detail, a decision), add a dated entry to `CONTEXT.md` → Decision Log or Verified Facts, with a link.

## 8. Stack and conventions

- Python 3.12, managed with `uv`. Formatting and linting with `ruff`; type checks with `mypy --strict` on `common/` and `scoring/`.
- Storage: DuckDB plus Parquet in Phase 1; Postgres/PostGIS after Gate 1.
- Geo: `geopandas`, `h3` at resolution 8, Census Geocoder, HUD ZIP-tract crosswalk.
- Linkage: `splink`. Models: `lightgbm`, `shap`, `lifelines`. Causal: `pyfixest`. Spatial: PySAL (`esda`, `libpysal`).
- PDFs: `pdfplumber` first, then Tesseract OCR. JavaScript-rendered pages: Playwright.
- LLM extraction is allowed only as a fallback after deterministic parsing. Every LLM-extracted field stores `extraction_method="llm"` and the model ID. Accuracy is measured against the same hand-labeled sample.
- Schedule: GitHub Actions cron, daily at 06:15 America/Chicago (11:15 UTC; 12:15 UTC during CST — set both or use a tolerant window). No always-on services in Phase 1.
- Secrets live only in environment variables; never commit them.
- Commits use imperative mood and reference task IDs.

## 9. Definition of done (the whole project, per phase)

- **Phase 1 / Gate 1:** tax-sale and vehicle feeds live for Tarrant, Harris, and Collin. Parcel model backtest (train 2022–24, test 2025–26) reaches top-10% precision ≥ 2× the baseline "tax-delinquent > 6 months", with ≥ 200 positive cases. **If it misses, report that plainly.** A miss is a valid result.
- **Phase 2 / Gate 2:** difference-in-differences across the 8 counties plus comparison metros, with effect size and confidence interval, in `research/`.
- **Phase 3 / Gate 3:** decided by Rob (paying customer or underwritten deal). Agents prepare materials only.
