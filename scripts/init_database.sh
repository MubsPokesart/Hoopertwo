#!/bin/bash
# Initialize database from SQL file if database doesn't exist

DB_PATH="data/hooper_two.db"
SQL_FILE="data/hooper_two_players_only.sql"

if [ ! -f "$DB_PATH" ]; then
    echo "Database not found. Initializing from SQL file..."
    sqlite3 "$DB_PATH" < "$SQL_FILE"
    echo "Database initialized with 1751 players!"
else
    echo "Database already exists. Skipping initialization."
fi
