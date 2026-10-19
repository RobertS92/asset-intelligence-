export type Listing = {
  listing_id: string;
  source: string;
  source_key: string;
  asset_type: string;
  sale_type: string;
  sale_date: string | null;
  status: string;
  county_fips: string | null;
  address: string | null;
  parcel_id: string | null;
  vin: string | null;
  min_bid_usd: number | string | null;
  redemption_days: number | null;
  url: string;
  cause_no?: string | null;
  account_no?: string | null;
  make?: string | null;
  model?: string | null;
  year?: number | string | null;
  storage_facility?: string | null;
  notes?: string | null;
  lat?: number | null;
  lon?: number | null;
};

export type ListingsPayload = {
  generated_from: string;
  count: number;
  listings: Listing[];
};

export const COUNTY_LABELS: Record<string, string> = {
  "48085": "Collin",
  "48113": "Dallas",
  "48121": "Denton",
  "48157": "Fort Bend",
  "48201": "Harris",
  "48439": "Tarrant",
  "48453": "Travis",
  "48491": "Williamson",
};

export function countyLabel(fips: string | null | undefined): string {
  if (!fips) return "Unknown";
  return COUNTY_LABELS[fips] ?? fips;
}

export function uniqueSorted(values: Array<string | null | undefined>): string[] {
  return [...new Set(values.filter((v): v is string => Boolean(v)))].sort();
}
