"""Database connection management with automatic schema initialization."""
import sqlite3
from pathlib import Path
from typing import Optional
from src.database.models import ALL_TABLES, CREATE_INDEXES


class ConnectionManager:
    """Manages SQLite database connection and schema initialization.

    Responsibilities:
    - Create database file and directory if not exists
    - Initialize schema on first connection
    - Enable foreign key constraints
    - Provide thread-safe connection access
    """

    def __init__(self, database_path: str):
        """Initialize connection manager and create schema.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self._connection: Optional[sqlite3.Connection] = None

        # Ensure directory exists
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection and schema
        self._initialize()

    def _initialize(self) -> None:
        """Create database connection and initialize schema."""
        self._connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,  # Allow multi-threaded access
            isolation_level=None  # Autocommit mode
        )

        # Enable foreign key constraints (disabled by default in SQLite)
        self._connection.execute("PRAGMA foreign_keys = ON")

        # Create tables
        cursor = self._connection.cursor()
        for table_sql in ALL_TABLES:
            cursor.execute(table_sql)

        # Create indexes
        for index_sql in CREATE_INDEXES:
            cursor.execute(index_sql)

        self._connection.commit()

    def get_connection(self) -> sqlite3.Connection:
        """Get the database connection.

        Returns:
            SQLite connection object
        """
        if self._connection is None:
            raise RuntimeError("Connection manager not initialized")
        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# Singleton instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager(database_path: Optional[str] = None) -> ConnectionManager:
    """Get or create the singleton ConnectionManager instance.

    Args:
        database_path: Path to database (required on first call)

    Returns:
        ConnectionManager instance
    """
    global _connection_manager

    if _connection_manager is None:
        if database_path is None:
            raise ValueError("database_path required for first initialization")
        _connection_manager = ConnectionManager(database_path)

    return _connection_manager
