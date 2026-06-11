"""
Advanced data-cleaning pipeline.

Each public function corresponds to one of the 10 cleaning challenges in the
brief and is independently testable. ``clean_dataframe`` chains them in order
and returns a production-ready frame plus a quality report.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.utils import get_logger

logger = get_logger("data_cleaning")


@dataclass
class CleaningReport:
    """Accumulates before/after counts for a transparency audit."""
    steps: dict[str, str] = field(default_factory=dict)

    def log(self, step: str, detail: str) -> None:
        self.steps[step] = detail
        logger.info("[%s] %s", step, detail)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [{"step": k, "detail": v} for k, v in self.steps.items()]
        )


# --------------------------------------------------------------------------- #
# Challenge 1 — dates
# --------------------------------------------------------------------------- #
def clean_dates(df: pd.DataFrame, col: str = "order_date") -> pd.DataFrame:
    """Standardise mixed date formats to datetime, coercing invalids to NaT."""
    raw = df[col].astype("string").str.strip()

    parsed = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")
    for fmt in ("%d/%m/%Y", "%d-%m-%y", "%m/%d/%Y", "%d/%m/%y"):
        mask = parsed.isna()
        if mask.any():
            parsed.loc[mask] = pd.to_datetime(raw[mask], format=fmt, errors="coerce")

    # Drop impossible dates outside the project window.
    parsed = parsed.where(
        (parsed >= "2015-01-01") & (parsed <= "2025-12-31")
    )
    df[col] = parsed
    df["order_year"] = parsed.dt.year
    df["order_month"] = parsed.dt.month
    df["order_quarter"] = parsed.dt.quarter
    return df


# --------------------------------------------------------------------------- #
# Challenge 2 — prices
# --------------------------------------------------------------------------- #
def clean_prices(df: pd.DataFrame, col: str = "original_price_inr") -> pd.DataFrame:
    """Strip currency symbols / separators; 'Price on Request' -> NaN."""
    def parse(v: object) -> float:
        if pd.isna(v):
            return np.nan
        s = str(v).strip()
        if not s or "request" in s.lower():
            return np.nan
        s = re.sub(r"[^\d.]", "", s.replace(",", ""))
        try:
            return float(s)
        except ValueError:
            return np.nan

    df[col] = df[col].map(parse)
    return df


# --------------------------------------------------------------------------- #
# Challenge 3 — ratings
# --------------------------------------------------------------------------- #
def clean_ratings(df: pd.DataFrame, col: str = "customer_rating") -> pd.DataFrame:
    """Normalise '4 stars', '3/5', '2.5/5.0' etc. to a 1.0-5.0 float."""
    def parse(v: object) -> float:
        if pd.isna(v):
            return np.nan
        s = str(v).lower().strip()
        m = re.match(r"([\d.]+)\s*/\s*5", s)         # x/5 or x/5.0
        if m:
            val = float(m.group(1))
        else:
            m = re.match(r"([\d.]+)", s)             # "4 stars" / "5.0"
            val = float(m.group(1)) if m else np.nan
        if np.isnan(val):
            return np.nan
        return float(min(5.0, max(1.0, round(val * 2) / 2)))

    df[col] = df[col].map(parse)
    # Strategic imputation: fill blanks with the product's median rating.
    if "product_id" in df.columns:
        med = df.groupby("product_id")[col].transform("median")
        df[col] = df[col].fillna(med)
    df[col] = df[col].fillna(df[col].median())
    return df


# --------------------------------------------------------------------------- #
# Challenge 4 — cities
# --------------------------------------------------------------------------- #
CITY_CANONICAL = {
    "bangalore": "Bengaluru", "banglore": "Bengaluru", "bengaluru": "Bengaluru",
    "bombay": "Mumbai", "mumbai": "Mumbai",
    "new delhi": "Delhi", "delhi": "Delhi",
    "calcutta": "Kolkata", "kolkata": "Kolkata",
    "madras": "Chennai", "chennai": "Chennai",
}


def clean_cities(df: pd.DataFrame, col: str = "customer_city") -> pd.DataFrame:
    """Resolve city aliases / casing / common misspellings."""
    def fix(v: object) -> object:
        if pd.isna(v):
            return v
        key = str(v).strip().lower()
        return CITY_CANONICAL.get(key, str(v).strip().title())

    df[col] = df[col].map(fix)
    return df


# --------------------------------------------------------------------------- #
# Challenge 5 — booleans
# --------------------------------------------------------------------------- #
TRUE_TOKENS = {"true", "yes", "y", "1", "1.0"}
FALSE_TOKENS = {"false", "no", "n", "0", "0.0"}


def clean_booleans(df: pd.DataFrame,
                   cols: tuple[str, ...] = ("is_prime_member",
                                            "is_prime_eligible",
                                            "is_festival_sale")) -> pd.DataFrame:
    """Convert mixed truthy/falsey representations to real booleans."""
    def to_bool(v: object) -> object:
        if pd.isna(v):
            return False                              # missing -> conservative False
        s = str(v).strip().lower()
        if s in TRUE_TOKENS:
            return True
        if s in FALSE_TOKENS:
            return False
        return False

    for c in cols:
        if c in df.columns:
            df[c] = df[c].map(to_bool).astype(bool)
    return df


# --------------------------------------------------------------------------- #
# Challenge 6 — categories
# --------------------------------------------------------------------------- #
CATEGORY_CANONICAL = {
    "electronic": "Electronics", "electronics": "Electronics",
    "electronics & accessories": "Electronics",
    "apparel": "Fashion", "fashion": "Fashion",
    "home and kitchen": "Home & Kitchen", "home & kitchen": "Home & Kitchen",
}


def clean_categories(df: pd.DataFrame, col: str = "category") -> pd.DataFrame:
    """Collapse category casing / aliases to canonical names."""
    def fix(v: object) -> object:
        if pd.isna(v):
            return v
        key = str(v).strip().lower()
        return CATEGORY_CANONICAL.get(key, str(v).strip().title())

    df[col] = df[col].map(fix)
    return df


# --------------------------------------------------------------------------- #
# Challenge 7 — delivery days
# --------------------------------------------------------------------------- #
def clean_delivery_days(df: pd.DataFrame, col: str = "delivery_days") -> pd.DataFrame:
    """Parse text/ranges, drop negatives and unrealistic values (>15)."""
    def parse(v: object) -> float:
        if pd.isna(v):
            return np.nan
        s = str(v).strip().lower()
        if "same day" in s:
            return 0.0
        nums = re.findall(r"\d+", s)
        if not nums:
            return np.nan
        val = np.mean([int(n) for n in nums])         # '1-2 days' -> 1.5
        if val < 0 or val > 15:                        # unrealistic
            return np.nan
        return float(val)

    df[col] = df[col].map(parse)
    df[col] = df[col].fillna(df[col].median())
    return df


# --------------------------------------------------------------------------- #
# Challenge 8 — duplicates
# --------------------------------------------------------------------------- #
def handle_duplicates(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    """Drop exact duplicate transaction_ids (data errors); keep distinct rows.

    A genuine bulk order has a unique transaction_id even with same customer /
    product / date, so we only remove rows that duplicate the *id*.
    """
    before = len(df)
    df = df.drop_duplicates(subset="transaction_id", keep="first")
    report.log("duplicates", f"removed {before - len(df)} duplicate transaction_ids")
    return df


# --------------------------------------------------------------------------- #
# Challenge 9 — price outliers (decimal-point errors)
# --------------------------------------------------------------------------- #
def fix_price_outliers(df: pd.DataFrame,
                       price_col: str = "original_price_inr") -> pd.DataFrame:
    """Detect ~100x decimal errors per category and divide them back down."""
    if "category" not in df.columns:
        return df

    # Per-category median as a benchmark; flag values ~100x above it.
    cat_median = df.groupby("category")[price_col].transform("median")
    mask = (df[price_col] > cat_median * 50) & cat_median.notna() & (cat_median > 0)
    df.loc[mask, price_col] = df.loc[mask, price_col] / 100.0
    return df


# --------------------------------------------------------------------------- #
# Challenge 10 — payment methods
# --------------------------------------------------------------------------- #
PAYMENT_CANONICAL = {
    "phonepe": "UPI", "googlepay": "UPI", "paytm upi": "UPI", "upi": "UPI",
    "credit_card": "Credit Card", "cc": "Credit Card", "credit card": "Credit Card",
    "cod": "Cash on Delivery", "c.o.d": "Cash on Delivery",
    "cash on delivery": "Cash on Delivery",
    "netbanking": "Net Banking", "net banking": "Net Banking",
    "debit card": "Debit Card", "emi": "EMI", "wallet": "Wallet",
}


def clean_payment_methods(df: pd.DataFrame, col: str = "payment_method") -> pd.DataFrame:
    """Map payment aliases to a clean categorical hierarchy."""
    def fix(v: object) -> object:
        if pd.isna(v):
            return "Unknown"
        return PAYMENT_CANONICAL.get(str(v).strip().lower(), str(v).strip().title())

    df[col] = df[col].map(fix).astype("category")
    return df


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Run the full cleaning pipeline and return (clean_df, report)."""
    report = CleaningReport()
    start_rows = len(df)

    df = clean_dates(df)
    df = clean_prices(df)
    df = clean_categories(df)
    df = fix_price_outliers(df)                       # group on canonical categories
    df = clean_ratings(df)
    df = clean_cities(df)
    df = clean_booleans(df)
    df = clean_delivery_days(df)
    df = clean_payment_methods(df)
    df = handle_duplicates(df, report)

    # Drop rows that lost their date (unparseable) or amount.
    before = len(df)
    df = df.dropna(subset=["order_date", "final_amount_inr"])
    report.log("dropped_invalid", f"removed {before - len(df)} rows missing date/amount")

    report.log("rows", f"{start_rows:,} raw -> {len(df):,} clean")
    report.log("null_pct",
               f"{df.isna().mean().mean() * 100:.2f}% mean null across columns")
    return df.reset_index(drop=True), report
