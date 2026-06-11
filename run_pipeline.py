"""
End-to-end pipeline orchestrator.

Stages:
    1. generate   -> create synthetic messy raw CSVs (skip if real data present)
    2. clean      -> run the 10-challenge cleaning pipeline, save parquet/CSV
    3. eda        -> render the 20 EDA plots
    4. db         -> load clean data into SQLite star schema

Usage:
    python run_pipeline.py                # run everything
    python run_pipeline.py --stages clean eda
    python run_pipeline.py --no-generate  # use existing raw files
"""
from __future__ import annotations

import argparse
import glob

import pandas as pd

import config
from src import data_cleaning, database, eda, generate_data
from src.utils import get_logger, timer

logger = get_logger("pipeline")


def stage_generate() -> None:
    existing = glob.glob(str(config.RAW_DIR / "amazon_india_2*.csv"))
    if existing:
        logger.info("Found %d raw files; skipping generation.", len(existing))
        return
    generate_data.generate()


def _load_raw() -> pd.DataFrame:
    files = sorted(glob.glob(str(config.RAW_DIR / "amazon_india_2*.csv")))
    if not files:
        raise FileNotFoundError("No raw transaction files. Run the generate stage.")
    frames = [pd.read_csv(f, low_memory=False) for f in files]
    df = pd.concat(frames, ignore_index=True)
    logger.info("Loaded %s raw rows from %d files", f"{len(df):,}", len(files))
    return df


def stage_clean() -> pd.DataFrame:
    df = _load_raw()
    with timer("Cleaning", logger):
        clean, report = data_cleaning.clean_dataframe(df)
    clean.to_parquet(config.PROCESSED_DIR / "transactions_clean.parquet", index=False)
    clean.to_csv(config.PROCESSED_DIR / "transactions_clean.csv", index=False)
    report.to_frame().to_csv(config.OUTPUTS_DIR / "cleaning_report.csv", index=False)
    logger.info("Saved cleaned data (%s rows)", f"{len(clean):,}")
    return clean


def _load_clean() -> pd.DataFrame:
    pq = config.PROCESSED_DIR / "transactions_clean.parquet"
    if not pq.exists():
        return stage_clean()
    return pd.read_parquet(pq)


def stage_eda() -> None:
    eda.run_all_eda(_load_clean())


def stage_db() -> None:
    database.load_to_db(_load_clean())


STAGES = {
    "generate": stage_generate,
    "clean": stage_clean,
    "eda": stage_eda,
    "db": stage_db,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Amazon India analytics pipeline")
    parser.add_argument("--stages", nargs="*", default=list(STAGES),
                        choices=list(STAGES), help="subset of stages to run")
    parser.add_argument("--no-generate", action="store_true",
                        help="skip synthetic data generation")
    args = parser.parse_args()

    stages = [s for s in args.stages if not (args.no_generate and s == "generate")]
    logger.info("Running stages: %s", ", ".join(stages))
    for name in stages:
        logger.info("=== STAGE: %s ===", name)
        STAGES[name]()
    logger.info("Pipeline complete. Launch dashboard with:  "
                "streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
