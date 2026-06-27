"""
load.py — Upsert clean data into MySQL.

Uses INSERT ... ON DUPLICATE KEY UPDATE so re-running the pipeline
never creates duplicates — safe to run multiple times per day.
"""

import logging
import pandas as pd
from db import DBSession

logger = logging.getLogger(__name__)

UPSERT_SQL = """
    INSERT INTO stock_prices
        (symbol, trade_date, open_price, high_price, low_price, close_price, volume)
    VALUES
        (%(symbol)s, %(trade_date)s, %(open_price)s,
         %(high_price)s, %(low_price)s, %(close_price)s, %(volume)s)
    ON DUPLICATE KEY UPDATE
        open_price  = VALUES(open_price),
        high_price  = VALUES(high_price),
        low_price   = VALUES(low_price),
        close_price = VALUES(close_price),
        volume      = VALUES(volume),
        updated_at  = CURRENT_TIMESTAMP
"""


def load(df: pd.DataFrame, batch_size: int = 500) -> int:
    """
    Upsert rows from a clean DataFrame into stock_prices table.

    Args:
        df:         Clean DataFrame from transform.py
        batch_size: Number of rows per commit batch (default 500)

    Returns:
        Total number of rows successfully upserted.
    """
    if df.empty:
        logger.warning("load() received empty DataFrame — nothing to insert.")
        return 0

    # Convert to list of dicts for MySQL driver
    records = []
    for _, row in df.iterrows():
        records.append({
            "symbol":      row["symbol"],
            "trade_date":  row["trade_date"].strftime("%Y-%m-%d"),
            "open_price":  float(row["open_price"]),
            "high_price":  float(row["high_price"]),
            "low_price":   float(row["low_price"]),
            "close_price": float(row["close_price"]),
            "volume":      int(row["volume"]),
        })

    total_loaded = 0

    with DBSession() as conn:
        cursor = conn.cursor()
        # Batch inserts — avoids huge single transactions
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            cursor.executemany(UPSERT_SQL, batch)
            total_loaded += cursor.rowcount
            logger.debug("Batch %d: upserted %d rows.", i // batch_size + 1, cursor.rowcount)

    logger.info("Load complete: %d rows upserted into stock_prices.", total_loaded)
    return total_loaded


def log_pipeline_run(started_at, finished_at, status: str,
                     rows_extracted: int, rows_loaded: int,
                     anomalies_found: int, error_message: str = None) -> None:
    """Write a pipeline run record to the pipeline_runs audit table."""
    sql = """
        INSERT INTO pipeline_runs
            (started_at, finished_at, status, rows_extracted,
             rows_loaded, anomalies_found, error_message)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    with DBSession() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (
            started_at, finished_at, status,
            rows_extracted, rows_loaded, anomalies_found, error_message
        ))
    logger.debug("Pipeline run logged to audit table.")
