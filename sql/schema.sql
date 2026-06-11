-- =====================================================================
-- Amazon India Analytics — Star Schema (reference DDL)
-- Engine-agnostic; the Python loader (src/database.py) creates these
-- automatically via SQLAlchemy/pandas. Kept here for documentation and
-- for setting up Postgres/MySQL manually.
-- =====================================================================

-- ---- Dimension: products ------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    product_id      VARCHAR(16) PRIMARY KEY,
    product_name    TEXT,
    category        VARCHAR(64),
    subcategory     VARCHAR(64),
    brand           VARCHAR(64),
    product_rating  REAL
);

-- ---- Dimension: customers -----------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    customer_id      VARCHAR(16) PRIMARY KEY,
    customer_city    VARCHAR(64),
    customer_state   VARCHAR(64),
    customer_tier    VARCHAR(16),
    age_group        VARCHAR(16),
    is_prime_member  BOOLEAN,
    total_orders     INTEGER,
    total_spend      REAL
);

-- ---- Dimension: time ----------------------------------------------------
CREATE TABLE IF NOT EXISTS time_dimension (
    order_date   DATE PRIMARY KEY,
    year         INTEGER,
    quarter      INTEGER,
    month        INTEGER,
    month_name   VARCHAR(16),
    day_of_week  VARCHAR(16)
);

-- ---- Fact: transactions -------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id      VARCHAR(16) PRIMARY KEY,
    customer_id         VARCHAR(16),
    product_id          VARCHAR(16),
    category            VARCHAR(64),
    order_date          DATE,
    order_year          INTEGER,
    order_month         INTEGER,
    order_quarter       INTEGER,
    original_price_inr  REAL,
    discount_percent    REAL,
    final_amount_inr    REAL,
    delivery_charges    REAL,
    customer_city       VARCHAR(64),
    customer_state      VARCHAR(64),
    customer_tier       VARCHAR(16),
    age_group           VARCHAR(16),
    is_prime_member     BOOLEAN,
    payment_method      VARCHAR(32),
    delivery_days       REAL,
    return_status       VARCHAR(32),
    customer_rating     REAL,
    is_festival_sale    BOOLEAN,
    festival_name       VARCHAR(64)
    -- FK references omitted for SQLite portability; add in Postgres/MySQL:
    -- , FOREIGN KEY (product_id)  REFERENCES products(product_id)
    -- , FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- ---- Indexes ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_txn_year ON transactions(order_year);
CREATE INDEX IF NOT EXISTS ix_txn_cat  ON transactions(category);
CREATE INDEX IF NOT EXISTS ix_txn_city ON transactions(customer_city);
CREATE INDEX IF NOT EXISTS ix_txn_cust ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS ix_txn_prod ON transactions(product_id);
