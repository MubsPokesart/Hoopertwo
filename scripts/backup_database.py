"""Automated database backup with cleanup."""
import sqlite3
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_database():
    """Create timestamped backup of SQLite database."""
    db_path = os.getenv('DATABASE_PATH', 'data/hooper_two.db')
    backup_dir = os.getenv('BACKUP_DIRECTORY', 'data/backups')

    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"hoopertwo_backup_{timestamp}.db")

    try:
        # Use SQLite backup API for consistency
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(backup_path)
        source.backup(dest)
        source.close()
        dest.close()

        logger.info(f"✅ Database backed up to {backup_path}")

        # Cleanup old backups (keep last 7)
        cleanup_old_backups(backup_dir, keep=7)

    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        raise


def cleanup_old_backups(backup_dir: str, keep: int = 7):
    """Remove old backups, keeping only the most recent."""
    backups = sorted([
        os.path.join(backup_dir, f)
        for f in os.listdir(backup_dir)
        if f.startswith("hoopertwo_backup_") and f.endswith(".db")
    ])

    for old_backup in backups[:-keep]:
        os.remove(old_backup)
        logger.info(f"🗑️  Removed old backup: {os.path.basename(old_backup)}")


if __name__ == "__main__":
    backup_database()
