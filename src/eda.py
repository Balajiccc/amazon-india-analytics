"""
Exploratory Data Analysis — 20 visualizations.

Each ``q##_*`` function produces one of the 20 EDA deliverables and saves a PNG
to ``outputs/eda_plots``. ``run_all_eda`` executes the full suite.
"""
from __future__ import annotations

import warnings

import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import config
from src.utils import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("eda")

sns.set_theme(style="whitegrid", palette=config.SEABORN_PALETTE)
plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight",
                     "axes.titleweight": "bold", "font.size": 10})


def _save(fig: plt.Figure, name: str) -> None:
    path = config.EDA_PLOTS_DIR / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    logger.info("saved %s", path.name)


# --------------------------------------------------------------------------- #
def q01_revenue_trend(df: pd.DataFrame) -> None:
    """Yearly revenue with growth-rate annotations."""
    yearly = df.groupby("order_year")["final_amount_inr"].sum() / 1e7
    growth = yearly.pct_change() * 100
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(yearly.index, yearly.values, marker="o", lw=2.5,
            color=config.PALETTE["secondary"])
    ax.fill_between(yearly.index, yearly.values, alpha=0.12,
                    color=config.PALETTE["secondary"])
    for x, y, g in zip(yearly.index, yearly.values, growth.values):
        if not np.isnan(g):
            ax.annotate(f"{g:+.0f}%", (x, y), textcoords="offset points",
                        xytext=(0, 10), ha="center", fontsize=8)
    ax.set(title="Q1 · Revenue Trend 2015-2025 (₹ Crore)",
           xlabel="Year", ylabel="Revenue (₹ Cr)")
    _save(fig, "q01_revenue_trend")


def q02_seasonality(df: pd.DataFrame) -> None:
    """Month x Year revenue heatmap."""
    pivot = df.pivot_table(index="order_month", columns="order_year",
                           values="final_amount_inr", aggfunc="sum") / 1e6
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(pivot, cmap="YlOrRd", annot=False, ax=ax,
                cbar_kws={"label": "Revenue (₹ Million)"})
    ax.set(title="Q2 · Seasonal Sales Heatmap (Month vs Year)",
           xlabel="Year", ylabel="Month")
    _save(fig, "q02_seasonality")


def q03_rfm(df: pd.DataFrame) -> None:
    """RFM customer segmentation scatter."""
    snapshot = df["order_date"].max() + pd.Timedelta(days=1)
    rfm = df.groupby("customer_id").agg(
        recency=("order_date", lambda s: (snapshot - s.max()).days),
        frequency=("transaction_id", "count"),
        monetary=("final_amount_inr", "sum"),
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    sc = ax.scatter(rfm["recency"], rfm["frequency"],
                    c=np.log1p(rfm["monetary"]), s=18, cmap="viridis", alpha=0.6)
    fig.colorbar(sc, label="log(Monetary)")
    ax.set(title="Q3 · RFM Customer Segmentation",
           xlabel="Recency (days)", ylabel="Frequency (orders)")
    _save(fig, "q03_rfm")


def q04_payment_evolution(df: pd.DataFrame) -> None:
    """Payment-method market share as a stacked area chart."""
    share = (df.groupby(["order_year", "payment_method"])["transaction_id"]
             .count().unstack(fill_value=0))
    share = share.div(share.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.stackplot(share.index, share.T.values, labels=share.columns, alpha=0.85)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.set(title="Q4 · Payment Method Evolution (% share)",
           xlabel="Year", ylabel="Share (%)", ylim=(0, 100))
    _save(fig, "q04_payment_evolution")


def q05_category_performance(df: pd.DataFrame) -> None:
    """Category revenue share — bar + pie."""
    rev = df.groupby("category")["final_amount_inr"].sum().sort_values()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6))
    rev.plot.barh(ax=a1, color=config.PALETTE["primary"])
    a1.set(title="Revenue by Category", xlabel="Revenue (₹)")
    a2.pie(rev.values, labels=rev.index, autopct="%1.0f%%", startangle=90,
           colors=sns.color_palette("viridis", len(rev)))
    a2.set_title("Category Share")
    fig.suptitle("Q5 · Category Performance", fontweight="bold")
    _save(fig, "q05_category_performance")


