"""Offline database migration commands for production deployments."""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.migrations import (  # noqa: E402
    CURRENT_RARITIES,
    detect_schema_state,
    migrate_schema,
)
from src.database.models import ALL_TABLES, CREATE_INDEXES  # noqa: E402

EXPECTED_COSMIC_PLAYERS = {
    "Hakeem Olajuwon",
    "Kevin Garnett",
    "Larry Bird",
    "Magic Johnson",
    "Shaquille O'Neal",
    "Stephen Curry",
}
COUNTED_TABLES = (
    "players",
    "user_collections",
    "server_configs",
    "leaderboard_snapshots",
    "leaderboard_snapshot_runs",
)


def _connect(database_path: Path) -> sqlite3.Connection:
    if not database_path.is_file():
        raise RuntimeError(f"Database does not exist: {database_path}")
    connection = sqlite3.connect(str(database_path), timeout=1, isolation_level=None)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _database_sha256(database_path: Path) -> str:
    digest = hashlib.sha256()
    with database_path.open("rb") as database_file:
        for chunk in iter(lambda: database_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def _row_counts(connection: sqlite3.Connection) -> dict[str, int]:
    existing_tables = _table_names(connection)
    return {
        table_name: connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        for table_name in COUNTED_TABLES
        if table_name in existing_tables
    }


def _check_database(connection: sqlite3.Connection, expected_state: str) -> dict[str, Any]:
    state = detect_schema_state(connection)
    if state != expected_state:
        raise RuntimeError(f"Expected schema {expected_state}, found {state}")

    integrity_result = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity_result != ("ok",):
        raise RuntimeError(f"SQLite integrity check failed: {integrity_result}")
    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise RuntimeError(f"Foreign key check failed: {foreign_key_errors}")

    required_tables = {
        "players",
        "user_collections",
        "server_configs",
        "leaderboard_snapshots",
    }
    missing_tables = required_tables - _table_names(connection)
    if missing_tables:
        raise RuntimeError(f"Required tables are missing: {sorted(missing_tables)}")

    allowed_rarities = (
        CURRENT_RARITIES if expected_state == "current_v1" else CURRENT_RARITIES - {"Cosmic"}
    )
    invalid_rarities = connection.execute(
        f"""
        SELECT DISTINCT rarity_tier
        FROM players
        WHERE rarity_tier NOT IN ({",".join("?" for _ in allowed_rarities)})
        """,
        tuple(sorted(allowed_rarities)),
    ).fetchall()
    if invalid_rarities:
        raise RuntimeError(f"Players contain invalid rarities: {invalid_rarities}")

    if expected_state == "current_v1":
        invalid_editions = connection.execute(
            """
            SELECT DISTINCT edition
            FROM user_collections
            WHERE edition NOT IN (?, ?)
            """,
            ("Standard", "Phantom"),
        ).fetchall()
        if invalid_editions:
            raise RuntimeError(f"Collections contain invalid editions: {invalid_editions}")
        cosmic_players = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM players WHERE rarity_tier = ?",
                ("Cosmic",),
            )
        }
        if cosmic_players != EXPECTED_COSMIC_PLAYERS:
            raise RuntimeError(
                "Cosmic player set does not match the approved six players: "
                f"{sorted(cosmic_players)}"
            )

    return {
        "schema_state": state,
        "schema_version": connection.execute("PRAGMA user_version").fetchone()[0],
        "row_counts": _row_counts(connection),
    }


def _assert_offline(connection: sqlite3.Connection, confirmed: bool) -> None:
    if not confirmed:
        raise RuntimeError("Refusing write operation without --confirm-offline")
    try:
        connection.execute("BEGIN EXCLUSIVE")
        connection.rollback()
    except sqlite3.OperationalError as error:
        raise RuntimeError(
            "Could not acquire an exclusive database lock; ensure the bot is stopped"
        ) from error


def preflight(
    database_path: Path,
    backup_directory: Optional[Path] = None,
) -> dict[str, Any]:
    """Validate a canonical legacy or already-current production database."""
    connection = _connect(database_path)
    try:
        state = detect_schema_state(connection)
        if state not in {"legacy_v0", "current_v1"}:
            raise RuntimeError(f"Unsafe schema state: {state}")
        result = _check_database(connection, state)
    finally:
        connection.close()
    result["database_path"] = str(database_path.resolve())
    result["database_sha256"] = _database_sha256(database_path)
    if backup_directory is not None:
        backup_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=backup_directory):
            pass
        result["backup_directory"] = str(backup_directory.resolve())
    return result


