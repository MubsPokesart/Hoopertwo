"""Database schema definitions for SQLite.

All tables use parameterized queries for security.
Foreign keys are enforced.
"""

# SQL statements for table creation
CREATE_PLAYERS_TABLE = """
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    adp_value REAL,
    rarity_tier TEXT NOT NULL CHECK(rarity_tier IN ('GOAT', 'Cosmic', 'Mythic', 'Legendary', 'Epic', 'Rare', 'Uncommon', 'Common')),
    image_url TEXT,
    career_minutes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_USER_COLLECTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS user_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    server_id INTEGER NOT NULL,
    edition TEXT NOT NULL DEFAULT 'Standard' CHECK(edition IN ('Standard', 'Phantom')),
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    UNIQUE(user_id, player_id, server_id, edition)
);
"""

CREATE_SERVER_CONFIGS_TABLE = """
CREATE TABLE IF NOT EXISTS server_configs (
    server_id INTEGER PRIMARY KEY,
    spawn_channels TEXT NOT NULL DEFAULT '[]',
    spawn_threshold INTEGER NOT NULL DEFAULT 500,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_LEADERBOARD_SNAPSHOTS_TABLE = """
CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    server_id INTEGER NOT NULL,
    period TEXT NOT NULL CHECK(period IN ('weekly', 'monthly', 'yearly', 'alltime')),
    points INTEGER NOT NULL DEFAULT 0,
    player_count INTEGER NOT NULL DEFAULT 0,
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, server_id, period, snapshot_date)
);
"""

CREATE_LEADERBOARD_SNAPSHOT_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS leaderboard_snapshot_runs (
    server_id INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    published_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (server_id, snapshot_date)
);
"""

# Indexes for query performance
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_user_collections_user_id ON user_collections(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_user_collections_server_id ON user_collections(server_id);",
    "CREATE INDEX IF NOT EXISTS idx_leaderboard_period ON leaderboard_snapshots(period, server_id);",
    "CREATE INDEX IF NOT EXISTS idx_players_rarity ON players(rarity_tier);",
]

ALL_TABLES = [
    CREATE_PLAYERS_TABLE,
    CREATE_USER_COLLECTIONS_TABLE,
    CREATE_SERVER_CONFIGS_TABLE,
    CREATE_LEADERBOARD_SNAPSHOTS_TABLE,
    CREATE_LEADERBOARD_SNAPSHOT_RUNS_TABLE,
]
