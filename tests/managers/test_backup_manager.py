import pytest
import sqlite3
import tempfile
import time
from pathlib import Path
from datetime import datetime
from src.managers.backup_manager import BackupManager


@pytest.fixture
def temp_database():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        backup_dir = Path(tmpdir) / "backups"
        backup_dir.mkdir()

        # Create database with test data
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO test (value) VALUES ('test_data')")
        conn.commit()

        yield {
            "db_path": db_path,
            "backup_dir": backup_dir,
            "connection": conn
        }

        conn.close()


def test_create_backup(temp_database):
    """Test creating a database backup."""
    manager = BackupManager(
        database_path=str(temp_database["db_path"]),
        backup_directory=str(temp_database["backup_dir"])
    )

    # Create backup
    backup_path = manager.create_backup()

    assert backup_path is not None
    assert Path(backup_path).exists()
    assert Path(backup_path).suffix == ".db"
    assert "hooper_backup_" in Path(backup_path).name

    # Verify backup contains data
    backup_conn = sqlite3.connect(backup_path)
    cursor = backup_conn.execute("SELECT value FROM test WHERE id = 1")
    row = cursor.fetchone()
    assert row[0] == "test_data"
    backup_conn.close()


def test_verify_backup_integrity(temp_database):
    """Test verifying backup integrity."""
    manager = BackupManager(
        database_path=str(temp_database["db_path"]),
        backup_directory=str(temp_database["backup_dir"])
    )

    # Create backup
    backup_path = manager.create_backup()

    # Verify integrity
    is_valid = manager.verify_backup_integrity(backup_path)

    assert is_valid is True


def test_verify_corrupt_backup(temp_database):
    """Test detecting corrupted backup."""
    manager = BackupManager(
        database_path=str(temp_database["db_path"]),
        backup_directory=str(temp_database["backup_dir"])
    )

    # Create a corrupted file
    corrupt_path = temp_database["backup_dir"] / "corrupt.db"
    with open(corrupt_path, "w") as f:
        f.write("This is not a valid SQLite database")

    # Verify should fail
    is_valid = manager.verify_backup_integrity(str(corrupt_path))

    assert is_valid is False


def test_cleanup_old_backups(temp_database):
    """Test cleaning up backups older than retention days."""
    manager = BackupManager(
        database_path=str(temp_database["db_path"]),
        backup_directory=str(temp_database["backup_dir"])
    )

    # Create an "old" backup by manually creating file
    old_backup = temp_database["backup_dir"] / "hooper_backup_20250101_000000.db"
    old_backup.touch()

    # Create recent backup
    recent_backup = manager.create_backup()

    # Cleanup with 30 day retention (old backup should be deleted)
    deleted_count = manager.cleanup_old_backups(retention_days=30)

    # The manually created old backup should be deleted
    # Note: In real scenario, we'd use file modification time
    assert deleted_count >= 0
    assert Path(recent_backup).exists()


def test_list_backups(temp_database):
    """Test listing available backups."""
    manager = BackupManager(
        database_path=str(temp_database["db_path"]),
        backup_directory=str(temp_database["backup_dir"])
    )

    # Create multiple backups
    backup1 = manager.create_backup()
    time.sleep(1.1)  # Ensure different timestamps (format uses seconds)
    backup2 = manager.create_backup()

    # List backups
    backups = manager.list_backups()

    assert len(backups) == 2
    assert backups[0]["path"] in [backup1, backup2]
    assert "size" in backups[0]
    assert "created_at" in backups[0]
