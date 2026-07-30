#!/usr/bin/env bash
set -euo pipefail

if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
else
    echo "Docker Compose is required." >&2
    exit 1
fi

SERVICE="hooper-two"

echo "Building the new application image while the current bot remains online..."
"${COMPOSE[@]}" build "$SERVICE"

echo "Checking the production database schema and integrity..."
"${COMPOSE[@]}" run --rm --no-deps "$SERVICE" \
    python scripts/migrate_database.py preflight

echo "Stopping the bot before acquiring the SQLite migration lock..."
"${COMPOSE[@]}" stop "$SERVICE"

echo "Applying the backup-first migration..."
"${COMPOSE[@]}" run --rm --no-deps "$SERVICE" \
    python scripts/migrate_database.py apply \
    --confirm-offline \
    --result-file /app/data/backups/latest-migration-result.json

echo "Verifying the migrated database before restart..."
"${COMPOSE[@]}" run --rm --no-deps "$SERVICE" \
    python scripts/migrate_database.py verify \
    --apply-result /app/data/backups/latest-migration-result.json

echo "Starting the bot..."
"${COMPOSE[@]}" up -d "$SERVICE"
CONTAINER_ID=$("${COMPOSE[@]}" ps -q "$SERVICE")
for _ in {1..40}; do
    STATE=$(docker inspect --format \
        '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
        "$CONTAINER_ID")
    if [[ "$STATE" == "running healthy" ]]; then
        "${COMPOSE[@]}" ps "$SERVICE"
        exit 0
    fi
    sleep 3
done

echo "Bot failed to become healthy after deployment." >&2
"${COMPOSE[@]}" ps "$SERVICE" >&2
"${COMPOSE[@]}" logs --tail=100 "$SERVICE" >&2
exit 1
