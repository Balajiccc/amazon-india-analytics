"""
Amazon India — Interactive Business Intelligence Dashboard (Streamlit).

Run with:  streamlit run dashboard/app.py

Six pages map to the brief's dashboard sections (Executive, Revenue, Customer,
Product, Operations, Advanced) and together render ~28 interactive charts, all
driven by the cleaned data loaded into SQLite. Global sidebar filters
(year range, category, city tier) flow through every page.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Make project root importable when launched via `streamlit run`.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from src.database import get_engine, query  # noqa: E402

st.set_page_config(page_title="Amazon India Analytics",
                   page_icon="📦", layout="wide")

PLOTLY_SEQ = px.colors.sequential.Oranges
TEMPLATE = "plotly_white"


# --------------------------------------------------------------------------- #
# Data access
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """Load the full transactions table once, from SQLite or parquet fallback."""
    pq = config.PROCESSED_DIR / "transactions_clean.parquet"
    if config.DB_PATH.exists():
        try:
            return query("SELECT * FROM transactions", get_engine())
        except Exception:  # noqa: BLE001
            pass
    if pq.exists():
        return pd.read_parquet(pq)
    st.error("No data found. Run `python run_pipeline.py` first.")
    st.stop()


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Sidebar filters shared across all pages."""
    st.sidebar.header("🔎 Filters")
    yrs = sorted(df["order_year"].dropna().unique().astype(int))
    y0, y1 = st.sidebar.select_slider("Year range", options=yrs,
                                      value=(yrs[0], yrs[-1]))
    cats = sorted(df["category"].dropna().unique())
    chosen_cats = st.sidebar.multiselect("Categories", cats, default=cats)
    tiers = sorted(df["customer_tier"].dropna().unique())
    chosen_tiers = st.sidebar.multiselect("City tiers", tiers, default=tiers)

    mask = (df["order_year"].between(y0, y1)
            & df["category"].isin(chosen_cats)
            & df["customer_tier"].isin(chosen_tiers))
    return df.loc[mask]


def inr(x: float) -> str:
    if x >= 1e7:
        return f"₹{x/1e7:.2f} Cr"
    if x >= 1e5:
        return f"₹{x/1e5:.2f} L"
    return f"₹{x:,.0f}"


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_executive(df: pd.DataFrame) -> None:
    st.title("📊 Executive Summary")
    c1, c2, c3, c4, c5 = st.columns(5)
    rev = df["final_amount_inr"].sum()
    yearly = df.groupby("order_year")["final_amount_inr"].sum()
    growth = (yearly.pct_change().iloc[-1] * 100) if len(yearly) > 1 else 0
    c1.metric("Total Revenue", inr(rev))
    c2.metric("YoY Growth", f"{growth:+.1f}%")
    c3.metric("Active Customers", f"{df['customer_id'].nunique():,}")
    c4.metric("Avg Order Value", inr(df["final_amount_inr"].mean()))
    c5.metric("Total Orders", f"{len(df):,}")

    # 1 revenue trend
    yr = df.groupby("order_year")["final_amount_inr"].sum().reset_index()
    st.plotly_chart(px.line(yr, x="order_year", y="final_amount_inr", markers=True,
                            title="Revenue Trend", template=TEMPLATE),
                    use_container_width=True)
    a, b = st.columns(2)
    # 2 top categories
    cat = (df.groupby("category")["final_amount_inr"].sum()
           .sort_values(ascending=False).reset_index())
    a.plotly_chart(px.bar(cat, x="final_amount_inr", y="category", orientation="h",
                          title="Top Categories", template=TEMPLATE,
                          color="final_amount_inr", color_continuous_scale="Oranges"),
                   use_container_width=True)
    # 3 orders by year
    oy = df.groupby("order_year")["transaction_id"].count().reset_index()
    b.plotly_chart(px.bar(oy, x="order_year", y="transaction_id",
                          title="Orders by Year", template=TEMPLATE),
                   use_container_width=True)
    # 4 customer growth
    cg = df.groupby("order_year")["customer_id"].nunique().reset_index()
    st.plotly_chart(px.area(cg, x="order_year", y="customer_id",
                            title="Active Customer Growth", template=TEMPLATE),
                    use_container_width=True)


