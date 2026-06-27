"""
transform.py — Clean, validate, and normalise raw API rows.

Rules enforced:
  - All price columns must be positive floats
  - Volume must be a non-negative integer
  - trade_date must be a valid date string (YYYY-MM-DD)
  - No duplicate (symbol, trade_date) pairs
  - Prices: open/high/low/close must be internally consistent
             (high >= open, close, low;  low <= open, close, high)
"""

import logging
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


def _parse_date(date_str: str) -> datetime | None:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def transform(raw_rows: list[dict]) -> pd.DataFrame:
    """
    Clean and validate raw rows returned by extract.py.

    Returns a clean pandas DataFrame ready for loading into MySQL.
    Rows that fail validation are dropped and logged.
    """
    if not raw_rows:
        logger.warning("transform() received empty data.")
        return pd.DataFrame()

    df = pd.DataFrame(raw_rows)
    initial_count = len(df)

    # ── 1. Type coercion ──────────────────────────────────
    numeric_cols = ["open_price", "high_price", "low_price", "close_price"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("Int64")

    # ── 2. Date validation ────────────────────────────────
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y-%m-%d", errors="coerce")

    # ── 3. Drop rows with any null in critical columns ────
    critical = ["symbol", "trade_date"] + numeric_cols + ["volume"]
    before = len(df)
    df.dropna(subset=critical, inplace=True)
    dropped_null = before - len(df)
    if dropped_null:
        logger.warning("Dropped %d rows with null values.", dropped_null)

    # ── 4. Business-logic validation ──────────────────────
    # Prices must be positive
    price_valid = (df[numeric_cols] > 0).all(axis=1)
    # Volume must be non-negative
    vol_valid = df["volume"] >= 0
    # High must be the highest price of the four
    consistency = (
        (df["high_price"] >= df["open_price"]) &
        (df["high_price"] >= df["close_price"]) &
        (df["high_price"] >= df["low_price"]) &
        (df["low_price"]  <= df["open_price"]) &
        (df["low_price"]  <= df["close_price"])
    )

    mask = price_valid & vol_valid & consistency
    dropped_logic = (~mask).sum()
    if dropped_logic:
        logger.warning("Dropped %d rows failing business-logic checks.", dropped_logic)
    df = df[mask].copy()

    # ── 5. Remove duplicate (symbol, trade_date) pairs ───
    before = len(df)
    df.drop_duplicates(subset=["symbol", "trade_date"], keep="last", inplace=True)
    dropped_dups = before - len(df)
    if dropped_dups:
        logger.info("Removed %d duplicate rows.", dropped_dups)

    # ── 6. Sort for deterministic load order ──────────────
    df.sort_values(["symbol", "trade_date"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # ── 7. Round prices to 4 decimal places ───────────────
    df[numeric_cols] = df[numeric_cols].round(4)

    final_count = len(df)
    logger.info(
        "Transform complete: %d → %d rows (%d dropped total).",
        initial_count, final_count, initial_count - final_count,
    )
    return df
