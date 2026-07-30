import json
import sqlite3
import sys
from pathlib import Path

import pytest

from scripts.migrate_database import (
    EXPECTED_COSMIC_PLAYERS,
    apply_migration,
    main,
    preflight,
    rollback,
    verify,
)


LEGACY_SCHEMA = """
CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    adp_value REAL,
    rarity_tier TEXT NOT NULL CHECK(
        rarity_tier IN (
            'GOAT', 'Mythic', 'Legendary', 'Epic',
            'Rare', 'Uncommon', 'Common'
        )
    ),
    image_url TEXT,
    career_minutes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE user_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    server_id INTEGER NOT NULL,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    UNIQUE(user_id, player_id, server_id)
);
CREATE TABLE server_configs (
    server_id INTEGER PRIMARY KEY,
    spawn_channels TEXT NOT NULL DEFAULT '[]',
    spawn_threshold INTEGER NOT NULL DEFAULT 500,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE leaderboard_snapshots (
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


def _create_legacy_database(database_path):
    connection = sqlite3.connect(database_path)
    connection.executescript(LEGACY_SCHEMA)
    cosmic_rows = [
        (name, adp_value, "Mythic")
        for name, adp_value in zip(sorted(EXPECTED_COSMIC_PLAYERS), range(2, 8))
    ]
    connection.executemany(
        """
        INSERT INTO players (name, adp_value, rarity_tier, image_url, career_minutes)
        VALUES (?, ?, ?, NULL, 1000)
        """,
        cosmic_rows + [("Michael Jordan", 1.0, "GOAT")],
    )
    connection.execute(
        """
        INSERT INTO user_collections (user_id, player_id, caught_at, server_id)
        VALUES (?, ?, ?, ?)
        """,
        (123, 1, "2026-07-30 12:00:00", 456),
    )
    connection.execute(
        """
        INSERT INTO leaderboard_snapshots
            (user_id, server_id, period, points, player_count, snapshot_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (123, 456, "alltime", 100, 1, "2026-07-30"),
    )
    connection.commit()
    connection.close()


def test_offline_migration_verify_and_rollback(tmp_path):
    database_path = tmp_path / "production.db"
    backup_directory = tmp_path / "backups"
    _create_legacy_database(database_path)

    before = preflight(database_path)
    assert before["schema_state"] == "legacy_v0"
    assert before["row_counts"]["players"] == 7
    with pytest.raises(RuntimeError, match="confirm-offline"):
        apply_migration(database_path, backup_directory, False)

    applied = apply_migration(database_path, backup_directory, True)
    assert applied["status"] == "migrated"
    assert applied["schema_state"] == "current_v1"
    assert applied["row_counts"]["user_collections"] == 1

    manifest_path = Path(applied["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    backup_path = Path(manifest["backup_path"])

    verified = verify(database_path, manifest_path)
    assert verified["schema_version"] == 1
    assert verified["row_counts"]["leaderboard_snapshots"] == 1

    rolled_back = rollback(
        database_path,
        backup_directory,
        backup_path,
        manifest_path,
        True,
    )
    assert rolled_back["status"] == "rolled_back"
    assert rolled_back["schema_state"] == "legacy_v0"
    assert rolled_back["row_counts"] == before["row_counts"]
    assert list(backup_directory.glob("*_pre_rollback_*.db"))


def test_preflight_rejects_partial_edition_schema(tmp_path):
    database_path = tmp_path / "partial.db"
    _create_legacy_database(database_path)
    connection = sqlite3.connect(database_path)
    connection.execute("ALTER TABLE user_collections ADD COLUMN edition TEXT DEFAULT 'Standard'")
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="unknown"):
        preflight(database_path)


def test_preflight_rejects_malformed_snapshot_schema(tmp_path):
    database_path = tmp_path / "malformed.db"
    backup_directory = tmp_path / "backups"
    _create_legacy_database(database_path)
    apply_migration(database_path, backup_directory, True)

    connection = sqlite3.connect(database_path)
    connection.execute("DROP TABLE leaderboard_snapshots")
    connection.execute("CREATE TABLE leaderboard_snapshots (id INTEGER PRIMARY KEY)")
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="unknown"):
        preflight(database_path)


def test_rollback_rejects_different_target_database(tmp_path):
    database_path = tmp_path / "production.db"
    other_database_path = tmp_path / "other.db"
    backup_directory = tmp_path / "backups"
    _create_legacy_database(database_path)
    _create_legacy_database(other_database_path)
    applied = apply_migration(database_path, backup_directory, True)
    manifest_path = Path(applied["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    with pytest.raises(RuntimeError, match="Target database path"):
        rollback(
            other_database_path,
            backup_directory,
            Path(manifest["backup_path"]),
            manifest_path,
            True,
        )


def test_cli_verifies_apply_result_manifest(tmp_path, monkeypatch, capsys):
    database_path = tmp_path / "production.db"
    backup_directory = tmp_path / "backups"
    result_path = backup_directory / "latest-migration-result.json"
    _create_legacy_database(database_path)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "migrate_database.py",
            "--database",
            str(database_path),
            "--backup-directory",
            str(backup_directory),
            "apply",
            "--confirm-offline",
            "--result-file",
            str(result_path),
        ],
    )
    assert main() == 0
    assert json.loads(result_path.read_text(encoding="utf-8"))["status"] == "migrated"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "migrate_database.py",
            "--database",
            str(database_path),
            "verify",
            "--apply-result",
            str(result_path),
        ],
    )
    assert main() == 0
    assert '"schema_state": "current_v1"' in capsys.readouterr().out
