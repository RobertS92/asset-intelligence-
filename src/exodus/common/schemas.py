"""Data contracts. Changing these requires a needs-rob issue (AGENTS.md §5)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha1
from typing import Literal

from pydantic import BaseModel, HttpUrl

AssetType = Literal["real_property", "vehicle", "equipment", "business", "contents", "other"]
SaleType = Literal[
    "tax_sale",
    "trustee_sale",
    "reo",
    "impound_auction",
    "gov_surplus",
    "federal_seizure",
    "equipment_auction",
    "bankruptcy_sale",
    "storage_lien",
]
ListingStatus = Literal["scheduled", "for_sale", "withdrawn", "sold", "struck_off", "unknown"]
DistressEventType = Literal[
    "tax_delinquent",
    "tax_suit",
    "trustee_notice",
    "hoa_lien",
    "code_violation",
    "usps_vacant",
    "homestead_removed",
    "mailing_moved_out_of_state",
]


class ListingStatusEnum(StrEnum):
    SCHEDULED = "scheduled"
    FOR_SALE = "for_sale"
    WITHDRAWN = "withdrawn"
    SOLD = "sold"
    STRUCK_OFF = "struck_off"
    UNKNOWN = "unknown"


STATUS_MAP: dict[str, ListingStatus] = {
    "for sale": "for_sale",
    "for_sale": "for_sale",
    "scheduled": "scheduled",
    "withdrawn": "withdrawn",
    "withdrawn prior to dc": "withdrawn",
    "withdrawn prior to sale": "withdrawn",
    "sold": "sold",
    "struck off": "struck_off",
    "struck_off": "struck_off",
    "unknown": "unknown",
}


def map_status(raw: str) -> ListingStatus:
    key = raw.strip().lower()
    if key not in STATUS_MAP:
        raise ValueError(f"Unknown listing status: {raw!r}")
    return STATUS_MAP[key]


def make_listing_id(source: str, source_key: str) -> str:
    return sha1(f"{source}|{source_key}".encode()).hexdigest()


class Listing(BaseModel):
    """One auction/sale item."""

    listing_id: str
    source: str
    source_key: str
    asset_type: AssetType
    sale_type: SaleType
    sale_date: date | None = None
    status: ListingStatus
    county_fips: str | None = None
    address: str | None = None
    parcel_id: str | None = None
    vin: str | None = None
    min_bid_usd: Decimal | None = None
    redemption_days: int | None = None
    url: HttpUrl
    raw_ref: str
    fetched_at: datetime
    notes: str | None = None
    cause_no: str | None = None
    account_no: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    storage_facility: str | None = None
    legal_description: str | None = None


class DistressEvent(BaseModel):
    """Labels + features for parcels."""

    parcel_id: str
    event_type: DistressEventType
    event_date: date
    source: str
    raw_ref: str


class TractExposure(BaseModel):
    """RESEARCH ONLY — never imported by scoring/."""

    tract_geoid: str
    period: str
    metric: str
    value: float
    source: str


class StatusHistoryRow(BaseModel):
    listing_id: str
    old_status: ListingStatus
    new_status: ListingStatus
    changed_at: date
    source: str


# Column / field names that must never appear in scoring schemas or feature tables.
DEMOGRAPHIC_FORBIDDEN: frozenset[str] = frozenset(
    {
        "race",
        "ethnicity",
        "national_origin",
        "ancestry",
        "language",
        "surname",
        "religion",
        "hispanic",
        "latino",
        "black",
        "white",
        "asian",
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
)


class ParcelFeatures(BaseModel):
    """Property-level features only — no demographics (AGENTS.md §2)."""

    parcel_id: str
    county_fips: str
    scoring_date: date
    months_delinquent: float | None = None
    amount_owed_usd: float | None = None
    assessed_value_usd: float | None = None
    owed_to_value_ratio: float | None = None
    prior_delinquency: bool = False
    purchase_year: int | None = None
    purchase_price_usd: float | None = None
    estimated_ltv: float | None = None
    hoa_lien: bool = False
    mailing_out_of_state: bool = False
    utility_shutoff: bool = False
    code_violations: int = 0
    listing_vacant_remark: bool = False
    listing_expired: bool = False
    price_cut: bool = False
    days_on_market: float | None = None
    nearby_foreclosures: int = 0
    label_6m: int | None = None
    label_12m: int | None = None
