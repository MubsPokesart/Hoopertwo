import pytest
import sqlite3
import tempfile
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
