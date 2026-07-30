# HooperTwo Production Deployment Guide

## What Was Implemented

All production hosting changes have been successfully implemented:

### Modified Files
1. **bot.py**
   - Added `COMMAND_SYNC_MODE` environment variable support (lines 144-162)
   - Added production database optimization call before bot start (lines 213-215)
   - Added `import os` for environment variable access

2. **.env.example**
   - Added `COMMAND_SYNC_MODE=guild` (development default)
   - Added `ENVIRONMENT=development` (production indicator)

3. **docker-compose.yml**
   - Added health check for database connectivity (lines 22-27)

### New Files Created
1. **src/utils/db_optimizer.py**
   - Enables WAL mode for better concurrent access
   - Sets production-optimal PRAGMA settings (64MB cache, memory temp store)

2. **scripts/backup_database.py**
   - Creates timestamped database backups
   - Automatically cleans up old backups (keeps last 7)
   - Tested and working ✅

3. **.github/workflows/deploy.yml**
   - CI/CD workflow for automated deployment to Oracle Cloud
   - Triggers on push to main or manual dispatch

---

## Quick Start: Deploy to Production

### Step 1: Oracle Cloud Setup

1. Create account at [cloud.oracle.com](https://cloud.oracle.com)
2. Create Compute Instance:
   - Name: `hoopertwo-bot`
   - Image: Ubuntu 22.04
   - Shape: VM.Standard.A1.Flex (2 OCPUs, 12GB RAM)
   - Add your SSH public key

### Step 2: Server Setup

SSH into your instance and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose git -y

# Logout and login again
exit
```

### Step 3: Deploy Application

```bash
# Clone repository
cd ~
git clone https://github.com/yourusername/hoopertwo.git
cd hoopertwo

# Configure environment
cp .env.example .env
nano .env
```

**Edit .env file:**
```bash
DISCORD_TOKEN=your_actual_bot_token_here
COMMAND_SYNC_MODE=global
ENVIRONMENT=production
DATABASE_PATH=/app/data/hooper_two.db
BACKUP_DIRECTORY=/app/data/backups
```

**Initialize Database (Optional):**

If you want to start fresh with all players but no user collections:

```bash
# Initialize database from SQL file
python3 scripts/init_database.py

# OR use the automated deployment script
chmod +x scripts/deploy_to_oracle.sh
./scripts/deploy_to_oracle.sh
```

**Deploy:**
```bash
docker-compose up -d
docker-compose logs -f
```

### Step 4: Setup Automated Backups

```bash
# Test manual backup
docker exec hooper-two-bot python scripts/backup_database.py

# Setup cron for daily backups at 3 AM
crontab -e
# Add this line:
0 3 * * * docker exec hooper-two-bot python scripts/backup_database.py

# Optional: Weekly restart (Monday 4 AM)
0 4 * * 1 cd ~/Hoopertwo && docker-compose restart
```

---

## Environment Variables

### Development Mode (Current)
```bash
COMMAND_SYNC_MODE=guild      # Instant command sync to first guild
ENVIRONMENT=development      # Skips database optimizations
```

### Production Mode
```bash
COMMAND_SYNC_MODE=global     # Syncs commands to all servers (~1 hour)
ENVIRONMENT=production       # Enables WAL mode and optimizations
```

---

## Maintenance Commands

### View Logs
```bash
docker-compose logs -f                # Live logs
docker-compose logs --tail=100        # Recent logs
```

### Update Bot
```bash
cd ~/Hoopertwo
git pull --ff-only origin main
bash scripts/deploy_with_migration.sh
```

The deployment script builds first, stops the bot, and then runs the database
`preflight`, `apply`, and `verify` gates in one-off containers. It restarts the bot
only after all three commands succeed. `apply` creates a verified SQLite backup and
JSON manifest before changing schema or data.

### Phantom/Cosmic Database Migration

Run these commands only while the bot service is stopped. The migration refuses
unknown or partially upgraded schemas and requires an explicit offline confirmation.

```bash
cd ~/Hoopertwo
docker-compose build hooper-two
docker-compose stop hooper-two
docker-compose run --rm --no-deps hooper-two \
  python scripts/migrate_database.py preflight
docker-compose run --rm --no-deps hooper-two \
  python scripts/migrate_database.py apply --confirm-offline
docker-compose run --rm --no-deps hooper-two \
  python scripts/migrate_database.py verify
docker-compose up -d hooper-two
```

Do not restart after a failed migration or verification. The `apply` output records
the exact backup and manifest paths needed for rollback:

```bash
docker-compose run --rm --no-deps hooper-two \
  python scripts/migrate_database.py rollback \
  --backup /app/data/backups/<backup>.db \
  --manifest /app/data/backups/<backup>.manifest.json \
  --confirm-offline
```

Rollback validates the manifest and backup hash, creates a safety backup of the
current database, atomically restores the legacy database, and leaves the bot stopped.

### Check Health
```bash
docker-compose ps              # Container status
docker stats hooper-two-bot    # Resource usage
docker inspect hooper-two-bot | grep -A 5 Health  # Health check status
```

### Restore from Backup
```bash
docker-compose stop hooper-two
# Use migrate_database.py rollback with the matching migration manifest.
```

### Reset Database (Keep Players, Wipe Collections)
```bash
# Backup first!
docker exec hooper-two-bot python scripts/backup_database.py

# Stop bot
docker-compose down

# Reset to fresh player data (removes all user collections)
sqlite3 data/hooper_two.db < data/hooper_two_players_only.sql

# Restart
docker-compose up -d
```

### Update Player Rarities
```bash
# Make rarity changes in local database
# Then regenerate the SQL file
poetry run python -c "from export_db_to_sql import export_database; export_database()"

# Commit the updated SQL file
git add data/hooper_two_players_only.sql
git commit -m "Update player rarities"
git push

# Pull on Oracle server
cd ~/Hoopertwo
git pull
# Optionally reset database if you want to apply rarity changes
```

---

## CI/CD Setup (Optional)

To enable automated deployments via GitHub Actions:

1. Go to your GitHub repository settings
2. Navigate to Secrets and variables > Actions
3. Add these secrets:
   - `ORACLE_HOST`: Your Oracle Cloud instance IP
   - `ORACLE_SSH_KEY`: Your private SSH key

Now every push to `main` will automatically deploy to production!

---

## Production Checklist

After deployment, verify:

- [ ] Bot is online in Discord
- [ ] Commands sync globally (wait ~1 hour after first deployment)
- [ ] `/recognize` works across all servers
- [ ] `/collection` shows user collections
- [ ] `/leaderboard` displays rankings
- [ ] Admin commands work (server config)
- [ ] Spawning triggers correctly
- [ ] Database backups running (check `data/backups/`)
- [ ] Health checks passing (`docker inspect hooper-two-bot`)
- [ ] Logs rotating properly

---

## Scaling Capacity

**Current Usage:**
- 75k messages/month (2,500/day)
- 300 active users
- ~50MB database
- ~200MB memory usage

**Oracle Free Tier Can Handle:**
- 120x memory headroom (24GB available)
- 199x storage headroom (200GB available)
- Estimated capacity: 30,000+ concurrent users

---

## Support Resources

**Discord.py Docs:**
- [Command Sync API](https://discordpy.readthedocs.io/en/stable/interactions/api)

**Hosting Guides:**
- [Oracle Cloud Free Tier Setup](https://www.oracle.com/cloud/free/)
- [Host Discord Bot on Oracle Cloud](https://www.linkedin.com/pulse/host-your-discord-bot-free-oci-bilegt-bat-ochir)

**Troubleshooting:**
```bash
# Check environment variables
docker exec hooper-two-bot env | grep COMMAND_SYNC_MODE

# Test database connection
docker exec hooper-two-bot python -c "import sqlite3; print(sqlite3.connect('data/hooper_two.db').execute('SELECT COUNT(*) FROM players').fetchone())"

# View full logs
docker-compose logs --tail=500 > debug.log
```

---

## Next Steps

1. **Test Locally** - Set `ENVIRONMENT=production` in `.env` and run `docker-compose up` to test WAL mode
2. **Create Oracle Account** - Sign up for free tier
3. **Deploy** - Follow Step 1-4 above
4. **Monitor** - Check logs and health for 48 hours
5. **Optimize** - Adjust spawn thresholds per server as needed

---

## Files Changed Summary

**Modified:**
- `bot.py` (command sync mode + db optimizer)
- `.env.example` (production config variables)
- `docker-compose.yml` (health check)

**Created:**
- `src/utils/db_optimizer.py` (WAL mode + optimizations)
- `scripts/backup_database.py` (automated backups)
- `.github/workflows/deploy.yml` (CI/CD)
- `DEPLOYMENT.md` (this file)

**Architecture Notes:**
- ✅ Database already multi-server ready (server_id scoping)
- ✅ Code already handles multiple guilds
- ✅ Docker setup production-ready
- ✅ No major refactoring needed

Good luck with your deployment! 🚀
