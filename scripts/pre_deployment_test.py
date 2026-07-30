"""Pre-deployment validation script - Test production readiness."""
import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime

# Handle Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


class Colors:
    """Terminal colors for output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"


def print_header(text):
    """Print section header."""
    print(f"\n{Colors.BLUE}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{Colors.END}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def test_database_connection():
    """Test database connection and basic queries."""
    print_header("TEST 1: Database Connection")

    db_path = os.getenv("DATABASE_PATH", "data/hooper_two.db")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Test query
        cursor.execute("SELECT COUNT(*) FROM players")
        player_count = cursor.fetchone()[0]

        print_success(f"Database connected: {db_path}")
        print_success(f"Player count: {player_count:,}")

        conn.close()
        return True

    except Exception as e:
        print_error(f"Database connection failed: {e}")
        return False


def test_database_integrity():
    """Test database integrity."""
    print_header("TEST 2: Database Integrity")

    db_path = os.getenv("DATABASE_PATH", "data/hooper_two.db")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]

        if result == "ok":
            print_success("Database integrity: OK")
            conn.close()
            return True
        else:
            print_error(f"Database integrity failed: {result}")
            conn.close()
            return False

    except Exception as e:
        print_error(f"Integrity check failed: {e}")
        return False


def test_wal_mode_compatibility():
    """Test WAL mode enablement and compatibility."""
    print_header("TEST 3: WAL Mode Compatibility")

    db_path = os.getenv("DATABASE_PATH", "data/hooper_two.db")
    environment = os.getenv("ENVIRONMENT", "development")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check current mode
        current_mode = cursor.execute("PRAGMA journal_mode").fetchone()[0]
        print(f"📊 Current journal mode: {current_mode}")
        print(f"🔧 Environment: {environment}")

        if environment == "production":
            if current_mode.lower() == "wal":
                print_success("WAL mode enabled (production)")
            else:
                print_warning(f"Production mode but WAL not enabled (mode: {current_mode})")
                print_warning("WAL will be enabled on next bot start")
        else:
            print_success(f"Development mode (journal mode: {current_mode})")

        # Test WAL compatibility (try enabling temporarily)
        test_db = "data/test_wal_compatibility.db"
        test_conn = sqlite3.connect(test_db)
        test_conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
        result = test_conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]

        if result.lower() == "wal":
            print_success("WAL mode compatible with this SQLite version")
        else:
            print_error("WAL mode not supported by this SQLite version")
            return False

        test_conn.close()
        if os.path.exists(test_db):
            os.remove(test_db)
            for ext in ["-wal", "-shm"]:
                if os.path.exists(test_db + ext):
                    os.remove(test_db + ext)

        conn.close()
        return True

    except Exception as e:
        print_error(f"WAL compatibility test failed: {e}")
        return False


def test_backup_system():
    """Test backup creation and verification."""
    print_header("TEST 4: Backup System")

    try:
        # Import backup script
        import scripts.backup_database as backup_module

        # Create backup
        print("Creating test backup...")
        backup_module.backup_database()

        # Verify backup created
        backup_dir = Path(os.getenv("BACKUP_DIRECTORY", "data/backups"))
        backups = sorted(backup_dir.glob("hoopertwo_backup_*.db"))

        if not backups:
            print_error("No backups found after creation")
            return False

        latest_backup = backups[-1]
        print_success(f"Backup created: {latest_backup.name}")

        # Verify backup integrity
        conn = sqlite3.connect(str(latest_backup))
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        player_count = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        conn.close()

        if integrity == "ok":
            print_success("Backup integrity: OK")
            print_success(f"Backup player count: {player_count:,}")
            return True
        else:
            print_error(f"Backup integrity failed: {integrity}")
            return False

    except Exception as e:
        print_error(f"Backup test failed: {e}")
        return False


def test_environment_variables():
    """Test required environment variables."""
    print_header("TEST 5: Environment Variables")

    required_vars = {
        "DISCORD_TOKEN": "Discord bot token",
        "DATABASE_PATH": "Database file path",
        "BACKUP_DIRECTORY": "Backup directory path",
    }

    optional_vars = {
        "COMMAND_SYNC_MODE": "Command sync mode (guild/global)",
        "ENVIRONMENT": "Environment (development/production)",
    }

    all_present = True

    print("Required variables:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            display_value = value if var != "DISCORD_TOKEN" else "*" * 20
            print_success(f"{var}: {display_value}")
        else:
            print_error(f"{var}: NOT SET ({description})")
            all_present = False

    print("\nOptional variables:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print_success(f"{var}: {value}")
        else:
            print_warning(f"{var}: Not set (will use default)")

    return all_present


def test_docker_volume_persistence():
    """Test Docker volume configuration."""
    print_header("TEST 6: Docker Volume Persistence")

    try:
        # Check if running in Docker
        in_docker = os.path.exists("/.dockerenv")

        if in_docker:
            print("🐳 Running inside Docker container")

            # Check if data directory is mounted
            data_path = Path("data")
            if data_path.exists() and data_path.is_dir():
                print_success("Data directory mounted: data/")

                # Check write permissions
                test_file = data_path / ".write_test"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                    print_success("Write permissions: OK")
                except Exception as e:
                    print_error(f"Write permission test failed: {e}")
                    return False
            else:
                print_error("Data directory not mounted!")
                return False

        else:
            print("💻 Running on host (not in Docker)")
            print_success("Skipping Docker-specific checks")

        return True

    except Exception as e:
        print_error(f"Docker volume test failed: {e}")
        return False


def test_database_schema():
    """Test database schema completeness."""
    print_header("TEST 7: Database Schema")

    db_path = os.getenv("DATABASE_PATH", "data/hooper_two.db")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for required tables
        required_tables = [
            "players",
            "user_collections",
            "leaderboard_snapshots",
            "leaderboard_snapshot_runs",
            "server_configs",
        ]

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        all_present = True
        for table in required_tables:
            if table in existing_tables:
                # Count rows
                count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print_success(f"Table '{table}': {count:,} rows")
            else:
                print_error(f"Table '{table}': MISSING")
                all_present = False

        if "user_collections" in existing_tables:
            collection_columns = {
                row[1] for row in cursor.execute("PRAGMA table_info(user_collections)")
            }
            if "edition" in collection_columns:
                print_success("Collection edition column: present")
            else:
                print_error("Collection edition column: MISSING")
                all_present = False

        schema_version = cursor.execute("PRAGMA user_version").fetchone()[0]
        if schema_version >= 1:
            print_success(f"Schema version: {schema_version}")
        else:
            print_error(f"Schema version is outdated: {schema_version}")
            all_present = False

        # Check for indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"\n📊 Indexes: {len(indexes)} found")

        conn.close()
        return all_present

    except Exception as e:
        print_error(f"Schema test failed: {e}")
        return False


def run_all_tests():
    """Run all pre-deployment tests."""
    print(f"\n{Colors.BLUE}{'='*70}")
    print("HooperTwo Pre-Deployment Validation")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}{Colors.END}")

    tests = [
        ("Database Connection", test_database_connection),
        ("Database Integrity", test_database_integrity),
        ("WAL Mode Compatibility", test_wal_mode_compatibility),
        ("Backup System", test_backup_system),
        ("Environment Variables", test_environment_variables),
        ("Docker Volume Persistence", test_docker_volume_persistence),
        ("Database Schema", test_database_schema),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    print_header("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")

    print(f"\n{Colors.BLUE}{'='*70}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'='*70}{Colors.END}\n")

    if passed == total:
        print_success("🎉 All tests passed! Ready for production deployment.")
        return 0
    else:
        print_error(f"❌ {total - passed} test(s) failed. Fix issues before deploying.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
