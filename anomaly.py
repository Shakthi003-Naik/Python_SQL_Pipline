"""
anomaly.py — Statistical anomaly detection on stock prices.

Two methods run in parallel:

  Z-Score:  Flag close prices more than N standard deviations
            from the rolling 30-day mean. Sensitive to sharp spikes.

  IQR:      Flag prices outside  Q1 - 1.5*IQR  or  Q3 + 1.5*IQR.
            Robust to outliers in the baseline itself.

An anomaly is only raised when BOTH methods agree — reducing false positives.
"""

import os
import logging
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from db import DBSession

load_dotenv()
logger = logging.getLogger(__name__)

ZSCORE_THRESHOLD  = float(os.getenv("ANOMALY_ZSCORE_THRESHOLD", 3.0))
LOOKBACK_DAYS     = int(os.getenv("ANOMALY_LOOKBACK_DAYS", 30))


# ── Helper: fetch baseline data from MySQL ────────────────

def _fetch_baseline(symbol: str, as_of_date: str) -> pd.Series:
    """
    Return the last LOOKBACK_DAYS close prices for a symbol
    BEFORE as_of_date (i.e. the historical window, not today).
    """
    sql = """
        SELECT close_price
        FROM   stock_prices
        WHERE  symbol     = %s
          AND  trade_date < %s
        ORDER  BY trade_date DESC
        LIMIT  %s
    """
    with DBSession() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (symbol, as_of_date, LOOKBACK_DAYS))
        rows = cursor.fetchall()

    if not rows:
        return pd.Series(dtype=float)

    return pd.Series([float(r[0]) for r in rows])


# ── Z-score detection ─────────────────────────────────────

def zscore_flag(value: float, baseline: pd.Series) -> tuple[bool, float | None]:
    """
    Returns (is_anomaly, z_score).
    Needs at least 5 data points for a reliable standard deviation.
    """
    if len(baseline) < 5:
        return False, None

    mean = baseline.mean()
    std  = baseline.std()

    if std == 0:
        return False, 0.0

    z = (value - mean) / std
    return abs(z) > ZSCORE_THRESHOLD, round(z, 4)


# ── IQR detection ─────────────────────────────────────────

def iqr_flag(value: float, baseline: pd.Series) -> bool:
    """
    Returns True if value lies outside 1.5× IQR fence.
    Needs at least 4 data points.
    """
    if len(baseline) < 4:
        return False

    q1  = baseline.quantile(0.25)
    q3  = baseline.quantile(0.75)
    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    return value < lower or value > upper


# ── Main detection function ───────────────────────────────

def detect_anomalies(df: pd.DataFrame) -> list[dict]:
    """
    Run anomaly detection on a transformed DataFrame.

    For each (symbol, trade_date) row, fetch its historical baseline
    from MySQL and apply both Z-score and IQR checks.

    Returns a list of anomaly dicts ready to insert into anomaly_alerts.
    """
    if df.empty:
        return []

    anomalies = []

    for _, row in df.iterrows():
        symbol     = row["symbol"]
        trade_date = row["trade_date"].strftime("%Y-%m-%d")
        close      = float(row["close_price"])

        baseline = _fetch_baseline(symbol, trade_date)

        is_z, z_score = zscore_flag(close, baseline)
        is_iqr        = iqr_flag(close, baseline)

        # Only flag when BOTH methods agree
        if is_z and is_iqr:
            anomaly_type = "BOTH"
        elif is_z:
            anomaly_type = "ZSCORE"
        elif is_iqr:
            anomaly_type = "IQR"
        else:
            continue   # No anomaly — skip

        # Only raise when BOTH agree (most reliable)
        if anomaly_type != "BOTH":
            logger.debug(
                "%s %s: single-method flag (%s) — not raising alert.",
                symbol, trade_date, anomaly_type
            )
            continue

        anomaly = {
            "symbol":        symbol,
            "trade_date":    trade_date,
            "close_price":   close,
            "zscore":        z_score,
            "iqr_flag":      1,
            "anomaly_type":  anomaly_type,
            "baseline_mean": round(float(baseline.mean()), 4) if len(baseline) else None,
            "baseline_std":  round(float(baseline.std()),  4) if len(baseline) > 1 else None,
        }
        anomalies.append(anomaly)

    logger.info("Anomaly detection complete: %d anomalies found.", len(anomalies))
    return anomalies


def save_anomalies(anomalies: list[dict]) -> None:
    """Persist detected anomalies to the anomaly_alerts table."""
    if not anomalies:
        return

    sql = """
        INSERT INTO anomaly_alerts
            (symbol, trade_date, close_price, zscore, iqr_flag,
             anomaly_type, baseline_mean, baseline_std)
        VALUES
            (%(symbol)s, %(trade_date)s, %(close_price)s, %(zscore)s,
             %(iqr_flag)s, %(anomaly_type)s, %(baseline_mean)s, %(baseline_std)s)
    """
    with DBSession() as conn:
        cursor = conn.cursor()
        cursor.executemany(sql, anomalies)

    logger.info("Saved %d anomaly records to anomaly_alerts.", len(anomalies))