def apply_migration(
    database_path: Path,
    backup_directory: Path,
    confirmed_offline: bool,
) -> dict[str, Any]:
    """Apply v1 transactionally and write a backup-linked manifest."""
    connection = _connect(database_path)
    try:
        _assert_offline(connection, confirmed_offline)
        state = detect_schema_state(connection)
        if state == "current_v1":
            result = _check_database(connection, "current_v1")
            result["status"] = "already_current"
            return result
        if state != "legacy_v0":
            raise RuntimeError(f"Unsafe schema state: {state}")

        before = _check_database(connection, "legacy_v0")
        backup_path_value = migrate_schema(
            connection,
            str(database_path),
            str(backup_directory),
            allow_upgrade=True,
        )
        if backup_path_value is None:
            raise RuntimeError("Migration did not create its required backup")
        for table_sql in ALL_TABLES:
            connection.execute(table_sql)
        for index_sql in CREATE_INDEXES:
            connection.execute(index_sql)
        connection.commit()
        after = _check_database(connection, "current_v1")
    finally:
        connection.close()

    preserved_counts = {
        table_name: count
        for table_name, count in before["row_counts"].items()
        if table_name in after["row_counts"]
    }
    changed_counts = {
        table_name: (count, after["row_counts"].get(table_name))
        for table_name, count in preserved_counts.items()
        if after["row_counts"].get(table_name) != count
    }
    if changed_counts:
        raise RuntimeError(f"Migration changed preserved row counts: {changed_counts}")

    backup_path = Path(backup_path_value)
    manifest = {
        "migration": "phantom_cosmic_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "database_path": str(database_path.resolve()),
        "database_sha256_before": _database_sha256(backup_path),
        "database_sha256_after": _database_sha256(database_path),
        "backup_path": str(backup_path.resolve()),
        "backup_sha256": _database_sha256(backup_path),
        "before": before,
        "after": after,
    }
    manifest_path = backup_path.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "status": "migrated",
        "backup_path": str(backup_path),
        "manifest_path": str(manifest_path),
        **after,
    }


def verify(database_path: Path, manifest_path: Optional[Path] = None) -> dict[str, Any]:
    """Verify current schema, data invariants, and optional migration counts."""
    connection = _connect(database_path)
    try:
        result = _check_database(connection, "current_v1")
    finally:
        connection.close()

    if manifest_path is not None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_counts = manifest["before"]["row_counts"]
        changed_counts = {
            table_name: (count, result["row_counts"].get(table_name))
            for table_name, count in expected_counts.items()
            if result["row_counts"].get(table_name) != count
        }
        if changed_counts:
            raise RuntimeError(f"Row counts differ from migration manifest: {changed_counts}")
        if _database_sha256(database_path) != manifest["database_sha256_after"]:
            raise RuntimeError("Database hash differs from migration manifest")
        result["manifest_path"] = str(manifest_path)
    return result


def _create_rollback_safety_backup(database_path: Path, backup_directory: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_path = backup_directory / f"{database_path.stem}_pre_rollback_{timestamp}.db"
    source = sqlite3.connect(str(database_path))
    destination = sqlite3.connect(str(backup_path))
    try:
        source.backup(destination)
        if destination.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise RuntimeError("Rollback safety backup failed integrity validation")
    finally:
        destination.close()
        source.close()
    return backup_path


def rollback(
    database_path: Path,
    backup_directory: Path,
    backup_path: Path,
    manifest_path: Path,
    confirmed_offline: bool,
) -> dict[str, Any]:
    """Atomically restore the verified pre-migration backup."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if database_path.resolve() != Path(manifest["database_path"]).resolve():
        raise RuntimeError("Target database path does not match the migration manifest")
    if backup_path.resolve() != Path(manifest["backup_path"]).resolve():
        raise RuntimeError("Backup path does not match the migration manifest")
    if _database_sha256(backup_path) != manifest["backup_sha256"]:
        raise RuntimeError("Backup hash does not match the migration manifest")

    backup_connection = sqlite3.connect(f"file:{backup_path.resolve()}?mode=ro", uri=True)
    try:
        if backup_connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise RuntimeError("Selected rollback backup failed integrity validation")
        if detect_schema_state(backup_connection) != "legacy_v0":
            raise RuntimeError("Selected rollback backup is not the canonical legacy schema")
    finally:
        backup_connection.close()

    connection = _connect(database_path)
    try:
        _assert_offline(connection, confirmed_offline)
    finally:
        connection.close()
    safety_backup = _create_rollback_safety_backup(database_path, backup_directory)

    restore_path = database_path.with_suffix(database_path.suffix + ".restore")
    shutil.copy2(backup_path, restore_path)
    os.replace(restore_path, database_path)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{database_path}{suffix}")
        if sidecar.exists():
            sidecar.unlink()
    restored = preflight(database_path)
    if restored["schema_state"] != "legacy_v0":
        raise RuntimeError("Rollback did not restore the legacy schema")
    return {
        "status": "rolled_back",
        "restored_backup": str(backup_path),
        "safety_backup": str(safety_backup),
        **restored,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(os.getenv("DATABASE_PATH", "data/hooper_two.db")),
    )
    parser.add_argument(
        "--backup-directory",
        type=Path,
        default=Path(os.getenv("BACKUP_DIRECTORY", "data/backups")),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--confirm-offline", action="store_true")
    apply_parser.add_argument("--result-file", type=Path)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--manifest", type=Path)
    verify_parser.add_argument("--apply-result", type=Path)

    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--backup", type=Path, required=True)
    rollback_parser.add_argument("--manifest", type=Path, required=True)
    rollback_parser.add_argument("--confirm-offline", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.command == "preflight":
            result = preflight(args.database, args.backup_directory)
        elif args.command == "apply":
            result = apply_migration(
                args.database,
                args.backup_directory,
                args.confirm_offline,
            )
        elif args.command == "verify":
            manifest_path = args.manifest
            if args.apply_result is not None:
                apply_result = json.loads(args.apply_result.read_text(encoding="utf-8"))
                manifest_value = apply_result.get("manifest_path")
                manifest_path = Path(manifest_value) if manifest_value else None
            result = verify(args.database, manifest_path)
        else:
            result = rollback(
                args.database,
                args.backup_directory,
                args.backup,
                args.manifest,
                args.confirm_offline,
            )
    except (OSError, KeyError, ValueError, RuntimeError, sqlite3.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    result_file = getattr(args, "result_file", None)
    if result_file is not None:
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