def page_revenue(df: pd.DataFrame) -> None:
    st.title("💰 Revenue Analytics")
    a, b = st.columns(2)
    # 5 quarterly revenue
    q = df.groupby(["order_year", "order_quarter"])["final_amount_inr"].sum().reset_index()
    q["period"] = q["order_year"].astype(str) + "-Q" + q["order_quarter"].astype(str)
    a.plotly_chart(px.line(q, x="period", y="final_amount_inr",
                           title="Quarterly Revenue", template=TEMPLATE),
                   use_container_width=True)
    # 6 monthly seasonality
    m = df.groupby("order_month")["final_amount_inr"].sum().reset_index()
    b.plotly_chart(px.bar(m, x="order_month", y="final_amount_inr",
                          title="Revenue by Month (Seasonality)", template=TEMPLATE),
                   use_container_width=True)
    # 7 category revenue treemap
    cat = df.groupby("category")["final_amount_inr"].sum().reset_index()
    st.plotly_chart(px.treemap(cat, path=["category"], values="final_amount_inr",
                               title="Category Revenue Share", template=TEMPLATE,
                               color="final_amount_inr", color_continuous_scale="Oranges"),
                    use_container_width=True)
    a2, b2 = st.columns(2)
    # 8 festival impact
    fest = df.groupby("is_festival_sale")["final_amount_inr"].mean().reset_index()
    fest["label"] = fest["is_festival_sale"].map({True: "Festival", False: "Regular"})
    a2.plotly_chart(px.bar(fest, x="label", y="final_amount_inr",
                           title="Avg Order Value: Festival vs Regular", template=TEMPLATE),
                    use_container_width=True)
    # 9 discount vs revenue
    df2 = df.copy()
    df2["band"] = pd.cut(df2["discount_percent"], [-1, 0, 10, 20, 30, 100],
                         labels=["0%", "1-10%", "11-20%", "21-30%", "30%+"])
    disc = df2.groupby("band")["final_amount_inr"].sum().reset_index()
    b2.plotly_chart(px.bar(disc, x="band", y="final_amount_inr",
                           title="Revenue by Discount Band", template=TEMPLATE),
                    use_container_width=True)


def page_customer(df: pd.DataFrame) -> None:
    st.title("👥 Customer Analytics")
    # 10 RFM
    snap = pd.to_datetime(df["order_date"]).max() + pd.Timedelta(days=1)
    rfm = df.assign(order_date=pd.to_datetime(df["order_date"])).groupby("customer_id").agg(
        recency=("order_date", lambda s: (snap - s.max()).days),
        frequency=("transaction_id", "count"),
        monetary=("final_amount_inr", "sum")).reset_index()
    st.plotly_chart(px.scatter(rfm, x="recency", y="frequency", color="monetary",
                               title="RFM Segmentation", template=TEMPLATE,
                               color_continuous_scale="Viridis", opacity=0.6),
                    use_container_width=True)
    a, b = st.columns(2)
    # 11 prime vs non-prime
    pm = df.groupby("is_prime_member")["final_amount_inr"].mean().reset_index()
    pm["label"] = pm["is_prime_member"].map({True: "Prime", False: "Non-Prime"})
    a.plotly_chart(px.bar(pm, x="label", y="final_amount_inr",
                          title="AOV: Prime vs Non-Prime", template=TEMPLATE),
                   use_container_width=True)
    # 12 age group spend
    ag = df.groupby("age_group")["final_amount_inr"].sum().reset_index()
    b.plotly_chart(px.pie(ag, names="age_group", values="final_amount_inr",
                          title="Spend by Age Group", template=TEMPLATE, hole=0.4),
                   use_container_width=True)
    a2, b2 = st.columns(2)
    # 13 purchase frequency
    freq = df.groupby("customer_id")["transaction_id"].count().reset_index()
    a2.plotly_chart(px.histogram(freq, x="transaction_id", nbins=20,
                                 title="Purchase Frequency Distribution", template=TEMPLATE),
                    use_container_width=True)
    # 14 spending tier
    if "customer_spending_tier" in df.columns:
        sp = df.groupby("customer_spending_tier")["final_amount_inr"].sum().reset_index()
        b2.plotly_chart(px.bar(sp, x="customer_spending_tier", y="final_amount_inr",
                               title="Revenue by Spending Tier", template=TEMPLATE),
                        use_container_width=True)
    # 15 cohort retention
    first = df.assign(order_date=pd.to_datetime(df["order_date"])) \
              .groupby("customer_id")["order_year"].min().rename("cohort")
    merged = df.join(first, on="customer_id")
    cohort = merged.groupby(["cohort", "order_year"])["customer_id"].nunique().unstack()
    retention = cohort.div(cohort.iloc[:, 0], axis=0)
    st.plotly_chart(px.imshow(retention, text_auto=".0%", aspect="auto",
                              title="Cohort Retention", template=TEMPLATE,
                              color_continuous_scale="Greens"),
                    use_container_width=True)


def page_product(df: pd.DataFrame) -> None:
    st.title("📦 Product & Brand Analytics")
    a, b = st.columns(2)
    # 16 top products
    tp = (df.groupby("product_name")["final_amount_inr"].sum()
          .nlargest(10).reset_index())
    a.plotly_chart(px.bar(tp, x="final_amount_inr", y="product_name", orientation="h",
                          title="Top 10 Products", template=TEMPLATE),
                   use_container_width=True)
    # 17 top brands
    tb = df.groupby("brand")["final_amount_inr"].sum().nlargest(10).reset_index()
    b.plotly_chart(px.bar(tb, x="final_amount_inr", y="brand", orientation="h",
                          title="Top 10 Brands", template=TEMPLATE),
                   use_container_width=True)
    a2, b2 = st.columns(2)
    # 18 rating distribution
    a2.plotly_chart(px.histogram(df, x="customer_rating", nbins=9,
                                 title="Customer Rating Distribution", template=TEMPLATE),
                    use_container_width=True)
    # 19 price by category box
    b2.plotly_chart(px.box(df, x="category", y="final_amount_inr",
                           title="Price Distribution by Category", template=TEMPLATE,
                           points=False),
                    use_container_width=True)
    # 20 category lifecycle
    life = df.pivot_table(index="order_year", columns="category",
                          values="transaction_id", aggfunc="count").reset_index()
    fig = go.Figure()
    for col in [c for c in life.columns if c != "order_year"]:
        fig.add_trace(go.Scatter(x=life["order_year"], y=life[col],
                                 mode="lines+markers", name=col))
    fig.update_layout(title="Category Lifecycle (order volume)", template=TEMPLATE)
    st.plotly_chart(fig, use_container_width=True)


