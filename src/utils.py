"""Shared helper utilities used across the pipeline."""
from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from typing import Iterator


def get_logger(name: str) -> logging.Logger:
    """Return a configured module-level logger writing to stdout."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                              datefmt="%H:%M:%S")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


@contextmanager
def timer(label: str, logger: logging.Logger | None = None) -> Iterator[None]:
    """Context manager that logs how long a block of work takes."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    msg = f"{label} finished in {elapsed:.2f}s"
    (logger.info if logger else print)(msg)


def human_int(value: float) -> str:
    """Format a number using Indian-style abbreviations (K / L / Cr)."""
    value = float(value)
    if abs(value) >= 1e7:
        return f"{value / 1e7:.2f} Cr"
    if abs(value) >= 1e5:
        return f"{value / 1e5:.2f} L"
    if abs(value) >= 1e3:
        return f"{value / 1e3:.1f} K"
    return f"{value:.0f}"
