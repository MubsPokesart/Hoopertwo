# HooperTwo Commands Reference

Complete reference for all bot commands.

## User Commands

### `/recognize <player_name>`

Catch a spawned player and add them to your collection.

**Parameters:**
- `player_name` (required): Full name of the player (case-insensitive)

**Example:**
```
/recognize LeBron James
```

**Response:**
- ✅ Success: Standard or Phantom edition added with its base rarity tier
- ⚠️ Already owned: You already have that edition; the spawn remains available
- ❌ Wrong player: Name doesn't match active spawn
- ❌ No spawn: No player to recognize

**Cooldown:** 5 seconds per user

---

### `/collection [@user]`

View a player collection with pagination.

**Parameters:**
- `user` (optional): User to view (defaults to yourself)

**Features:**
- Shows total players and points
- Rarity breakdown
- Separate Phantom edition count
- Phantom cards show their edition alongside their base rarity
- Paginated list (9 players per page)
- Navigation buttons: First, Prev, Next, Last

**Example:**
```
/collection
/collection @friend
```

---

### `/leaderboard [period]`

View server leaderboard rankings.

**Parameters:**
- `period` (optional): Time period (weekly/monthly/yearly/alltime, defaults to weekly)

**Features:**
- Top 10 players per page
- Shows rank, points, and player count
- Rolling UTC windows: 7 days (weekly), 30 days (monthly), and 365 days (yearly)
- All-time includes every capture before the latest snapshot refresh
- Period selector dropdown
- Pagination controls

**Example:**
```
/leaderboard
/leaderboard alltime
```

---

### `/rank [@user] [period]`

Check your or another user's rank.

**Parameters:**
- `user` (optional): User to check (defaults to yourself)
- `period` (optional): Time period (defaults to alltime)

**Example:**
```
/rank
/rank @friend weekly
```

---

## Admin Commands

**Required Permission:** Administrator

### `/config`

View current server configuration.

**Shows:**
- Spawn threshold (messages needed)
- Spawn channels (or "all channels")
- Last updated timestamp

---

### `/set-spawn-threshold <threshold>`

Set how many messages trigger a player spawn.

**Parameters:**
- `threshold` (required): Number between 10 and 10,000

**Example:**
```
/set-spawn-threshold 300
```

---

### `/set-spawn-channels <channels>`

Configure which channels can have spawns.

**Parameters:**
- `channels` (required): Space-separated channel mentions

**Example:**
```
/set-spawn-channels #general #spawns #nba
```

**Limit:** Maximum 50 channels

---

### `/clear-spawn-channels`

Remove spawn channel restrictions (allow all channels).

**Example:**
```
/clear-spawn-channels
```

---

### `/backup`

Create a manual database backup.

**Features:**
- Creates timestamped backup
- Verifies integrity automatically
- Shows file size and verification status

**Example:**
```
/backup
```

---

### `/list-backups`

List all available database backups.

**Shows:**
- Up to 10 most recent backups
- Filename, size, and creation date

**Example:**
```
/list-backups
```

---

## Automatic Features

### Player Spawning

- Triggers after X messages (configured by `/set-spawn-threshold`)
- Random player selection weighted by rarity
- Only in configured channels (or all channels if not set)
- Shows player image and rarity

### Daily Leaderboard Snapshots

- Refreshes once when the bot starts
- Runs at midnight UTC
- Creates snapshots using rolling 7/30/365-day UTC windows plus all-time
- Automatic for all servers

### Daily Backups

- Runs at 2 AM UTC
- Creates timestamped backup
- Verifies integrity
- Cleans up backups older than 30 days
- Fully automatic

---

## Rarity Tiers

| Tier | ADP Range | Spawn Weight | Points |
|------|-----------|--------------|--------|
| GOAT | < 2.0 | 1 (rarest) | 1000 |
| Mythic | 2-31.9 | 5 | 500 |
| Legendary | 32-63.9 | 15 | 250 |
| Epic | 64-127.9 | 30 | 100 |
| Rare | 128-255.9 | 50 | 50 |
| Common | 256+ | 100 (common) | 10 |

---

## Support

For issues or questions:
- GitHub Issues: [github.com/yourusername/HooperTwo/issues](https://github.com/yourusername/HooperTwo/issues)
- Discord Support Server: [Your server invite]