def q06_prime_impact(df: pd.DataFrame) -> None:
    """Prime vs non-Prime AOV and order frequency."""
    aov = df.groupby("is_prime_member")["final_amount_inr"].mean()
    freq = df.groupby("is_prime_member")["transaction_id"].count()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
    aov.plot.bar(ax=a1, color=[config.PALETTE["accent"], config.PALETTE["primary"]])
    a1.set(title="Avg Order Value", ylabel="₹", xticklabels=["Non-Prime", "Prime"])
    freq.plot.bar(ax=a2, color=[config.PALETTE["accent"], config.PALETTE["secondary"]])
    a2.set(title="Order Count", xticklabels=["Non-Prime", "Prime"])
    fig.suptitle("Q6 · Prime Membership Impact", fontweight="bold")
    _save(fig, "q06_prime_impact")


def q07_geography(df: pd.DataFrame) -> None:
    """Revenue by tier and top cities."""
    tier = df.groupby("customer_tier")["final_amount_inr"].sum().sort_values()
    city = df.groupby("customer_city")["final_amount_inr"].sum().nlargest(10)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6))
    tier.plot.bar(ax=a1, color=config.PALETTE["secondary"])
    a1.set(title="Revenue by City Tier", ylabel="₹")
    city.sort_values().plot.barh(ax=a2, color=config.PALETTE["primary"])
    a2.set(title="Top 10 Cities by Revenue", xlabel="₹")
    fig.suptitle("Q7 · Geographic Analysis", fontweight="bold")
    _save(fig, "q07_geography")


def q08_festival_impact(df: pd.DataFrame) -> None:
    """Festival vs non-festival daily revenue."""
    daily = df.groupby(["order_date", "is_festival_sale"])["final_amount_inr"].sum()
    daily = daily.reset_index()
    fig, ax = plt.subplots(figsize=(12, 6))
    for flag, grp in daily.groupby("is_festival_sale"):
        ax.scatter(grp["order_date"], grp["final_amount_inr"], s=6, alpha=0.4,
                   label="Festival" if flag else "Regular")
    ax.legend()
    ax.set(title="Q8 · Festival Sales Impact", xlabel="Date", ylabel="Daily Revenue (₹)")
    _save(fig, "q08_festival_impact")


def q09_age_behavior(df: pd.DataFrame) -> None:
    """Age-group spend and category preference."""
    pivot = df.pivot_table(index="age_group", columns="category",
                           values="final_amount_inr", aggfunc="sum")
    pivot = pivot.div(pivot.sum(axis=1), axis=0)
    fig, ax = plt.subplots(figsize=(12, 6))
    pivot.plot.bar(stacked=True, ax=ax, colormap="viridis")
    ax.legend(bbox_to_anchor=(1.01, 1), fontsize=7)
    ax.set(title="Q9 · Category Preference by Age Group", ylabel="Share of spend")
    _save(fig, "q09_age_behavior")


def q10_price_demand(df: pd.DataFrame) -> None:
    """Price vs demand + correlation matrix."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6))
    sample = df.sample(min(5000, len(df)), random_state=1)
    a1.scatter(sample["final_amount_inr"], sample["discount_percent"],
               s=8, alpha=0.3, color=config.PALETTE["secondary"])
    a1.set(title="Price vs Discount", xlabel="Final Amount (₹)", ylabel="Discount %")
    num = df[["final_amount_inr", "discount_percent", "delivery_days",
              "customer_rating", "product_rating"]].corr()
    sns.heatmap(num, annot=True, cmap="coolwarm", center=0, ax=a2, fmt=".2f")
    a2.set_title("Correlation Matrix")
    fig.suptitle("Q10 · Price vs Demand", fontweight="bold")
    _save(fig, "q10_price_demand")


def q11_delivery_performance(df: pd.DataFrame) -> None:
    """Delivery-days distribution and by-tier performance."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6))
    sns.histplot(df["delivery_days"], bins=16, ax=a1, color=config.PALETTE["primary"])
    a1.set(title="Delivery Days Distribution", xlabel="Days")
    df.groupby("customer_tier")["delivery_days"].mean().plot.bar(
        ax=a2, color=config.PALETTE["secondary"])
    a2.set(title="Avg Delivery Days by Tier", ylabel="Days")
    fig.suptitle("Q11 · Delivery Performance", fontweight="bold")
    _save(fig, "q11_delivery_performance")


