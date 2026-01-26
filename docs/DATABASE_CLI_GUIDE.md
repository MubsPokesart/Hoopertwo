# Database CLI Management Guide

## Overview

This guide covers managing the HooperTwo SQLite database directly via SSH and command line on Oracle Cloud. Use this for quick queries, data inspection, and minor updates.

**Prerequisites:**
- SSH access to Oracle Cloud instance
- Docker installed and bot running
- Basic SQL knowledge

---

## Connecting to the Database

### Option 1: Via Docker Container (Recommended)

```bash
# SSH into Oracle Cloud
ssh ubuntu@<oracle-cloud-ip>

# Access database through Docker container
cd ~/hoopertwo
docker exec -it hooper-two-bot sqlite3 data/hooper_two.db
```

### Option 2: Direct Access (If Not Running)

```bash
# SSH into Oracle Cloud
ssh ubuntu@<oracle-cloud-ip>

# Access database directly
cd ~/hoopertwo
sqlite3 data/hooper_two.db
```

---

## Essential SQLite Commands

Once connected, you'll see the `sqlite>` prompt.

### Navigation & Help

```sql
.help                    -- Show all SQLite commands
.tables                  -- List all tables
.schema TABLE_NAME       -- Show table structure
.databases               -- Show database file path
.quit                    -- Exit SQLite
```

### Display Settings

```sql
.mode column             -- Display results in columns
.headers on              -- Show column headers
.width 10 30 15          -- Set column widths
.mode csv                -- CSV output
.mode json               -- JSON output
```

### Example Session

```bash
sqlite> .tables
players  user_collections  leaderboard_snapshots  server_configs

sqlite> .schema players
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    team TEXT NOT NULL,
    image_url TEXT,
    rarity_tier TEXT NOT NULL,
    adp_rank REAL,
    spawn_weight INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

sqlite> .headers on
sqlite> .mode column
```

---

## Common Queries for HooperTwo

### Inspect Players

```sql
-- View all players
SELECT * FROM players LIMIT 10;

-- Count players by rarity
SELECT rarity_tier, COUNT(*) as total
FROM players
GROUP BY rarity_tier
ORDER BY total DESC;

-- Find specific player
SELECT * FROM players WHERE name LIKE '%LeBron%';

-- View GOAT tier players
SELECT id, name, team, rarity_tier, adp_rank
FROM players
WHERE rarity_tier = 'GOAT'
ORDER BY adp_rank;

-- Check player with specific ID
SELECT * FROM players WHERE id = 123;
```

### Inspect Collections

```sql
-- View user collections
SELECT user_id, player_id, server_id, recognized_at
FROM user_collections
ORDER BY recognized_at DESC
LIMIT 20;

-- Count collections per user
SELECT user_id, COUNT(*) as total_players
FROM user_collections
GROUP BY user_id
ORDER BY total_players DESC;

-- Check specific user's collection
SELECT uc.user_id, p.name, p.team, p.rarity_tier
FROM user_collections uc
JOIN players p ON uc.player_id = p.id
WHERE uc.user_id = 'USER_ID_HERE'
ORDER BY p.rarity_tier;

-- Find who owns a specific player
SELECT user_id, server_id, recognized_at
FROM user_collections
WHERE player_id = 123;
```

### Inspect Server Configs

```sql
-- View all server configurations
SELECT * FROM server_configs;

-- Check spawn settings for specific server
SELECT server_id, spawn_threshold, spawn_channels
FROM server_configs
WHERE server_id = 'SERVER_ID_HERE';

-- Count configured servers
SELECT COUNT(*) FROM server_configs;
```

### Leaderboard Data

```sql
-- View leaderboard snapshots
SELECT * FROM leaderboard_snapshots
ORDER BY snapshot_date DESC
LIMIT 10;

-- Check specific server leaderboard
SELECT * FROM leaderboard_snapshots
WHERE server_id = 'SERVER_ID_HERE'
ORDER BY snapshot_date DESC;
```

---

## Data Modification Examples

**⚠️ ALWAYS BACKUP FIRST:**

```bash
# Before making ANY changes
docker exec hooper-two-bot python scripts/backup_database.py
```

### Safe Update Pattern

```sql
-- 1. Start transaction
BEGIN TRANSACTION;

-- 2. Make changes
UPDATE players SET name = 'Updated Name' WHERE id = 123;

-- 3. Verify changes
SELECT * FROM players WHERE id = 123;

-- 4. If correct, commit; if wrong, rollback
COMMIT;        -- Save changes
-- OR
ROLLBACK;      -- Undo changes
```

### Update Player Information

```sql
-- Fix player name typo
BEGIN TRANSACTION;
UPDATE players SET name = 'LeBron James' WHERE id = 123;
SELECT * FROM players WHERE id = 123;  -- Verify
COMMIT;

-- Update player image URL
BEGIN TRANSACTION;
UPDATE players SET image_url = 'https://new-url.com/image.png' WHERE id = 123;
COMMIT;

-- Change rarity tier (careful!)
BEGIN TRANSACTION;
UPDATE players SET rarity_tier = 'GOAT', spawn_weight = 1 WHERE id = 123;
SELECT * FROM players WHERE id = 123;  -- Verify
COMMIT;
```

