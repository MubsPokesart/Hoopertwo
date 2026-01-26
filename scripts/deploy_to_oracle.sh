#!/bin/bash
# Deploy HooperTwo to Oracle Cloud with database initialization

set -e  # Exit on error

echo "=== HooperTwo Oracle Cloud Deployment ==="
echo ""

# Check if database exists
if [ -f "data/hooper_two.db" ]; then
    echo "⚠️  Database already exists!"
    read -p "Do you want to reset it? This will DELETE all user collections! (yes/no): " RESET_CONFIRM

    if [ "$RESET_CONFIRM" = "yes" ]; then
        echo "Creating backup..."
        BACKUP_FILE="data/backups/hooper_backup_$(date +%Y%m%d_%H%M%S).db"
        cp data/hooper_two.db "$BACKUP_FILE"
        echo "Backup saved: $BACKUP_FILE"

        echo "Resetting database..."
        rm data/hooper_two.db
        sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql
        echo "Database reset with 1751 players (no collections)"
    else
        echo "Keeping existing database."
    fi
else
    echo "No database found. Initializing from SQL file..."
    sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql
    echo "Database initialized with 1751 players!"
fi

echo ""
echo "Building Docker container..."
docker-compose build

echo ""
echo "Starting bot..."
docker-compose up -d

echo ""
echo "=== Deployment Complete! ==="
echo ""
echo "Check status with: docker-compose ps"
echo "View logs with: docker-compose logs -f"
echo ""
echo "Your bot should be online in Discord shortly!"
