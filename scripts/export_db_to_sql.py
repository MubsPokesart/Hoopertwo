"""Export HooperTwo database to SQL file with players only (no collections)."""
import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path("data/hooper_two.db")
OUTPUT_PATH = Path("data/hooper_two_players_only.sql")


def export_database():
    """Export database schema and player data to SQL file."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        # Write header
        f.write("-- HooperTwo Database Reconstruction\n")
        f.write("-- Contains all players but no user collections\n")
        f.write("-- Generated automatically\n\n")

        # Enable foreign keys
        f.write("PRAGMA foreign_keys = ON;\n\n")
        f.write("PRAGMA user_version = 1;\n\n")

        # Create players table
        f.write("-- Create players table\n")
        f.write(
            """CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    adp_value REAL,
    rarity_tier TEXT NOT NULL CHECK(rarity_tier IN ('GOAT', 'Cosmic', 'Mythic', 'Legendary', 'Epic', 'Rare', 'Uncommon', 'Common')),
    image_url TEXT,
    career_minutes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

"""
        )

        # Create user_collections table (empty)
        f.write("-- Create user_collections table (will be empty)\n")
        f.write(
            """CREATE TABLE IF NOT EXISTS user_collections (
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
        )

        # Create server_configs table (empty)
        f.write("-- Create server_configs table (will be empty)\n")
        f.write(
            """CREATE TABLE IF NOT EXISTS server_configs (
    server_id INTEGER PRIMARY KEY,
    spawn_channels TEXT NOT NULL DEFAULT '[]',
    spawn_threshold INTEGER NOT NULL DEFAULT 500,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

"""
        )

        # Create leaderboard_snapshots table (empty)
        f.write("-- Create leaderboard_snapshots table (will be empty)\n")
        f.write(
            """CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
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
        )

        f.write("-- Create leaderboard_snapshot_runs table (will be empty)\n")
        f.write(
            """CREATE TABLE IF NOT EXISTS leaderboard_snapshot_runs (
    server_id INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    published_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (server_id, snapshot_date)
);

"""
        )

        # Create indexes
        f.write("-- Create indexes\n")
        f.write(
            "CREATE INDEX IF NOT EXISTS idx_user_collections_user_id ON user_collections(user_id);\n"
        )
        f.write(
            "CREATE INDEX IF NOT EXISTS idx_user_collections_server_id ON user_collections(server_id);\n"
        )
        f.write(
            "CREATE INDEX IF NOT EXISTS idx_leaderboard_period ON leaderboard_snapshots(period, server_id);\n"
        )
        f.write("CREATE INDEX IF NOT EXISTS idx_players_rarity ON players(rarity_tier);\n\n")

        # Export player data
        f.write("-- Insert player data\n")
        f.write("BEGIN TRANSACTION;\n\n")

        cursor.execute(
            "SELECT id, name, adp_value, rarity_tier, image_url, career_minutes, created_at FROM players ORDER BY id"
        )
        players = cursor.fetchall()

        for player in players:
            player_id, name, adp_value, rarity_tier, image_url, career_minutes, created_at = player

            # Escape single quotes in strings
            name_escaped = name.replace("'", "''") if name else ""
            image_url_escaped = image_url.replace("'", "''") if image_url else None

            # Build INSERT statement with proper NULL handling
            image_val = f"'{image_url_escaped}'" if image_url_escaped else "NULL"
            minutes_val = str(career_minutes) if career_minutes is not None else "NULL"
            adp_val = str(adp_value) if adp_value is not None else "NULL"
            time_val = f"'{created_at}'" if created_at else "NULL"

            f.write(
                "INSERT INTO players (id, name, adp_value, rarity_tier, image_url, career_minutes, created_at) "
            )
            f.write(
                f"VALUES ({player_id}, '{name_escaped}', {adp_val}, '{rarity_tier}', {image_val}, {minutes_val}, {time_val});\n"
            )

        f.write("\nCOMMIT;\n\n")

        # Add summary
        f.write(f"-- Total players exported: {len(players)}\n")
        f.write("-- No user collections, server configs, or leaderboard data included\n")

    conn.close()
    print(f"Exported {len(players)} players to {OUTPUT_PATH}")
    print(f"File size: {OUTPUT_PATH.stat().st_size / 1024:.2f} KB")
    return len(players)


if __name__ == "__main__":
    export_database()