### Update Server Configuration

```sql
-- Change spawn threshold
BEGIN TRANSACTION;
UPDATE server_configs
SET spawn_threshold = 100
WHERE server_id = 'SERVER_ID_HERE';
SELECT * FROM server_configs WHERE server_id = 'SERVER_ID_HERE';
COMMIT;

-- Update spawn channels (JSON format)
BEGIN TRANSACTION;
UPDATE server_configs
SET spawn_channels = '["CHANNEL_ID_1", "CHANNEL_ID_2"]'
WHERE server_id = 'SERVER_ID_HERE';
COMMIT;
```

### Remove Data (Dangerous!)

```sql
-- Remove specific collection
BEGIN TRANSACTION;
DELETE FROM user_collections
WHERE user_id = 'USER_ID' AND player_id = 123;
SELECT changes();  -- Shows number of rows deleted
COMMIT;

-- Remove player (will fail if in collections due to foreign key)
BEGIN TRANSACTION;
DELETE FROM players WHERE id = 999;
COMMIT;
```

---

## Bulk Operations

### Export Data

```sql
-- Export all players to CSV
.mode csv
.output players_export.csv
SELECT * FROM players;
.output stdout

-- Export user collections
.mode csv
.output collections_export.csv
SELECT uc.user_id, p.name, p.team, p.rarity_tier, uc.recognized_at
FROM user_collections uc
JOIN players p ON uc.player_id = p.id;
.output stdout

-- Export as JSON
.mode json
.output players.json
SELECT * FROM players LIMIT 100;
.output stdout
```

### Import Data (Advanced)

```sql
-- Import from CSV (create temp table first)
CREATE TEMP TABLE temp_players (
    name TEXT,
    team TEXT,
    rarity_tier TEXT
);

.mode csv
.import /path/to/players.csv temp_players

-- Insert into main table
INSERT INTO players (name, team, rarity_tier, spawn_weight, adp_rank)
SELECT name, team, rarity_tier, 50, 999.0 FROM temp_players;
```

---

## Database Health Checks

### Check Integrity

```sql
-- Verify database integrity
PRAGMA integrity_check;
-- Should return: ok

-- Check foreign key violations
PRAGMA foreign_key_check;
-- Should return nothing if all good
```

### View Database Info

```sql
-- Check journal mode (should be 'wal' in production)
PRAGMA journal_mode;

-- Check synchronous setting (should be '2' = FULL)
PRAGMA synchronous;

-- View database page count and size
PRAGMA page_count;
PRAGMA page_size;

-- List all indexes
SELECT name, tbl_name FROM sqlite_master WHERE type = 'index';

-- Check table row counts
SELECT
    'players' as table_name,
    COUNT(*) as row_count
FROM players
UNION ALL
SELECT 'user_collections', COUNT(*) FROM user_collections
UNION ALL
SELECT 'server_configs', COUNT(*) FROM server_configs
UNION ALL
SELECT 'leaderboard_snapshots', COUNT(*) FROM leaderboard_snapshots;
```

### Performance Analysis

```sql
-- Find largest tables by row count
SELECT name,
       (SELECT COUNT(*) FROM sqlite_master WHERE type = 'table') as table_count
FROM sqlite_master
WHERE type = 'table';

-- Analyze query performance
EXPLAIN QUERY PLAN
SELECT * FROM players WHERE rarity_tier = 'GOAT';

-- Check for missing indexes (advanced)
SELECT name FROM sqlite_master
WHERE type = 'index'
AND tbl_name = 'players';
```

---

## Troubleshooting

### Database Locked Error

```bash
# Check if bot is running and accessing database
docker ps | grep hooper-two-bot

# Option 1: Stop bot temporarily
docker-compose down
sqlite3 data/hooper_two.db
# ... make changes ...
docker-compose up -d

# Option 2: Use read-only mode
sqlite3 file:data/hooper_two.db?mode=ro
```

### WAL Mode Checkpoint

```sql
-- If WAL file is growing large
PRAGMA wal_checkpoint(TRUNCATE);

-- Check WAL status
PRAGMA wal_autocheckpoint;
```

### Foreign Key Issues

```sql
-- Enable foreign keys (required per connection)
PRAGMA foreign_keys = ON;

-- Check foreign key constraints
PRAGMA foreign_key_check;

-- Disable temporarily (not recommended)
PRAGMA foreign_keys = OFF;
```

---

## Safety Best Practices

### Always Backup First

```bash
# Before ANY data modification
docker exec hooper-two-bot python scripts/backup_database.py

# Verify backup created
ls -lh data/backups/
```

### Use Transactions

```sql
-- Wrap all changes in transactions
BEGIN TRANSACTION;
-- ... your changes ...
ROLLBACK;  -- Test changes first
-- Then run again with COMMIT when verified
```

