# Data Dictionary

## `transactions` (fact table — cleaned)

| Column | Type | Description |
|---|---|---|
| transaction_id | string | Unique order line identifier (primary key) |
| customer_id | string | Customer identifier |
| product_id | string | Product identifier (FK → products) |
| product_name | string | Product display name |
| category | string | Canonical category (Electronics, Fashion, …) |
| subcategory | string | Sub-category |
| brand | string | Brand name |
| product_rating | float | Catalog rating of the product (1.0–5.0) |
| order_date | date | Standardised order date (YYYY-MM-DD) |
| order_year | int | Derived year |
| order_month | int | Derived month (1–12) |
| order_quarter | int | Derived quarter (1–4) |
| original_price_inr | float | List price in ₹ (currency symbols/commas stripped) |
| discount_percent | float | Discount applied (%) |
| final_amount_inr | float | Amount paid in ₹ |
| delivery_charges | float | Delivery fee in ₹ |
| customer_city | string | Canonical city name |
| customer_state | string | State |
| customer_tier | string | Metro / Tier1 / Tier2 / Rural |
| age_group | string | 18-25, 26-35, 36-45, 46-55, 55+ |
| is_prime_member | bool | Prime membership flag |
| payment_method | category | UPI, Credit Card, Cash on Delivery, … |
| delivery_days | float | Days to deliver (0 = same day) |
| return_status | string | Returned / Not Returned |
| customer_rating | float | Customer's rating (1.0–5.0) |
| is_festival_sale | bool | Whether the order fell in a festival sale |
| festival_name | string | Festival name (nullable) |
| customer_spending_tier | string | Low / Medium / High / Premium |

## `products` (dimension)
`product_id` (PK), `product_name`, `category`, `subcategory`, `brand`, `product_rating`

## `customers` (dimension)
`customer_id` (PK), `customer_city`, `customer_state`, `customer_tier`, `age_group`,
`is_prime_member`, `total_orders`, `total_spend`

## `time_dimension` (dimension)
`order_date` (PK), `year`, `quarter`, `month`, `month_name`, `day_of_week`

---

## Cleaning rules applied (10 challenges)

1. **Dates** — multi-format parse (`DD/MM/YYYY`, `DD-MM-YY`, `YYYY-MM-DD`, …); invalid → dropped.
2. **Prices** — strip `₹`, commas; `Price on Request` → null.
3. **Ratings** — `4 stars`, `3/5`, `2.5/5.0` → float 1.0–5.0; impute by product median.
4. **Cities** — alias map (Bangalore→Bengaluru, Bombay→Mumbai, …) + case/spelling fixes.
5. **Booleans** — Yes/No, 1/0, Y/N, blanks → real `bool`.
6. **Categories** — casing/alias collapse to canonical names.
7. **Delivery days** — `Same Day`→0, `1-2 days`→avg; negatives & >15 dropped, then imputed.
8. **Duplicates** — exact duplicate `transaction_id` removed; genuine bulk orders preserved.
9. **Price outliers** — per-category ~100x decimal errors detected and divided by 100.
10. **Payment methods** — PhonePe/GooglePay→UPI, CC→Credit Card, C.O.D→Cash on Delivery, …
