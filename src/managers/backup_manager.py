"""Manager for database backup operations."""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages database backup operations.

    Responsibilities:
    - Create timestamped backups using SQLite backup API
    - Verify backup integrity
    - Manage backup retention
    - List available backups
    """

    def __init__(self, database_path: str, backup_directory: str):
        """Initialize backup manager.

        Args:
            database_path: Path to main database file
            backup_directory: Directory to store backups
        """
        self.database_path = Path(database_path)
        self.backup_directory = Path(backup_directory)

        # Ensure backup directory exists
        self.backup_directory.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Optional[str]:
        """Create a timestamped backup of the database.

        Uses SQLite's online backup API for safe backups.

        Returns:
            Path to backup file, or None if backup failed
        """
        try:
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"hooper_backup_{timestamp}.db"
            backup_path = self.backup_directory / backup_filename

            # Open source database
            source_conn = sqlite3.connect(str(self.database_path))

            # Create backup connection
            backup_conn = sqlite3.connect(str(backup_path))

            # Perform backup using SQLite backup API
            source_conn.backup(backup_conn)

            # Close connections
            backup_conn.close()
            source_conn.close()

            logger.info(f"Backup created successfully: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return None

    def verify_backup_integrity(self, backup_path: str) -> bool:
        """Verify integrity of a backup file.

        Uses SQLite's PRAGMA integrity_check.

        Args:
            backup_path: Path to backup file

        Returns:
            True if backup is valid, False otherwise
        """
        conn = None
        try:
            # Open backup database
            conn = sqlite3.connect(backup_path)
            cursor = conn.cursor()

            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            # Result should be ("ok",) for valid database
            is_valid = result and result[0] == "ok"

            if is_valid:
                logger.info(f"Backup integrity verified: {backup_path}")
            else:
                logger.warning(f"Backup integrity check failed: {backup_path}")

            return is_valid

        except Exception as e:
            logger.error(f"Integrity verification failed for {backup_path}: {e}")
            return False
        finally:
            if conn:
                conn.close()
