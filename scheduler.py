"""
scheduler.py — Run the pipeline on a repeating schedule.

Uses APScheduler (lightweight, no Celery/Redis required).
Interval is configured via .env: SCHEDULE_INTERVAL_MINUTES (default 15).
"""

import os
import logging
import sys
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

load_dotenv()
logger = logging.getLogger(__name__)

INTERVAL = int(os.getenv("SCHEDULE_INTERVAL_MINUTES", 15))


def _job_listener(event) -> None:
    """Log scheduler-level job outcomes."""
    if event.exception:
        logger.error("Scheduled job CRASHED: %s", event.exception)
    else:
        logger.debug("Scheduled job completed successfully.")


def start_scheduler() -> None:
    """Start the blocking scheduler — runs until Ctrl+C."""
    # Import here to avoid circular imports
    from pipeline import run_pipeline

    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # Run immediately on start, then every INTERVAL minutes
    scheduler.add_job(
        run_pipeline,
        trigger="interval",
        minutes=INTERVAL,
        id="etl_pipeline",
        name="Market Data ETL",
        next_run_time=__import__("datetime").datetime.now(),  # run now on start
        max_instances=1,       # never overlap two runs
        coalesce=True,         # skip missed runs if behind
    )

    logger.info("Scheduler started — running every %d minute(s). Press Ctrl+C to stop.", INTERVAL)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user.")
        scheduler.shutdown(wait=False)
        sys.exit(0)


if __name__ == "__main__":
    start_scheduler()
