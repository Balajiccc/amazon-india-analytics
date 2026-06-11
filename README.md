# 🛒 Amazon India: A Decade of Sales Analytics 📈🇮🇳

End-to-end e-commerce analytics platform over Amazon India's 2015–2025
transactional data: messy raw data → cleaning pipeline → EDA → SQL star schema →
interactive BI dashboard.

## What's inside

```
amazon_india_analytics/
├── config.py                 # paths, constants, palettes
├── run_pipeline.py           # orchestrates the full pipeline
├── requirements.txt
├── src/
│   ├── generate_data.py      # synthetic messy data (matches the spec schema)
│   ├── data_cleaning.py      # 10 cleaning challenges
│   ├── eda.py                # 20 EDA visualizations
│   ├── database.py           # SQLite star-schema load + KPI queries
│   └── utils.py
├── dashboard/
│   └── app.py                # Streamlit dashboard (~28 interactive charts)
├── sql/
│   └── schema.sql            # reference DDL
├── docs/
│   └── data_dictionary.md
└── data/                     # raw/ and processed/ (created at runtime)
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the pipeline

```bash
python run_pipeline.py          # generate → clean → eda → db
```

Individual stages:

```bash
python run_pipeline.py --stages clean eda
python run_pipeline.py --no-generate          # use real CSVs you dropped in data/raw/
```

Outputs:
- `data/processed/transactions_clean.parquet` & `.csv` — production-ready data
- `data/processed/amazon_india.db` — SQLite analytics DB
- `outputs/eda_plots/*.png` — 20 EDA charts
- `outputs/cleaning_report.csv` — before/after audit

## Launch the dashboard

```bash
streamlit run dashboard/app.py
```

Six pages (Executive, Revenue, Customer, Product, Operations, Advanced) with
global year/category/tier filters.

## Using the real dataset

This repo ships a **synthetic generator** because the brief's dataset link
isn't bundled. The generator produces the exact column schema with the same 25%
data-quality defects. To use the real data instead, place the official files in
`data/raw/` using the same names:

```
amazon_india_products_catalog.csv
amazon_india_2015.csv … amazon_india_2025.csv
```

then run `python run_pipeline.py --no-generate`. The cleaning code only depends
on column names, so everything downstream works unchanged.

## Scaling to ~1M rows

Edit `ROWS_PER_YEAR` in `config.py` (e.g. `90_000`) to approach the full
~1M-row target. The default (`9_000`) keeps local runs fast.

## Notes

- SQLite is used for zero-setup portability; swap the URL in
  `src/database.get_engine` for Postgres/MySQL.
- The forecast on the Advanced page is a simple linear trend — replace with
  Prophet/ARIMA for production.
- Code follows PEP 8 with module-level docstrings and type hints.
