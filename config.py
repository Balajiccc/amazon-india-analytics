"""
Central configuration for the Amazon India Sales Analytics project.

All paths are resolved relative to the project root so the code runs the same
regardless of the working directory it is invoked from.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT: Path = Path(__file__).resolve().parent
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs"
EDA_PLOTS_DIR: Path = OUTPUTS_DIR / "eda_plots"
DB_PATH: Path = PROCESSED_DIR / "amazon_india.db"

for _p in (RAW_DIR, PROCESSED_DIR, OUTPUTS_DIR, EDA_PLOTS_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Dataset shape
# --------------------------------------------------------------------------- #
START_YEAR: int = 2015
END_YEAR: int = 2025
N_PRODUCTS: int = 2000

# Transactions generated per year by the synthetic generator.
# The full spec targets ~1M rows total. Keep this modest for fast local runs;
# bump it up (e.g. 90_000) to approach the 1M-row target.
ROWS_PER_YEAR: int = 9_000

# Fraction of cells that receive an intentional data-quality defect.
QUALITY_ISSUE_RATE: float = 0.25

RANDOM_SEED: int = 42

# --------------------------------------------------------------------------- #
# Canonical domain vocabularies (the "clean" target values)
# --------------------------------------------------------------------------- #
CATEGORIES: dict[str, list[str]] = {
    "Electronics": ["Smartphones", "Laptops", "Headphones", "Cameras"],
    "Fashion": ["Men Clothing", "Women Clothing", "Footwear", "Watches"],
    "Home & Kitchen": ["Cookware", "Furniture", "Decor", "Appliances"],
    "Books": ["Fiction", "Non-Fiction", "Academic"],
    "Beauty": ["Skincare", "Makeup", "Fragrance"],
    "Sports": ["Fitness", "Outdoor", "Cycling"],
    "Toys": ["Action Figures", "Board Games", "Educational"],
    "Grocery": ["Snacks", "Beverages", "Staples"],
}

BRANDS: list[str] = [
    "Samsung", "Apple", "OnePlus", "Xiaomi", "Boat", "Sony", "HP", "Dell",
    "Lenovo", "Nike", "Adidas", "Puma", "Levis", "Allen Solly", "Prestige",
    "Bajaj", "Philips", "Havells", "Mamaearth", "Lakme", "Maybelline",
    "Penguin", "HarperCollins", "Cosco", "Wildcraft", "Local Brand",
]

# city -> (state, tier)
CITY_TIERS: dict[str, tuple[str, str]] = {
    "Mumbai": ("Maharashtra", "Metro"),
    "Delhi": ("Delhi", "Metro"),
    "Bengaluru": ("Karnataka", "Metro"),
    "Chennai": ("Tamil Nadu", "Metro"),
    "Kolkata": ("West Bengal", "Metro"),
    "Hyderabad": ("Telangana", "Metro"),
    "Pune": ("Maharashtra", "Tier1"),
    "Ahmedabad": ("Gujarat", "Tier1"),
    "Jaipur": ("Rajasthan", "Tier1"),
    "Lucknow": ("Uttar Pradesh", "Tier1"),
    "Surat": ("Gujarat", "Tier1"),
    "Indore": ("Madhya Pradesh", "Tier2"),
    "Bhopal": ("Madhya Pradesh", "Tier2"),
    "Nagpur": ("Maharashtra", "Tier2"),
    "Coimbatore": ("Tamil Nadu", "Tier2"),
    "Kochi": ("Kerala", "Tier2"),
    "Guwahati": ("Assam", "Tier2"),
    "Patna": ("Bihar", "Tier2"),
    "Ranchi": ("Jharkhand", "Rural"),
    "Udaipur": ("Rajasthan", "Rural"),
    "Shimla": ("Himachal Pradesh", "Rural"),
}

PAYMENT_METHODS: list[str] = [
    "UPI", "Credit Card", "Debit Card", "Net Banking",
    "Cash on Delivery", "EMI", "Wallet",
]

AGE_GROUPS: list[str] = ["18-25", "26-35", "36-45", "46-55", "55+"]

FESTIVALS: list[str] = [
    "Diwali", "Great Indian Festival", "Prime Day",
    "Republic Day Sale", "Holi", "New Year Sale",
]

# Brand colour palette for consistent visuals.
PALETTE: dict[str, str] = {
    "primary": "#FF9900",   # Amazon orange
    "secondary": "#146EB4",  # Amazon blue
    "dark": "#232F3E",
    "accent": "#37475A",
    "success": "#2E8B57",
    "danger": "#C0392B",
}
SEABORN_PALETTE: str = "viridis"
