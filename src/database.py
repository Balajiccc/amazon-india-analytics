"""
SQL database integration.

Builds a small analytics star-schema in SQLite (zero external setup) using
SQLAlchemy, so the same code can target Postgres/MySQL by swapping the URL.
Loads cleaned transactions plus product / customer / time dimensions and adds
indexes on the columns the dashboard queries most.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

import config
from src.utils import get_logger, timer

logger = get_logger("database")


def get_engine(url: str | None = None) -> Engine:
    """Return a SQLAlchemy engine (SQLite file by default)."""
    url = url or f"sqlite:///{config.DB_PATH}"
    return create_engine(url, future=True)


def _build_dimensions(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Derive product, customer and time dimension tables from transactions."""
    products = (df[["product_id", "product_name", "category", "subcategory",
                    "brand", "product_rating"]]
                .drop_duplicates("product_id").reset_index(drop=True))

    customers = (df.groupby("customer_id")
                 .agg(customer_city=("customer_city", "first"),
                      customer_state=("customer_state", "first"),
                      customer_tier=("customer_tier", "first"),
                      age_group=("age_group", "first"),
                      is_prime_member=("is_prime_member", "max"),
                      total_orders=("transaction_id", "count"),
                      total_spend=("final_amount_inr", "sum"))
                 .reset_index())

    dates = pd.DataFrame({"order_date": df["order_date"].dropna().unique()})
    dates["year"] = dates["order_date"].dt.year
    dates["quarter"] = dates["order_date"].dt.quarter
    dates["month"] = dates["order_date"].dt.month
    dates["month_name"] = dates["order_date"].dt.month_name()
    dates["day_of_week"] = dates["order_date"].dt.day_name()

    return {"products": products, "customers": customers, "time_dimension": dates}


def load_to_db(df: pd.DataFrame, engine: Engine | None = None) -> Engine:
    """Load transactions + dimensions into the database and create indexes."""
    engine = engine or get_engine()
    dims = _build_dimensions(df)

    with timer("DB load", logger):
        df.to_sql("transactions", engine, if_exists="replace",
                  index=False, chunksize=10_000)
        for name, frame in dims.items():
            frame.to_sql(name, engine, if_exists="replace", index=False)
            logger.info("loaded %s (%d rows)", name, len(frame))

    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_txn_year ON transactions(order_year)",
        "CREATE INDEX IF NOT EXISTS ix_txn_cat ON transactions(category)",
        "CREATE INDEX IF NOT EXISTS ix_txn_city ON transactions(customer_city)",
        "CREATE INDEX IF NOT EXISTS ix_txn_cust ON transactions(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_txn_prod ON transactions(product_id)",
    ]
    with engine.begin() as conn:
        for stmt in indexes:
            conn.execute(text(stmt))
    logger.info("indexes created; DB at %s", config.DB_PATH)
    return engine


def query(sql: str, engine: Engine | None = None) -> pd.DataFrame:
    """Run a SQL query and return a DataFrame (used by the dashboard)."""
    engine = engine or get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


# A few ready-made KPI queries the dashboard reuses.
KPI_QUERIES: dict[str, str] = {
    "yearly_revenue": """
        SELECT order_year AS year, SUM(final_amount_inr) AS revenue,
               COUNT(*) AS orders, COUNT(DISTINCT customer_id) AS customers
        FROM transactions GROUP BY order_year ORDER BY order_year
    """,
    "category_revenue": """
        SELECT category, SUM(final_amount_inr) AS revenue, COUNT(*) AS orders
        FROM transactions GROUP BY category ORDER BY revenue DESC
    """,
    "top_cities": """
        SELECT customer_city AS city, SUM(final_amount_inr) AS revenue
        FROM transactions GROUP BY customer_city
        ORDER BY revenue DESC LIMIT 10
    """,
}


if __name__ == "__main__":
    frame = pd.read_parquet(config.PROCESSED_DIR / "transactions_clean.parquet")
    load_to_db(frame)