def q12_returns(df: pd.DataFrame) -> None:
    """Return rate by category and rating correlation."""
    df = df.copy()
    df["returned"] = (df["return_status"] == "Returned").astype(int)
    rate = df.groupby("category")["returned"].mean() * 100
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6))
    rate.sort_values().plot.barh(ax=a1, color=config.PALETTE["danger"])
    a1.set(title="Return Rate by Category (%)")
    sns.boxplot(data=df, x="return_status", y="customer_rating", ax=a2)
    a2.set(title="Rating vs Return Status")
    fig.suptitle("Q12 · Return Patterns", fontweight="bold")
    _save(fig, "q12_returns")


def q13_brand_performance(df: pd.DataFrame) -> None:
    """Top brands by revenue and share trend."""
    top = df.groupby("brand")["final_amount_inr"].sum().nlargest(10)
    fig, ax = plt.subplots(figsize=(11, 6))
    top.sort_values().plot.barh(ax=ax, color=config.PALETTE["accent"])
    ax.set(title="Q13 · Top 10 Brands by Revenue", xlabel="₹")
    _save(fig, "q13_brand_performance")


def q14_clv_cohort(df: pd.DataFrame) -> None:
    """Acquisition-year cohort retention heatmap."""
    first = df.groupby("customer_id")["order_year"].min().rename("cohort")
    merged = df.join(first, on="customer_id")
    cohort = merged.groupby(["cohort", "order_year"])["customer_id"].nunique().unstack()
    retention = cohort.div(cohort.iloc[:, 0], axis=0)
    fig, ax = plt.subplots(figsize=(11, 7))
    sns.heatmap(retention, annot=True, fmt=".0%", cmap="Greens", ax=ax)
    ax.set(title="Q14 · Cohort Retention by Acquisition Year",
           xlabel="Year", ylabel="Cohort")
    _save(fig, "q14_clv_cohort")


def q15_discount_effectiveness(df: pd.DataFrame) -> None:
    """Discount band vs revenue / volume."""
    df = df.copy()
    df["band"] = pd.cut(df["discount_percent"], [-1, 0, 10, 20, 30, 100],
                        labels=["0%", "1-10%", "11-20%", "21-30%", "30%+"])
    agg = df.groupby("band").agg(revenue=("final_amount_inr", "sum"),
                                 orders=("transaction_id", "count"))
    fig, ax = plt.subplots(figsize=(11, 6))
    agg["revenue"].plot.bar(ax=ax, color=config.PALETTE["primary"], alpha=0.8)
    ax2 = ax.twinx()
    ax2.plot(range(len(agg)), agg["orders"].values, "o-",
             color=config.PALETTE["dark"])
    ax.set(title="Q15 · Discount Effectiveness", ylabel="Revenue (₹)")
    ax2.set_ylabel("Order count")
    _save(fig, "q15_discount_effectiveness")


