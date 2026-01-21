# HooperTwo Deployment Guide

## Docker Deployment (Recommended)

### Prerequisites

- Docker and Docker Compose installed
- Discord bot token

### Steps

1. **Clone and Configure**

```bash
git clone https://github.com/yourusername/HooperTwo.git
cd HooperTwo
cp .env.example .env
```

2. **Edit .env**

Add your Discord bot token:
```
DISCORD_TOKEN=your_token_here
```

3. **Start Bot**

```bash
docker compose up -d
```

4. **View Logs**

```bash
docker compose logs -f
```

5. **Stop Bot**

```bash
docker compose down
```

### Persistent Data

- Database: `./data/hooper.db` (mounted as volume)
- Backups: `./backups/` (mounted as volume)

### Updates

```bash
git pull
docker compose down
docker compose build
docker compose up -d
```

## Manual Deployment

### Prerequisites

- Python 3.10+
- Poetry

### Steps

1. **Install Dependencies**

```bash
poetry install
```

2. **Configure Environment**

```bash
cp .env.example .env
# Edit .env with your token
```

3. **Run Bot**

```bash
poetry run python bot.py
```

### Production Setup (systemd)

Create `/etc/systemd/system/hooper.service`:

```ini
[Unit]
Description=HooperTwo Discord Bot
After=network.target

[Service]
Type=simple
User=hooper
WorkingDirectory=/opt/HooperTwo
Environment="PATH=/opt/HooperTwo/.venv/bin"
ExecStart=/opt/HooperTwo/.venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable hooper
sudo systemctl start hooper
sudo systemctl status hooper
```

## Monitoring

### Health Checks

- Monitor logs for errors
- Check backup creation (daily at 2 AM UTC)
- Verify snapshot creation (daily at midnight UTC)

### Backup Verification

```bash
# List backups
ls -lh backups/

# Test backup integrity
sqlite3 backups/hooper_backup_TIMESTAMP.db "PRAGMA integrity_check;"
```

## Troubleshooting

### Bot Won't Connect

- Verify Discord token is correct
- Check intents are enabled in Discord Developer Portal
- Ensure bot has proper permissions

### Commands Not Appearing

- Commands sync to guild instantly, global sync takes 1 hour
- Re-invite bot with `applications.commands` scope
- Check logs for sync errors

### Database Issues

- Check `data/hooper.db` exists and has correct permissions
- Verify SQLite version >= 3.35.0
- Check disk space

## Security

- **Never commit `.env`** - token should stay private
- Use environment variables for sensitive data
- Regularly update dependencies
- Monitor backup sizes and clean old backups