### Test Queries First

```sql
-- Use SELECT before UPDATE/DELETE
SELECT * FROM players WHERE name LIKE '%LeBron%';  -- Check what will be affected
-- UPDATE players SET ... WHERE name LIKE '%LeBron%';  -- Then update
```

### Verify Row Counts

```sql
-- Check how many rows will be affected
SELECT COUNT(*) FROM players WHERE rarity_tier = 'Common';
-- Then delete if count is expected
DELETE FROM players WHERE rarity_tier = 'Common';
```

---

## Quick Reference Commands

### Connection

```bash
# Via Docker
docker exec -it hooper-two-bot sqlite3 data/hooper_two.db

# Direct
sqlite3 data/hooper_two.db
```

### Setup Display

```sql
.mode column
.headers on
.width 5 30 20 15
```

### Common Queries

```sql
-- List tables
.tables

-- Describe table
.schema players

-- Count rows
SELECT COUNT(*) FROM players;

-- Exit
.quit
```

### Safe Update

```sql
BEGIN TRANSACTION;
-- Make changes
SELECT changes();  -- See rows affected
COMMIT;  -- or ROLLBACK;
```

---

## Advanced: One-Liner Commands

Run queries without entering SQLite prompt:

```bash
# Count players
docker exec hooper-two-bot sqlite3 data/hooper_two.db "SELECT COUNT(*) FROM players;"

# Export specific data
docker exec hooper-two-bot sqlite3 -header -csv data/hooper_two.db \
  "SELECT * FROM players WHERE rarity_tier='GOAT';" > goat_players.csv

# Quick integrity check
docker exec hooper-two-bot sqlite3 data/hooper_two.db "PRAGMA integrity_check;"

# Check journal mode
docker exec hooper-two-bot sqlite3 data/hooper_two.db "PRAGMA journal_mode;"
```

---

## Useful Shell Scripts

### Create `db-query.sh` for Quick Access

```bash
#!/bin/bash
# Save as ~/hoopertwo/scripts/db-query.sh

if [ -z "$1" ]; then
    # Interactive mode
    docker exec -it hooper-two-bot sqlite3 data/hooper_two.db
else
    # Execute query and exit
    docker exec hooper-two-bot sqlite3 data/hooper_two.db "$1"
fi
```

**Usage:**

```bash
# Interactive
./scripts/db-query.sh

# Single query
./scripts/db-query.sh "SELECT COUNT(*) FROM players;"
```

---

## When to Use CLI vs GUI

### Use CLI When:
- ✅ Quick data inspection
- ✅ Running single queries
- ✅ Checking database health
- ✅ SSH-only access available
- ✅ Scripting/automation needed

### Use GUI When:
- ✅ Complex multi-table queries
- ✅ Bulk data editing
- ✅ Visual data exploration
- ✅ Schema modifications
- ✅ Exporting large datasets

---

## Emergency Recovery

### Restore from Backup

```bash
# Stop bot
docker-compose down

# List available backups
ls -lh data/backups/

# Restore specific backup
cp data/backups/hoopertwo_backup_20260125_120000.db data/hooper_two.db

# Restart bot
docker-compose up -d

# Verify
docker exec hooper-two-bot sqlite3 data/hooper_two.db "PRAGMA integrity_check;"
```

### Repair Corrupted Database

```bash
# Dump database to SQL
sqlite3 data/hooper_two.db ".dump" > backup.sql

# Create new database from dump
sqlite3 data/hooper_two_new.db < backup.sql

# Replace corrupted database
mv data/hooper_two.db data/hooper_two_corrupted.db
mv data/hooper_two_new.db data/hooper_two.db
```

---

## Related Documentation

- **DEPLOYMENT.md** - Production deployment guide
- **DATABASE_STABILITY.md** - Database stability and WAL mode
- **PRODUCTION_CHECKLIST.md** - Pre-deployment validation
- **scripts/backup_database.py** - Automated backup script
- **scripts/check_db_health.py** - Health monitoring

---

## Support & Resources

**SQLite Documentation:**
- [SQLite Command Line Shell](https://www.sqlite.org/cli.html)
- [SQLite SQL Syntax](https://www.sqlite.org/lang.html)
- [SQLite PRAGMA Statements](https://www.sqlite.org/pragma.html)

**Common Issues:**
- Database locked: Stop bot temporarily
- Permission denied: Check file ownership
- Foreign key errors: Enable `PRAGMA foreign_keys = ON`

**Need Help?**
- Check logs: `docker-compose logs -f`
- Verify bot status: `docker-compose ps`
- Test database: `python scripts/check_db_health.py`

---

## Summary

The CLI is powerful for quick database operations on Oracle Cloud. Key takeaways:

1. **Always backup before modifying data**
2. **Use transactions for all changes**
3. **Test with SELECT before UPDATE/DELETE**
4. **Check affected rows with `changes()`**
5. **Use `.mode column` and `.headers on` for readable output**

For complex operations or bulk edits, consider using a GUI tool instead.