def page_operations(df: pd.DataFrame) -> None:
    st.title("🚚 Operations & Logistics")
    a, b = st.columns(2)
    # 21 delivery distribution
    a.plotly_chart(px.histogram(df, x="delivery_days", nbins=16,
                                title="Delivery Days Distribution", template=TEMPLATE),
                   use_container_width=True)
    # 22 delivery by tier
    dt = df.groupby("customer_tier")["delivery_days"].mean().reset_index()
    b.plotly_chart(px.bar(dt, x="customer_tier", y="delivery_days",
                          title="Avg Delivery Days by Tier", template=TEMPLATE),
                   use_container_width=True)
    a2, b2 = st.columns(2)
    # 23 payment mix
    pay = df.groupby("payment_method")["transaction_id"].count().reset_index()
    a2.plotly_chart(px.pie(pay, names="payment_method", values="transaction_id",
                           title="Payment Method Mix", template=TEMPLATE, hole=0.4),
                    use_container_width=True)
    # 24 payment evolution
    pe = (df.groupby(["order_year", "payment_method"])["transaction_id"].count()
          .reset_index())
    b2.plotly_chart(px.area(pe, x="order_year", y="transaction_id",
                            color="payment_method", title="Payment Evolution",
                            template=TEMPLATE),
                    use_container_width=True)
    # 25 returns by category
    df2 = df.assign(returned=(df["return_status"] == "Returned").astype(int))
    ret = (df2.groupby("category")["returned"].mean() * 100).reset_index()
    st.plotly_chart(px.bar(ret, x="category", y="returned",
                           title="Return Rate by Category (%)", template=TEMPLATE,
                           color="returned", color_continuous_scale="Reds"),
                    use_container_width=True)


def page_advanced(df: pd.DataFrame) -> None:
    st.title("🔮 Advanced Analytics")
    # 26 revenue forecast (simple linear trend)
    yr = df.groupby("order_year")["final_amount_inr"].sum().reset_index()
    if len(yr) >= 3:
        import numpy as np
        coeffs = np.polyfit(yr["order_year"], yr["final_amount_inr"], 1)
        future = list(range(int(yr["order_year"].max()) + 1,
                            int(yr["order_year"].max()) + 4))
        fc = pd.DataFrame({"order_year": future,
                           "final_amount_inr": np.polyval(coeffs, future)})
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=yr["order_year"], y=yr["final_amount_inr"],
                                 mode="lines+markers", name="Actual"))
        fig.add_trace(go.Scatter(x=fc["order_year"], y=fc["final_amount_inr"],
                                 mode="lines+markers", name="Forecast",
                                 line=dict(dash="dash")))
        fig.update_layout(title="Revenue Forecast (linear trend)", template=TEMPLATE)
        st.plotly_chart(fig, use_container_width=True)
    a, b = st.columns(2)
    # 27 correlation heatmap
    num = df[["final_amount_inr", "discount_percent", "delivery_days",
              "customer_rating", "product_rating"]].corr()
    a.plotly_chart(px.imshow(num, text_auto=".2f", title="Correlation Matrix",
                             template=TEMPLATE, color_continuous_scale="RdBu", zmin=-1, zmax=1),
                   use_container_width=True)
    # 28 geographic revenue
    geo = df.groupby("customer_state")["final_amount_inr"].sum().nlargest(12).reset_index()
    b.plotly_chart(px.bar(geo, x="final_amount_inr", y="customer_state", orientation="h",
                          title="Top States by Revenue", template=TEMPLATE),
                   use_container_width=True)
    st.caption("Forecast uses a simple linear trend for illustration — swap in "
               "Prophet/ARIMA for production use.")


PAGES = {
    "📊 Executive Summary": page_executive,
    "💰 Revenue Analytics": page_revenue,
    "👥 Customer Analytics": page_customer,
    "📦 Product & Brand": page_product,
    "🚚 Operations & Logistics": page_operations,
    "🔮 Advanced Analytics": page_advanced,
}


def main() -> None:
    df = load_data()
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    st.sidebar.title("📦 Amazon India BI")
    choice = st.sidebar.radio("Navigate", list(PAGES.keys()))
    filtered = apply_filters(df)
    st.sidebar.caption(f"Rows in view: {len(filtered):,}")
    PAGES[choice](filtered)


if __name__ == "__main__":
    main()
