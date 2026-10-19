# CONTEXT.md — Exodus Asset Signals

> Background, verified facts, decisions, and open questions. Rules live in `AGENTS.md`.
> Every fact here has a source and a date. If you can't source it, it goes under Open Questions, not Facts.
> Last full review: 2026-10-18.

## 1. Origin and thesis

- **Trigger:** viral social posts and a podcast clip (Oct 2026) claimed H-1B families in DFW suburbs (Celina, Melissa, Frisco) are leaving the US and abandoning homes and cars, including cars at DFW Airport long-term parking.
- **Status of that claim:** *unverified.* Coverage repeating it says it hasn't been independently confirmed and doesn't show a large-scale trend ([NewsKarnataka, Sep 2026](https://newskarnataka.com/india/viral-post-claims-h-1b-families-are-leaving-us-homes-behind/11092026/)).
- **Hypothesis H1:** census tracts with high H-1B exposure show faster growth in tax delinquency, foreclosure notices, and vacancy after the 2025–26 policy changes than matched low-exposure tracts.
- **Hypothesis H2:** green card holder concentration has a much weaker effect than H-1B exposure. Green card holders don't lose status when they lose a job; they risk it by staying abroad for more than a year without a reentry permit.
- **Business thesis:** whether or not H1 holds, a parcel-level distress model plus one unified auction feed may be valuable, to Rob as a buyer or sold as a signal to investors. That gets tested at Gate 3.

## 2. Scope

| Tier | County | FIPS |
|---|---|---|
| Texas core | Collin | 48085 |
| Texas core | Denton | 48121 |
| Texas core | Dallas | 48113 |
| Texas core | Tarrant | 48439 |
| Houston | Fort Bend | 48157 |
| Houston | Harris | 48201 |
| Austin | Travis | 48453 |
| Austin | Williamson | 48491 |

**Comparison metros (research only, Phase 2):** Santa Clara CA, King WA, Middlesex NJ, Forsyth and Fulton GA, Mecklenburg NC, Maricopa AZ, DuPage and Cook IL.

**Asset priority:** real property → vehicles → equipment → small businesses → storage contents.

## 3. Verified facts (with sources)

### Texas law

- **Tax-sale redemption:** homestead and agricultural property can be redeemed for **2 years** after the purchaser's deed is recorded. The premium is 25% in year 1 and 50% in year 2. Other property: **180 days**, premium capped at 25%. Texas is a tax-deed state. ([Lone Star Land Law](https://lonestarlandlaw.com/redemption-issues-for-investors/); [Nolo](https://www.nolo.com/legal-encyclopedia/what-happens-if-i-dont-pay-property-taxes-texas.html))
- **Property-tax timeline:** taxes become delinquent after **Feb 1**. Penalties and interest build up, and a collection-attorney fee of up to 20% can be added. ([Cronista](https://www.cronista.com/en/finance/homeowners-could-lose-their-homes-for-delaying-this-tax-procedure/))
- **Abandoned vehicles:** Texas Transportation Code **Ch. 683**. A law enforcement agency takes custody, sends notice, and sells unclaimed vehicles at a **public auction** after proper notice. Private individuals can't seize vehicles. ([Ch. 683](https://statutes.capitol.texas.gov/Docs/TN/htm/TN.683.htm))
- **Trustee (mortgage) sales:** held on the first Tuesday of the month. The notice of sale is posted at least 21 days before. *(Confirm: cite Tex. Prop. Code §51.002 directly before relying on this in code comments.)*

### Auction sources (checked 2026-10-18)

- **Tarrant Constable Pct. 3** posts a monthly HTML page per sale date with tables of Cause No., Account No., and Status ("For Sale", "Withdrawn", "Withdrawn Prior to DC"), grouped by collection firm (Linebarger; Perdue Brandon), plus a writs-of-execution block with address and legal description. The Nov 3, 2026 page had 35 table rows and 7 writs. ([page](https://www.tarrantcountytx.gov/en/constables/constable-3/delinquent-tax-sales/monthly-tax-sales-listings/november-3--2026.html))
- **Houston PD vehicle auctions:** public, valid ID required, cash only, as-is; held at the storage facilities, starting 8:00 a.m. daily. Salvage vehicles are sold only to licensed salvage dealers. **Buying 5 or more vehicles a year requires a dealer (MVD) license.** Listings are on houstontx.gov ("Vehicles Scheduled For Auction") and on PublicSurplus. The buyer gets an Auction Sales Receipt and takes it to the county tax office for title. ([HPD](https://houstontx.gov/police/auto_dealers_detail/vehicle_auction.htm))
- **Harris County Sheriff** publishes vehicle auction lists as PDFs. ([Jan–Mar 2026 list](https://www.harriscountyso.org/Documents/Frontpage/HC_Auctions_Jan-Mar_2026_2026-02-13.pdf))
- **Linebarger** publishes county sale-list PDFs (e.g. `taxsalesib.lgbs.com/.../County_Sale_list_<COUNTY>_<YYYYMMDD>.pdf`). Its search site **taxsales.lgbs.com disallows crawling in robots.txt**, so use the PDFs and email alerts only.
- **Federal programs:** GSA Auctions (surplus), U.S. Treasury (forfeited property), U.S. Marshals (DOJ seizures). ([USA.gov](https://cms-dr.usa.gov/auctions-and-sales))

### Policy timeline (event dates for difference-in-differences)

| Date | Event | Source |
|---|---|---|
| 2025-12-29 | DHS final rule weighting the H-1B lottery by wage level (effective 2026-02-27) | [f1jobs summary](https://www.f1jobs.io/resources/blog/lca-uscis-employer-data-hub-build-target-company-list) — confirm on Federal Register |
| 2026-04 (late) | Texas AG expands H-1B probe; civil investigative demands to ~30 North Texas businesses | [WION](https://embed.wionews.com/world/indians-on-h-1b-visas-exit-texas-and-its-housing-boom-is-dying-other-states-could-see-decline-1780742655656) |
| 2026-05-22 | USCIS memo PM-602-0199: adjustment of status inside the US becomes discretionary ("extraordinary circumstances") | [Dawn via Spill](https://news.spill.org/en/article/green-card-seekers-must-leave-us-first-405) |
| 2026-05-30 | DHS says skilled applicants will see "no noticeable impact" | [Bloomberg Law](https://news.bloomberglaw.com/us-law-week/dhs-backs-off-its-demand-for-green-card-applicants-to-leave-us) |
| 2026 (date TBC) | Texas Governor orders state agencies and universities to stop new H-1B petitions until at least 2027-05-31 | [Deccan Chronicle](https://www.deccanchronicle.com/world/texas-plans-to-probe-h-1b-visa-frauds-1933624) — confirm the date at gov.texas.gov |

### Market context

- US foreclosure filings rose more than 20% in H1 2026; ATTOM describes this as mostly a return to normal levels. This is the background trend the difference-in-differences must net out. ([National Mortgage News](https://www.nationalmortgagenews.com/news/spiking-local-foreclosures-signal-new-credit-risks))
- Texas had 4,091 foreclosure filings in June 2026, and Fort Bend had the largest month-over-month jump. *Reported by a podcast; confirm with the county clerk.* ([source](https://apx-security-uk.audible.co.uk/pd/B0H36HKQVQ))
- A Collin County builder reported its South Asian buyer share fell from 70% to under 30%. *Reported claim, single source.* ([WION](https://embed.wionews.com/world/indians-on-h-1b-visas-exit-texas-and-its-housing-boom-is-dying-other-states-could-see-decline-1780742655656))

## 4. Data layers

Full registry: `config/sources.yaml`. Summary by role:

| Layer | Allowed in scoring? | Key sources |
|---|---|---|
| Exposure (visa, demographics) | **No** — research only | DOL LCA and PERM disclosures, [DOL DuckDB mirror](https://huggingface.co/datasets/Nason/dol-visas-database), USCIS H-1B Employer Data Hub, OHSS new-LPR county tables, ACS 5-year (B05006, B05001), HMDA (ancestry fields) |
| Triggers | Aggregates only | Texas WARN notices, QCEW, policy event dates |
| Departure proxies | Yes, at parcel level when not demographic | USPS vacancy (HUD), appraisal-district homestead removals and mailing-address moves, TEA enrollment (research), Google Trends (research) |
| Distress (labels and features) | Yes | Appraisal-district rolls, delinquent tax rolls, clerk trustee notices, HOA liens, 311 code violations, Fannie/Freddie loan performance (3-digit ZIP), Zillow/Realtor.com |
| Acquisition channels | Yes | Constable and sheriff tax sales, trustee sales, REO (HUD, HomePath), Ch. 683 auctions, GovDeals, PublicSurplus, GSA, Treasury, Marshals, RB Global, Purple Wave, PACER/CourtListener |

## 5. Model design (summary)

- **Tract model** (research): difference-in-differences with `pyfixest`, a synthetic-control check, Getis-Ord hot spots, change-point detection, and a dynamic-factor nowcast.
- **Parcel model** (scoring): LightGBM classifier with SHAP reasons, plus a survival model (`lifelines`), at 6- and 12-month horizons.
- **Labels:** trustee notice, tax suit or tax-sale listing, USPS vacancy for 90+ days, homestead removed with no new sale.
- **Validation:** time-based split (train 2022–24, test 2025–26). Metrics: top-5% and top-10% precision, calibration, and lead time. Baseline: tax-delinquent more than 6 months.
- **Fairness check:** after scoring, confirm (in `research/`) that scores don't track tract demographics once property features are controlled for. If they do, escalate.

## 6. Gates

| Gate | When | Pass | If fail |
|---|---|---|---|
| 1 | End of week 3 | Top-10% precision ≥ 2× baseline, ≥ 200 positives | Stop; write up the findings |
| 2 | End of week 7 | Effect estimate with CI produced | Effect null → drop H1, keep the general distress model |
| 3 | End of week 12 | 1 paying customer or 1 underwritten deal | Shelve |

Paid data (ATTOM, PropStream, Placer.ai, Nearmap) only after Gate 1, and only with Rob's approval.

## 7. Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-10-09 | Use H-1B exposure (DOL/USCIS) instead of ethnicity as the research variable | More precise, and avoids a fair-housing problem |
| 2026-10-09 | Demographics are research-only; scoring is property-only | Fair Housing Act; protects outreach |
| 2026-10-09 | Green card holders studied as a separate hypothesis (H2) | Different status rules |
| 2026-10-18 | Scheduled daily jobs, not 24/7; web app only after Gate 1 | Data cadence is daily to monthly |
| 2026-10-18 | Start with Tarrant, Harris, Collin tax sales plus Houston and Harris vehicle auctions | Public, structured, recurring |
| 2026-10-19 | Scaffold Phase 1 repo; Tarrant golden fixture locked (35+7); Houston PD list URL is Vehicles_Scheduled_For_Auction.htm | First feed + firewall |
| 2026-10-19 | Hosted Auction Finder is Next.js under `web/` on Vercel; Streamlit stays local-only (`app/`) | Streamlit needs WebSockets; Vercel is serverless |

## 8. Open questions

- [ ] Will Collin and Fort Bend appraisal districts provide historical certified rolls back to 2022? What format and cost?
- [ ] Is there an MLS data partner (licensed agent) for listing remarks?
- [ ] Will title companies share aggregate counts of remote, power-of-attorney, or apostille seller closings?
- [ ] Which DFW-area storage facilities hold airport tow contracts (TDLR roster)?
- [ ] Confirm the trustee-sale notice period (Prop. Code §51.002) and the Texas H-1B order date from primary sources.
- [ ] **CAD access (2026-10-19):** Drop certified rolls into `data/raw/cad_rolls/{collin,tarrant,harris}/`. Fetchers are loaders only (manual bulk export). Cost/format still unknown for Collin and Fort Bend historical rolls.
- [ ] **Harris SO vehicle PDFs (2026-10-19):** Jan–Mar 2026 PDF is a *schedule* of auction locations/dates, not per-VIN rows. Need the linked per-facility auction lists for VIN-level coverage.

## 9. Glossary

- **CAD:** county appraisal district. **Roll:** the appraisal district's annual list of parcels and values.
- **Trustee sale:** non-judicial mortgage foreclosure auction, held on the first Tuesday of the month.
- **Struck off:** a tax-sale parcel with no bidder, which goes to the taxing unit.
- **LCA:** Labor Condition Application (DOL), required before an H-1B petition. Shows employer intent, not a hire.
- **LPR:** lawful permanent resident (green card holder).
- **H3:** Uber's hexagonal grid system; resolution 8 cells are about 0.7 km².
- **DiD:** difference-in-differences.
