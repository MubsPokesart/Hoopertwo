"""Database optimization utilities for production."""
import sqlite3
import logging

logger = logging.getLogger(__name__)


def optimize_database(db_path: str) -> None:
    """Apply production optimizations to SQLite database.

    Enables WAL mode for better concurrent access and sets production-optimal
    PRAGMA settings.

    Args:
        db_path: Path to SQLite database file
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Enable WAL mode for better concurrent access
        cursor.execute("PRAGMA journal_mode=WAL")

        # Production optimizations
        cursor.execute("PRAGMA synchronous=FULL")    # Maximum safety (prevent data loss on crash)
        cursor.execute("PRAGMA cache_size=-64000")   # 64MB cache
        cursor.execute("PRAGMA temp_store=MEMORY")   # Use memory for temp tables

        conn.commit()
        logger.info("✅ Database optimized for production (WAL mode enabled)")

    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
    finally:
        if conn:
            conn.close()
