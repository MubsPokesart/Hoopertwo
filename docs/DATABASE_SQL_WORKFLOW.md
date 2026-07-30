# Database SQL File Workflow

This guide explains how to use `data/hooper_two_players_only.sql` for database management in your Oracle Cloud deployment.

## What is the SQL File?

**File:** `data/hooper_two_players_only.sql` (445 KB)

This file contains:
- ✅ Complete database schema (all tables, indexes, constraints)
- ✅ All 1,751 NBA players with full data (name, rarity, ADP, images)
- ❌ No user collections
- ❌ No server configurations
- ❌ No leaderboard data

## Common Use Cases

### 1. Fresh Deployment to Oracle Cloud

When deploying HooperTwo to a new server:

```bash
# On Oracle Cloud server
cd ~/Hoopertwo
git pull

# Initialize database from SQL file
python3 scripts/init_database.py

# Or use automated script
chmod +x scripts/deploy_to_oracle.sh
./scripts/deploy_to_oracle.sh

# Start bot
docker-compose up -d
```

### 2. Reset Database (Testing/Development)

Wipe all user collections but keep player data:

```bash
# Backup current database first!
docker exec hooper-two-bot python scripts/backup_database.py

# Stop bot
docker-compose down

# Reset database
sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql

# Restart bot
docker-compose up -d
```

### 3. Update Player Rarities for Production

When you change player rarities (like Fred VanVleet → Rare):

**On Local Machine:**
```bash
# Update rarities in your local database
poetry run python update_rarities.py

# Regenerate SQL file with updated rarities
poetry run python scripts/export_db_to_sql.py

# Commit and push
git add data/hooper_two_players_only.sql
git commit -m "Update Fred VanVleet to Rare, DeAndre Ayton to Uncommon"
git push origin main
```

**On Oracle Server:**
```bash
cd ~/Hoopertwo

# Pull latest changes (includes updated SQL file)
git pull

# Option A: Keep existing collections (rarities update on next spawn)
docker-compose restart

# Option B: Apply rarity changes immediately (wipes collections)
docker exec hooper-two-bot python scripts/backup_database.py
docker-compose down
sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql
docker-compose up -d
```

### 4. Disaster Recovery

If your database gets corrupted:

```bash
# Stop bot
docker-compose down

# Remove corrupted database
rm data/hooper_two.db

# Restore from SQL file (players only)
sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql

# Optional: Restore collections from backup
# sqlite3 data/hooper_two.db "ATTACH 'data/backups/hoopertwo_backup_YYYYMMDD.db' AS backup; INSERT INTO user_collections SELECT * FROM backup.user_collections;"

# Restart bot
docker-compose up -d
```

### 5. Migration to New Server

Moving to a different Oracle Cloud instance:

```bash
# On new server
cd ~
git clone https://github.com/yourusername/hoopertwo.git
cd hoopertwo

# Setup environment
cp .env.example .env
nano .env  # Add Discord token

# Initialize database
sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql

# Build and start
docker-compose up -d
```

## Workflow Scripts

### Generate Updated SQL File

After making any player data changes:

```bash
poetry run python scripts/export_db_to_sql.py
```

This creates/updates `data/hooper_two_players_only.sql` with current player data.

### Initialize Database from SQL

If database doesn't exist:

```bash
poetry run python scripts/init_database.py
```

Safe to run - won't overwrite existing database.

### Automated Deployment

Includes database initialization:

```bash
chmod +x scripts/deploy_to_oracle.sh
./scripts/deploy_to_oracle.sh
```

## File Integration with Docker

The SQL file is automatically included in Docker builds:

**Dockerfile (lines 31):**
```dockerfile
COPY data/hooper_two_players_only.sql ./data/
```

This means:
- ✅ SQL file is always available inside containers
- ✅ Can initialize database without external files
- ✅ Deployments are self-contained

## Best Practices

### When to Regenerate SQL File

Regenerate after:
- ✅ Adding new players
- ✅ Updating player rarities
- ✅ Fixing player data (names, images, ADP values)
- ✅ Any changes to player table structure

Don't regenerate for:
- ❌ User collection changes
- ❌ Leaderboard updates
- ❌ Server configuration changes
- ❌ Testing/development work

### Version Control

**Always commit the SQL file when:**
1. You update player rarities
2. You add new players to the database
3. You fix player data errors

```bash
git add data/hooper_two_players_only.sql
git commit -m "Update player rarities: VanVleet (Rare), Ayton (Uncommon)"
git push
```

### Production Safety

**Before resetting database in production:**
1. ✅ Always backup first: `docker exec hooper-two-bot python scripts/backup_database.py`
2. ✅ Announce downtime to users
3. ✅ Stop the bot: `docker-compose down`
4. ✅ Verify backup exists: `ls -lh data/backups/`
5. ✅ Then reset: `sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql`

## Quick Reference

| Task | Command |
|------|---------|
| Generate SQL file | `poetry run python scripts/export_db_to_sql.py` |
| Initialize new DB | `sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql` |
| Check if DB exists | `ls -lh data/hooper_two.db` |
| Reset to fresh players | `sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql` |
| Deploy with init | `./scripts/deploy_to_oracle.sh` |

## Related Files

- **SQL File:** `data/hooper_two_players_only.sql` (445 KB, 1751 players)
- **Generator:** `scripts/export_db_to_sql.py`
- **Initializer:** `scripts/init_database.py`
- **Deployment:** `scripts/deploy_to_oracle.sh`
- **Main Docs:** `docs/DEPLOYMENT.md`

## Troubleshooting

**Error: "database is locked"**
```bash
docker-compose down  # Stop bot first
sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql
docker-compose up -d
```

**Error: "SQL file not found"**
```bash
git pull  # Make sure you have latest code
ls -lh data/hooper_two_players_only.sql  # Verify file exists
```

**Want to keep some collections?**
```bash
# Export collections before reset
sqlite3 data/hooper_two.db ".dump user_collections" > collections_backup.sql

# Reset database
sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql

# Restore specific user's collection
sqlite3 data/hooper_two.db < collections_backup.sql
```

---

**Summary:** The SQL file is your single source of truth for player data. Use it for fresh deployments, database resets, and disaster recovery. Always commit it when player data changes.