def q16_rating_sales(df: pd.DataFrame) -> None:
    """Rating distribution and rating-vs-revenue relationship."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6))
    sns.histplot(df["customer_rating"], bins=9, ax=a1, color=config.PALETTE["secondary"])
    a1.set(title="Customer Rating Distribution")
    df.groupby(df["customer_rating"].round())["final_amount_inr"].mean().plot(
        ax=a2, marker="o", color=config.PALETTE["primary"])
    a2.set(title="Avg Order Value by Rating", xlabel="Rating", ylabel="₹")
    fig.suptitle("Q16 · Rating Patterns", fontweight="bold")
    _save(fig, "q16_rating_sales")


def q17_customer_journey(df: pd.DataFrame) -> None:
    """Purchase-frequency distribution (journey depth)."""
    freq = df.groupby("customer_id")["transaction_id"].count()
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.histplot(freq, bins=range(1, 20), ax=ax, color=config.PALETTE["accent"])
    ax.set(title="Q17 · Customer Purchase Frequency",
           xlabel="Orders per customer", ylabel="Customers")
    _save(fig, "q17_customer_journey")


def q18_product_lifecycle(df: pd.DataFrame) -> None:
    """Transactions per category over time (lifecycle)."""
    pivot = df.pivot_table(index="order_year", columns="category",
                           values="transaction_id", aggfunc="count")
    fig, ax = plt.subplots(figsize=(12, 6))
    pivot.plot(ax=ax, marker="o", colormap="tab10")
    ax.legend(bbox_to_anchor=(1.01, 1), fontsize=7)
    ax.set(title="Q18 · Category Lifecycle (order volume)", ylabel="Orders")
    _save(fig, "q18_product_lifecycle")


def q19_competitive_pricing(df: pd.DataFrame) -> None:
    """Price distribution by category (box plots)."""
    fig, ax = plt.subplots(figsize=(13, 6))
    order = df.groupby("category")["final_amount_inr"].median().sort_values().index
    sns.boxplot(data=df, x="category", y="final_amount_inr", order=order,
                ax=ax, showfliers=False)
    ax.set(title="Q19 · Competitive Pricing by Category", ylabel="₹")
    ax.tick_params(axis="x", rotation=30)
    _save(fig, "q19_competitive_pricing")


def q20_business_health(df: pd.DataFrame) -> None:
    """Multi-panel executive health dashboard."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    (df.groupby("order_year")["final_amount_inr"].sum() / 1e7).plot(
        ax=axes[0, 0], marker="o", color=config.PALETTE["secondary"])
    axes[0, 0].set(title="Revenue (₹ Cr)")
    df.groupby("order_year")["customer_id"].nunique().plot(
        ax=axes[0, 1], marker="o", color=config.PALETTE["primary"])
    axes[0, 1].set(title="Active Customers")
    df.groupby("order_year")["final_amount_inr"].mean().plot(
        ax=axes[1, 0], marker="o", color=config.PALETTE["success"])
    axes[1, 0].set(title="Avg Order Value (₹)")
    ((df.assign(r=(df["return_status"] == "Returned"))
        .groupby("order_year")["r"].mean()) * 100).plot(
        ax=axes[1, 1], marker="o", color=config.PALETTE["danger"])
    axes[1, 1].set(title="Return Rate (%)")
    fig.suptitle("Q20 · Business Health Dashboard", fontweight="bold", fontsize=14)
    _save(fig, "q20_business_health")


ALL_PLOTS = [
    q01_revenue_trend, q02_seasonality, q03_rfm, q04_payment_evolution,
    q05_category_performance, q06_prime_impact, q07_geography, q08_festival_impact,
    q09_age_behavior, q10_price_demand, q11_delivery_performance, q12_returns,
    q13_brand_performance, q14_clv_cohort, q15_discount_effectiveness,
    q16_rating_sales, q17_customer_journey, q18_product_lifecycle,
    q19_competitive_pricing, q20_business_health,
]


def run_all_eda(df: pd.DataFrame) -> None:
    """Generate all 20 EDA plots, skipping any that error on the given data."""
    logger.info("Generating %d EDA plots ...", len(ALL_PLOTS))
    for fn in ALL_PLOTS:
        try:
            fn(df)
        except Exception as exc:  # noqa: BLE001 - keep suite resilient
            logger.warning("plot %s failed: %s", fn.__name__, exc)
    logger.info("EDA complete -> %s", config.EDA_PLOTS_DIR)


if __name__ == "__main__":
    frame = pd.read_parquet(config.PROCESSED_DIR / "transactions_clean.parquet")
    run_all_eda(frame)
