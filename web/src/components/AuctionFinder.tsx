"use client";

import { useMemo, useState } from "react";

import {
  COUNTY_LABELS,
  countyLabel,
  type Listing,
  uniqueSorted,
} from "@/lib/listings";
import styles from "./AuctionFinder.module.css";

type Props = {
  listings: Listing[];
  generatedFrom: string;
};

function MultiFilter({
  label,
  options,
  selected,
  onChange,
  format = (v: string) => v,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
  format?: (value: string) => string;
}) {
  return (
    <fieldset className={styles.filterGroup}>
      <legend>{label}</legend>
      <div className={styles.chips}>
        {options.map((opt) => {
          const on = selected.includes(opt);
          return (
            <button
              key={opt}
              type="button"
              className={on ? styles.chipOn : styles.chip}
              aria-pressed={on}
              onClick={() =>
                onChange(on ? selected.filter((s) => s !== opt) : [...selected, opt])
              }
            >
              {format(opt)}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export default function AuctionFinder({ listings, generatedFrom }: Props) {
  const counties = useMemo(
    () => uniqueSorted(listings.map((l) => l.county_fips)),
    [listings],
  );
  const assetTypes = useMemo(
    () => uniqueSorted(listings.map((l) => l.asset_type)),
    [listings],
  );
  const statuses = useMemo(
    () => uniqueSorted(listings.map((l) => l.status)),
    [listings],
  );

  const [county, setCounty] = useState<string[]>(counties);
  const [assets, setAssets] = useState<string[]>(assetTypes);
  const [status, setStatus] = useState<string[]>(statuses);
  const [query, setQuery] = useState("");

  const view = useMemo(() => {
    const q = query.trim().toLowerCase();
    return listings
      .filter((l) => !county.length || (l.county_fips && county.includes(l.county_fips)))
      .filter((l) => !assets.length || assets.includes(l.asset_type))
      .filter((l) => !status.length || status.includes(l.status))
      .filter((l) => {
        if (!q) return true;
        const hay = [
          l.address,
          l.cause_no,
          l.account_no,
          l.vin,
          l.make,
          l.model,
          l.source,
          l.parcel_id,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return hay.includes(q);
      })
      .sort((a, b) => {
        const da = a.sale_date ?? "9999";
        const db = b.sale_date ?? "9999";
        return da.localeCompare(db);
      });
  }, [listings, county, assets, status, query]);

  const mapPoints = view.filter(
    (l) => typeof l.lat === "number" && typeof l.lon === "number" && !Number.isNaN(l.lat) && !Number.isNaN(l.lon),
  );

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <p className={styles.sidebarKicker}>Filters</p>
        <label className={styles.searchLabel}>
          Search
          <input
            className={styles.search}
            type="search"
            placeholder="Address, cause, VIN…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <MultiFilter
          label="County"
          options={counties}
          selected={county}
          onChange={setCounty}
          format={(f) => COUNTY_LABELS[f] ?? f}
        />
        <MultiFilter
          label="Asset type"
          options={assetTypes}
          selected={assets}
          onChange={setAssets}
        />
        <MultiFilter
          label="Status"
          options={statuses}
          selected={status}
          onChange={setStatus}
        />
        <p className={styles.rules}>
          Hard rules: no owner PII in this view; no demographics in scoring.
        </p>
        <p className={styles.meta}>{generatedFrom}</p>
      </aside>

      <section className={styles.main}>
        <header className={styles.toolbar}>
          <div>
            <p className={styles.metricLabel}>Listings</p>
            <p className={styles.metricValue}>{view.length}</p>
          </div>
          <button
            type="button"
            className={styles.reset}
            onClick={() => {
              setCounty(counties);
              setAssets(assetTypes);
              setStatus(statuses);
              setQuery("");
            }}
          >
            Reset filters
          </button>
        </header>

        {mapPoints.length > 0 ? (
          <div className={styles.mapNote}>
            {mapPoints.length} geocoded pin{mapPoints.length === 1 ? "" : "s"} ready
            (map layer wires after CAD geocode). Sample coords present in feed.
          </div>
        ) : (
          <div className={styles.mapNote}>
            No geocoded coordinates yet. Showing table only. Run resolve/geocode after CAD
            rolls load.
          </div>
        )}

        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Sale date</th>
                <th>Status</th>
                <th>Asset</th>
                <th>Sale type</th>
                <th>County</th>
                <th>Address / vehicle</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {view.map((l) => (
                <tr key={l.listing_id}>
                  <td>{l.sale_date ?? "—"}</td>
                  <td>
                    <span className={styles.status}>{l.status.replaceAll("_", " ")}</span>
                  </td>
                  <td>{l.asset_type.replaceAll("_", " ")}</td>
                  <td>{l.sale_type.replaceAll("_", " ")}</td>
                  <td>{countyLabel(l.county_fips)}</td>
                  <td>
                    {l.asset_type === "vehicle" ? (
                      <span>
                        {[l.year, l.make, l.model].filter(Boolean).join(" ") || "Vehicle"}
                        {l.vin ? (
                          <>
                            <br />
                            <span className={styles.muted}>VIN {l.vin}</span>
                          </>
                        ) : null}
                        {l.storage_facility ? (
                          <>
                            <br />
                            <span className={styles.muted}>{l.storage_facility}</span>
                          </>
                        ) : null}
                      </span>
                    ) : (
                      <span>
                        {l.address || "—"}
                        {l.cause_no || l.account_no ? (
                          <>
                            <br />
                            <span className={styles.muted}>
                              {[l.cause_no, l.account_no].filter(Boolean).join(" · ")}
                            </span>
                          </>
                        ) : null}
                      </span>
                    )}
                  </td>
                  <td>
                    <a href={l.url} target="_blank" rel="noreferrer">
                      {l.source}
                    </a>
                  </td>
                </tr>
              ))}
              {view.length === 0 ? (
                <tr>
                  <td colSpan={7} className={styles.empty}>
                    No listings match the current filters.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
