"""
pipeline.py — Main ETL orchestrator.

Runs all four stages in sequence:
  Extract → Transform → Load → Detect Anomalies → Alert

Usage:
  python src/pipeline.py              # scheduled mode
  python src/pipeline.py --run-once   # single run and exit
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Allow imports from src/ when running directly
sys.path.insert(0, os.path.dirname(__file__))

from extract  import fetch_all_symbols
from transform import transform
from load     import load, log_pipeline_run
from anomaly  import detect_anomalies, save_anomalies
from alerts   import dispatch

load_dotenv()

# ── Logging setup ─────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
log_file  = os.getenv("LOG_FILE", "logs/pipeline.log")

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="[%(asctime)s] %(levelname)-8s — %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger("pipeline")

# ── Symbols from .env ─────────────────────────────────────
SYMBOLS = [s.strip() for s in os.getenv("SYMBOLS", "AAPL,MSFT,GOOGL").split(",")]


def run_pipeline() -> dict:
    """
    Execute one full ETL cycle.

    Returns a summary dict with counts and status.
    """
    started_at = datetime.now()
    logger.info("=" * 60)
    logger.info("Pipeline started  |  symbols: %s", ", ".join(SYMBOLS))
    logger.info("=" * 60)

    rows_extracted = 0
    rows_loaded    = 0
    anomalies_found = 0
    status         = "SUCCESS"
    error_message  = None

    try:
        # ── EXTRACT ───────────────────────────────────────
        raw_rows = fetch_all_symbols(SYMBOLS)
        rows_extracted = len(raw_rows)

        # ── TRANSFORM ─────────────────────────────────────
        clean_df = transform(raw_rows)

        # ── LOAD ──────────────────────────────────────────
        rows_loaded = load(clean_df)

        # ── ANOMALY DETECTION ─────────────────────────────
        anomalies = detect_anomalies(clean_df)
        anomalies_found = len(anomalies)

        if anomalies:
            save_anomalies(anomalies)
            dispatch(anomalies)
        else:
            logger.info("No anomalies detected in this run.")

    except Exception as exc:
        status        = "FAILED"
        error_message = str(exc)
        logger.error("Pipeline FAILED: %s", exc, exc_info=True)

    finally:
        finished_at = datetime.now()
        duration    = (finished_at - started_at).total_seconds()

        # ── AUDIT LOG ─────────────────────────────────────
        try:
            log_pipeline_run(
                started_at, finished_at, status,
                rows_extracted, rows_loaded, anomalies_found, error_message
            )
        except Exception as audit_err:
            logger.warning("Could not write audit log: %s", audit_err)

        logger.info("-" * 60)
        logger.info(
            "Pipeline %s  |  extracted=%d  loaded=%d  anomalies=%d  duration=%.1fs",
            status, rows_extracted, rows_loaded, anomalies_found, duration,
        )
        logger.info("=" * 60)

    return {
        "status":          status,
        "rows_extracted":  rows_extracted,
        "rows_loaded":     rows_loaded,
        "anomalies_found": anomalies_found,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Data ETL Pipeline")
    parser.add_argument(
        "--run-once", action="store_true",
        help="Run the pipeline once and exit (skip scheduler)"
    )
    args = parser.parse_args()

    if args.run_once:
        result = run_pipeline()
        sys.exit(0 if result["status"] == "SUCCESS" else 1)
    else:
        # Import here so scheduler isn't required for --run-once
        from scheduler import start_scheduler
        start_scheduler()
