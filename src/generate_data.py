"""
Synthetic data generator for the Amazon India analytics project.

The brief ships a ~1M-row dataset with ~25% intentional data-quality issues.
Since that file is not bundled here, this module fabricates data with the *same
schema and the same defects* so the cleaning / EDA / dashboard code is fully
runnable. If you have the real CSVs, drop them in ``data/raw/`` using the same
file names and skip this step — the downstream code only depends on column
names, not on how the data was produced.

Defects injected (mapped to the 10 cleaning challenges):
    1. Mixed / invalid date formats
    2. Price strings with rupee symbols, commas, "Price on Request"
    3. Rating formats: "4 stars", "3/5", "2.5/5.0", blanks
    4. City name variants and case noise
    5. Boolean noise: Yes/No, 1/0, Y/N, blanks
    6. Category casing / aliasing
    7. Delivery days: "Same Day", "1-2 days", negatives, 50
    8. Duplicate transactions (genuine bulk vs accidental)
    9. 100x price outliers (decimal-point errors)
   10. Payment method aliases (PhonePe, CC, C.O.D, ...)
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

import config
from src.utils import get_logger, timer

logger = get_logger("generate_data")

# Messy-value lookups -------------------------------------------------------- #
CITY_VARIANTS = {
    "Bengaluru": ["Bangalore", "bengaluru", "BENGALURU", "Banglore"],
    "Mumbai": ["Bombay", "mumbai", "MUMBAI"],
    "Delhi": ["New Delhi", "delhi", "NEW DELHI"],
    "Kolkata": ["Calcutta", "kolkata"],
    "Chennai": ["Madras", "chennai"],
}
CATEGORY_VARIANTS = {
    "Electronics": ["Electronic", "ELECTRONICS", "Electronics & Accessories", "electronics"],
    "Fashion": ["fashion", "FASHION", "Apparel"],
    "Home & Kitchen": ["Home and Kitchen", "home & kitchen", "HOME & KITCHEN"],
}
PAYMENT_VARIANTS = {
    "UPI": ["PhonePe", "GooglePay", "upi", "Paytm UPI"],
    "Credit Card": ["CREDIT_CARD", "CC", "credit card"],
    "Cash on Delivery": ["COD", "C.O.D", "cash on delivery"],
    "Net Banking": ["NetBanking", "net banking", "NETBANKING"],
}


def _build_catalog(rng: random.Random) -> pd.DataFrame:
    """Create the product master catalog (clean reference data)."""
    rows = []
    cat_subcat = [(c, s) for c, subs in config.CATEGORIES.items() for s in subs]
    for i in range(config.N_PRODUCTS):
        category, subcategory = rng.choice(cat_subcat)
        base = round(rng.uniform(150, 90_000), 2)
        rows.append({
            "product_id": f"P{i:05d}",
            "product_name": f"{rng.choice(config.BRANDS)} {subcategory} {rng.randint(100, 999)}",
            "category": category,
            "subcategory": subcategory,
            "brand": rng.choice(config.BRANDS),
            "base_price_2015": base,
            "weight_kg": round(rng.uniform(0.1, 15.0), 2),
            "rating": round(rng.uniform(2.5, 5.0), 1),
            "is_prime_eligible": rng.random() < 0.6,
            "launch_year": rng.randint(config.START_YEAR, config.END_YEAR),
            "model": f"M{rng.randint(1000, 9999)}",
        })
    return pd.DataFrame(rows)


def _messy_date(d: date, rng: random.Random) -> str:
    """Return a date rendered in one of several inconsistent formats."""
    fmt = rng.random()
    if fmt < 0.30:
        return d.strftime("%d/%m/%Y")
    if fmt < 0.55:
        return d.strftime("%d-%m-%y")
    if fmt < 0.85:
        return d.strftime("%Y-%m-%d")
    if fmt < 0.93:
        return d.strftime("%m/%d/%Y")            # ambiguous US order
    return rng.choice(["32/13/2020", "00/00/0000", "not available", ""])  # invalid


def _messy_price(value: float, rng: random.Random) -> str | float:
    """Return a price as a noisy string or a decimal-error outlier."""
    roll = rng.random()
    if roll < 0.35:
        return f"\u20b9{value:,.0f}"               # ₹1,25,000 style
    if roll < 0.50:
        return f"{value:,.2f}"
    if roll < 0.58:
        return "Price on Request"
    if roll < 0.63:
        return round(value * 100, 2)               # decimal-point outlier (challenge 9)
    return round(value, 2)


def _messy_rating(rng: random.Random) -> str | float | None:
    base = round(rng.uniform(1.0, 5.0) * 2) / 2     # .0 or .5
    roll = rng.random()
    if roll < 0.20:
        return None
    if roll < 0.40:
        return f"{int(round(base))} stars"
    if roll < 0.55:
        return f"{int(round(base))}/5"
    if roll < 0.70:
        return f"{base}/5.0"
    return base


def _messy_bool(true_prob: float, rng: random.Random) -> object:
    val = rng.random() < true_prob
    style = rng.choice(["bool", "yesno", "10", "yn", "blank"])
    if style == "blank" and rng.random() < 0.3:
        return None
    if style == "yesno":
        return "Yes" if val else "No"
    if style == "10":
        return 1 if val else 0
    if style == "yn":
        return "Y" if val else "N"
    return val


def _messy_delivery(rng: random.Random) -> object:
    roll = rng.random()
    if roll < 0.70:
        return rng.randint(1, 9)
    if roll < 0.80:
        return "Same Day"
    if roll < 0.88:
        return f"{rng.randint(1, 3)}-{rng.randint(4, 6)} days"
    if roll < 0.94:
        return -rng.randint(1, 3)                  # invalid negative
    return rng.choice([50, 99, None])              # unrealistic / missing


def _apply_variant(canonical: str, mapping: dict, rng: random.Random) -> str:
    """With some probability swap a clean value for a messy variant."""
    if canonical in mapping and rng.random() < 0.45:
        return rng.choice(mapping[canonical])
    return canonical


def generate() -> None:
    """Generate the product catalog and one messy CSV per year."""
    rng = random.Random(config.RANDOM_SEED)
    np.random.seed(config.RANDOM_SEED)

    with timer("Catalog generation", logger):
        catalog = _build_catalog(rng)
        catalog.to_csv(config.RAW_DIR / "amazon_india_products_catalog.csv", index=False)
        logger.info("Wrote catalog with %d products", len(catalog))

    cities = list(config.CITY_TIERS.keys())
    txn_counter = 0

    for year in range(config.START_YEAR, config.END_YEAR + 1):
        # Revenue grows over the decade; UPI adoption rises, COD declines.
        growth = 1.0 + 0.12 * (year - config.START_YEAR)
        n_rows = int(config.ROWS_PER_YEAR * growth)
        upi_share = min(0.65, 0.05 + 0.06 * (year - config.START_YEAR))

        records = []
        with timer(f"Year {year} ({n_rows} rows)", logger):
            for _ in range(n_rows):
                prod = catalog.iloc[rng.randrange(len(catalog))]
                price = float(prod["base_price_2015"]) * (1.0 + 0.06 * (year - config.START_YEAR))
                discount = rng.choice([0, 0, 5, 10, 15, 20, 30, 40, 50])
                final_amt = round(price * (1 - discount / 100), 2)

                # Festival skew: more rows in Oct/Nov.
                month = rng.choices(range(1, 13),
                                    weights=[6, 5, 6, 6, 7, 6, 7, 7, 8, 12, 14, 9])[0]
                day = rng.randint(1, 28)
                d = date(year, month, day)
                is_fest = month in (10, 11) and rng.random() < 0.4

                canonical_city = rng.choice(cities)
                canonical_cat = prod["category"]
                canonical_pay = rng.choices(
                    config.PAYMENT_METHODS,
                    weights=[upi_share, 0.18, 0.12, 0.10,
                             max(0.05, 0.40 - upi_share), 0.08, 0.07],
                )[0]
                state, tier = config.CITY_TIERS[canonical_city]

                records.append({
                    "transaction_id": f"T{txn_counter:08d}",
                    "customer_id": f"C{rng.randint(1, n_rows // 3):07d}",
                    "product_id": prod["product_id"],
                    "product_name": prod["product_name"],
                    "category": _apply_variant(canonical_cat, CATEGORY_VARIANTS, rng),
                    "subcategory": prod["subcategory"],
                    "brand": prod["brand"],
                    "product_rating": prod["rating"],
                    "order_date": _messy_date(d, rng),
                    "order_year": year,
                    "original_price_inr": _messy_price(price, rng),
                    "discount_percent": discount,
                    "final_amount_inr": final_amt,
                    "delivery_charges": rng.choice([0, 0, 40, 60, 99]),
                    "customer_city": _apply_variant(canonical_city, CITY_VARIANTS, rng),
                    "customer_state": state,
                    "customer_tier": tier,
                    "age_group": rng.choice(config.AGE_GROUPS),
                    "is_prime_member": _messy_bool(0.45 + 0.03 * (year - config.START_YEAR), rng),
                    "payment_method": _apply_variant(canonical_pay, PAYMENT_VARIANTS, rng),
                    "delivery_days": _messy_delivery(rng),
                    "return_status": rng.choices(["Not Returned", "Returned"],
                                                 weights=[0.88, 0.12])[0],
                    "customer_rating": _messy_rating(rng),
                    "is_festival_sale": _messy_bool(0.4 if is_fest else 0.02, rng),
                    "festival_name": (rng.choice(config.FESTIVALS) if is_fest else None),
                    "customer_spending_tier": rng.choice(["Low", "Medium", "High", "Premium"]),
                })
                txn_counter += 1

            df = pd.DataFrame(records)

            # Challenge 8: inject duplicate transactions (genuine + accidental).
            dupes = df.sample(frac=0.03, random_state=year)
            df = pd.concat([df, dupes], ignore_index=True)

            df.to_csv(config.RAW_DIR / f"amazon_india_{year}.csv", index=False)
            logger.info("Wrote %d rows for %d (incl. %d duplicates)",
                        len(df), year, len(dupes))

    logger.info("Synthetic generation complete: %d base transactions", txn_counter)


if __name__ == "__main__":
    generate()
