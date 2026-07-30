"""Versioned SQLite schema migrations."""
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from src.database.models import (
    CREATE_LEADERBOARD_SNAPSHOT_RUNS_TABLE,
    CREATE_PLAYERS_TABLE,
    CREATE_USER_COLLECTIONS_TABLE,
)

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
SchemaState = Literal["empty", "legacy_v0", "current_v1", "unknown"]

LEGACY_PLAYER_COLUMNS = {
    "id",
    "name",
    "adp_value",
    "rarity_tier",
    "image_url",
    "career_minutes",
    "created_at",
}
LEGACY_COLLECTION_COLUMNS = {
    "id",
    "user_id",
    "player_id",
    "caught_at",
    "server_id",
}
CURRENT_COLLECTION_COLUMNS = LEGACY_COLLECTION_COLUMNS | {"edition"}
SERVER_CONFIG_COLUMNS = {
    "server_id",
    "spawn_channels",
    "spawn_threshold",
    "created_at",
    "updated_at",
}
SNAPSHOT_COLUMNS = {
    "id",
    "user_id",
    "server_id",
    "period",
    "points",
    "player_count",
    "snapshot_date",
    "created_at",
}
SNAPSHOT_RUN_COLUMNS = {"server_id", "snapshot_date", "published_at"}
LEGACY_RARITIES = {"GOAT", "Mythic", "Legendary", "Epic", "Rare", "Uncommon", "Common"}
CURRENT_RARITIES = LEGACY_RARITIES | {"Cosmic"}


def migrate_schema(
    connection: sqlite3.Connection,
    database_path: str,
    backup_directory: str,
    *,
    allow_upgrade: bool = False,
) -> Optional[str]:
    """Upgrade an existing database and return its verified backup path."""
    schema_state = detect_schema_state(connection)
    if schema_state == "empty":
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        return None
    if schema_state == "current_v1":
        return None
    if schema_state == "unknown":
        raise RuntimeError(
            "Database schema is unknown or partially migrated; refusing automatic changes"
        )
    if not allow_upgrade:
        raise RuntimeError(
            "Database schema v0 requires an offline migration. "
            "Run scripts/migrate_database.py apply while the bot is stopped."
        )

    backup_path = _create_verified_backup(
        connection,
        database_path,
        backup_directory,
    )
    _rebuild_rarity_and_collection_tables(connection)
    if detect_schema_state(connection) != "current_v1":
        raise RuntimeError("Migration completed but the resulting schema is not version 1")
    logger.info("Database schema migrated to version %s", SCHEMA_VERSION)
    return backup_path


def detect_schema_state(connection: sqlite3.Connection) -> SchemaState:
    """Classify only the exact schemas that are safe to initialize or migrate."""
    players_sql = _get_table_sql(connection, "players")
    collections_sql = _get_table_sql(connection, "user_collections")
    server_configs_sql = _get_table_sql(connection, "server_configs")
    snapshots_sql = _get_table_sql(connection, "leaderboard_snapshots")
    snapshot_runs_sql = _get_table_sql(connection, "leaderboard_snapshot_runs")
    user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    if not _application_table_names(connection) and user_version == 0:
        return "empty"
    if None in (players_sql, collections_sql, server_configs_sql, snapshots_sql):
        return "unknown"

    player_columns = _get_column_names(connection, "players")
    collection_columns = _get_column_names(connection, "user_collections")
    has_player_foreign_key = _has_player_foreign_key(connection)
    if (
        player_columns != LEGACY_PLAYER_COLUMNS
        or not has_player_foreign_key
        or not _contains_rarities(players_sql, LEGACY_RARITIES)
        or not _has_unique_columns(connection, "players", ("name",))
        or _get_column_names(connection, "server_configs") != SERVER_CONFIG_COLUMNS
        or not _has_primary_key_columns(connection, "server_configs", ("server_id",))
        or _get_column_names(connection, "leaderboard_snapshots") != SNAPSHOT_COLUMNS
        or not _contains_snapshot_periods(snapshots_sql)
        or not _has_unique_columns(
            connection,
            "leaderboard_snapshots",
            ("user_id", "server_id", "period", "snapshot_date"),
        )
    ):
        return "unknown"

    is_legacy = (
        user_version == 0
        and snapshot_runs_sql is None
        and collection_columns == LEGACY_COLLECTION_COLUMNS
        and "Cosmic" not in players_sql
        and "edition" not in collections_sql
        and _has_unique_columns(
            connection,
            "user_collections",
            ("user_id", "player_id", "server_id"),
        )
    )
    if is_legacy:
        return "legacy_v0"

    is_current = (
        user_version == SCHEMA_VERSION
        and collection_columns == CURRENT_COLLECTION_COLUMNS
        and "Cosmic" in players_sql
        and "edition" in collections_sql
        and "Standard" in collections_sql
        and "Phantom" in collections_sql
        and _contains_rarities(players_sql, CURRENT_RARITIES)
        and snapshot_runs_sql is not None
        and _get_column_names(connection, "leaderboard_snapshot_runs") == SNAPSHOT_RUN_COLUMNS
        and _has_primary_key_columns(
            connection,
            "leaderboard_snapshot_runs",
            ("server_id", "snapshot_date"),
        )
        and _has_unique_columns(
            connection,
            "user_collections",
            ("user_id", "player_id", "server_id", "edition"),
        )
    )
    return "current_v1" if is_current else "unknown"


