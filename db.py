"""
db.py — MySQL connection manager
Provides a reusable, context-managed connection pool.
"""

import os
import logging
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Connection pool (reused across pipeline steps) ────────
_pool: pooling.MySQLConnectionPool | None = None


def _get_pool() -> pooling.MySQLConnectionPool:
    """Initialise the connection pool once; return it on subsequent calls."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="pipeline_pool",
            pool_size=5,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            database=os.getenv("DB_NAME", "market_pipeline"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            autocommit=False,
            charset="utf8mb4",
        )
        logger.debug("MySQL connection pool created.")
    return _pool


def get_connection() -> mysql.connector.MySQLConnection:
    """Get a connection from the pool."""
    return _get_pool().get_connection()


class DBSession:
    """
    Context manager — auto-commits on success, rolls back on error.

    Usage:
        with DBSession() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """

    def __enter__(self):
        self.conn = get_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
            logger.error("DB transaction rolled back due to: %s", exc_val)
        else:
            self.conn.commit()
        self.conn.close()
        return False   # don't suppress exceptions
