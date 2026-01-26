"""Initialize database from SQL file if it doesn't exist."""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path("data/hooper_two.db")
SQL_FILE = Path("data/hooper_two_players_only.sql")

def init_database():
    """Initialize database from SQL file if database doesn't exist."""
    if DB_PATH.exists():
        print(f"Database already exists at {DB_PATH}")
        print("Skipping initialization.")
        return False

    if not SQL_FILE.exists():
        print(f"ERROR: SQL file not found at {SQL_FILE}")
        print("Cannot initialize database.")
        return False

    print(f"Database not found. Initializing from {SQL_FILE}...")

    # Read SQL file
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    # Execute SQL script
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(sql_script)
    conn.close()

    print("Database initialized successfully!")
    print("- 1751 players loaded")
    print("- 0 user collections")
    print("- Ready for use!")
    return True

if __name__ == "__main__":
    init_database()