def _application_table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _get_column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}


def _contains_rarities(table_sql: str, rarities: set[str]) -> bool:
    return all(f"'{rarity}'" in table_sql for rarity in rarities)


def _contains_snapshot_periods(table_sql: str) -> bool:
    return all(f"'{period}'" in table_sql for period in ("weekly", "monthly", "yearly", "alltime"))


def _has_player_foreign_key(connection: sqlite3.Connection) -> bool:
    return any(
        row[2] == "players"
        and row[3] == "player_id"
        and row[4] == "id"
        and row[6].upper() == "CASCADE"
        for row in connection.execute("PRAGMA foreign_key_list(user_collections)")
    )


def _has_unique_columns(
    connection: sqlite3.Connection,
    table_name: str,
    expected_columns: tuple[str, ...],
) -> bool:
    for index in connection.execute(f"PRAGMA index_list({table_name})"):
        if not index[2]:
            continue
        columns = tuple(row[2] for row in connection.execute(f"PRAGMA index_info({index[1]})"))
        if columns == expected_columns:
            return True
    return False


def _has_primary_key_columns(
    connection: sqlite3.Connection,
    table_name: str,
    expected_columns: tuple[str, ...],
) -> bool:
    primary_key_columns = tuple(
        row[1]
        for row in sorted(
            (row for row in connection.execute(f"PRAGMA table_info({table_name})") if row[5]),
            key=lambda row: row[5],
        )
    )
    return primary_key_columns == expected_columns


def _get_table_sql(connection: sqlite3.Connection, table_name: str) -> Optional[str]:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row[0] if row else None


def _create_verified_backup(
    connection: sqlite3.Connection,
    database_path: str,
    backup_directory: str,
) -> str:
    """Create an online backup and reject migration if verification fails."""
    backup_dir = Path(backup_directory)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    database_name = Path(database_path).stem
    backup_path = backup_dir / f"{database_name}_pre_v{SCHEMA_VERSION}_{timestamp}.db"

    backup_connection = sqlite3.connect(str(backup_path))
    try:
        connection.backup(backup_connection)
        result = backup_connection.execute("PRAGMA integrity_check").fetchone()
        if result != ("ok",):
            raise RuntimeError(f"Migration backup integrity check failed: {backup_path}")
    finally:
        backup_connection.close()

    logger.info("Created verified pre-migration backup: %s", backup_path)
    return str(backup_path)


def _rebuild_rarity_and_collection_tables(connection: sqlite3.Connection) -> None:
    """Rebuild constrained tables while retaining all durable records."""
    player_count = connection.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    has_collections = _get_table_sql(connection, "user_collections") is not None
    collection_count = (
        connection.execute("SELECT COUNT(*) FROM user_collections").fetchone()[0]
        if has_collections
        else 0
    )
    connection.execute("PRAGMA foreign_keys = OFF")
    try:
        connection.execute("BEGIN IMMEDIATE")
        if has_collections:
            connection.execute("ALTER TABLE user_collections RENAME TO user_collections_v0")
        connection.execute("ALTER TABLE players RENAME TO players_v0")
        connection.execute(CREATE_PLAYERS_TABLE)
        connection.execute(CREATE_USER_COLLECTIONS_TABLE)
        connection.execute(CREATE_LEADERBOARD_SNAPSHOT_RUNS_TABLE)
        connection.execute(
            """
            INSERT INTO players
                (id, name, adp_value, rarity_tier, image_url, career_minutes, created_at)
            SELECT
                id,
                name,
                adp_value,
                CASE
                    WHEN adp_value >= 2.0 AND adp_value < 10.0 THEN 'Cosmic'
                    ELSE rarity_tier
                END,
                image_url,
                career_minutes,
                created_at
            FROM players_v0
            """
        )
        if has_collections:
            connection.execute(
                """
                INSERT INTO user_collections
                    (id, user_id, player_id, caught_at, server_id, edition)
                SELECT id, user_id, player_id, caught_at, server_id, 'Standard'
                FROM user_collections_v0
                """
            )
            connection.execute("DROP TABLE user_collections_v0")
        connection.execute("DROP TABLE players_v0")
        migrated_player_count = connection.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        migrated_collection_count = connection.execute(
            "SELECT COUNT(*) FROM user_collections"
        ).fetchone()[0]
        if (migrated_player_count, migrated_collection_count) != (
            player_count,
            collection_count,
        ):
            raise RuntimeError("Migration row-count validation failed")

        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise RuntimeError(
                f"Foreign key validation failed after migration: {foreign_key_errors}"
            )

        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys = ON")
