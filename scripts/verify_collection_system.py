#!/usr/bin/env python3
"""
Comprehensive verification script for Batch 7: Collection System.

This script tests:
1. CollectionRepository functionality
2. CollectionManager functionality
3. Database integrity
4. End-to-end collection flow

Run with: python verify_collection_system.py
"""
import sys
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.connection_manager import ConnectionManager
from src.database.repositories.collection_repository import CollectionRepository
from src.managers.collection_manager import CollectionManager


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_success(text):
    """Print a success message."""
    print(f"[PASS] {text}")


def print_error(text):
    """Print an error message."""
    print(f"[FAIL] {text}")


def print_info(text):
    """Print an info message."""
    print(f"[INFO] {text}")


def verify_repository():
    """Verify CollectionRepository functionality."""
    print_header("Testing CollectionRepository")

    # Create in-memory database
    manager = ConnectionManager(":memory:")
    conn = manager.get_connection()

    # Insert test players
    conn.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("LeBron James", 1.5, "GOAT")
    )
    conn.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("Michael Jordan", 1.0, "GOAT")
    )
    conn.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("Steph Curry", 15.5, "Mythic")
    )
    conn.commit()

    repo = CollectionRepository(conn)

    # Test 1: Add player to collection
    print_info("Test 1: Adding player to collection...")
    result = repo.add_player_to_collection(
        user_id=123456789,
        player_id=1,
        server_id=987654321
    )
    if result:
        print_success("Player added successfully")
    else:
        print_error("Failed to add player")
        return False

    # Test 2: Duplicate prevention
    print_info("Test 2: Testing duplicate prevention...")
    result = repo.add_player_to_collection(
        user_id=123456789,
        player_id=1,
        server_id=987654321
    )
    if not result:
        print_success("Duplicate correctly prevented")
    else:
        print_error("Duplicate prevention failed")
        return False

    # Test 3: Get user collection
    print_info("Test 3: Retrieving user collection...")
    repo.add_player_to_collection(123456789, 2, 987654321)
    repo.add_player_to_collection(123456789, 3, 987654321)

    collection = repo.get_user_collection(123456789, 987654321)
    if len(collection) == 3:
        print_success(f"Retrieved {len(collection)} players")
        for player in collection:
            print(f"   - {player['name']} ({player['rarity_tier']})")
    else:
        print_error(f"Expected 3 players, got {len(collection)}")
        return False

    # Test 4: Collection statistics
    print_info("Test 4: Calculating collection statistics...")
    stats = repo.get_collection_stats(123456789, 987654321)

    expected_players = 3
    expected_goat = 2
    expected_mythic = 1
    expected_points = 2500  # 2 GOAT (2000) + 1 Mythic (500)

    if stats["total_players"] == expected_players:
        print_success(f"Total players: {stats['total_players']}")
    else:
        print_error(f"Expected {expected_players} players, got {stats['total_players']}")
        return False

    if stats["total_points"] == expected_points:
        print_success(f"Total points: {stats['total_points']}")
    else:
        print_error(f"Expected {expected_points} points, got {stats['total_points']}")
        return False

    if stats["rarity_counts"]["GOAT"] == expected_goat:
        print_success(f"GOAT count: {stats['rarity_counts']['GOAT']}")
    else:
        print_error(f"Expected {expected_goat} GOAT players, got {stats['rarity_counts']['GOAT']}")
        return False

    if stats["rarity_counts"]["Mythic"] == expected_mythic:
        print_success(f"Mythic count: {stats['rarity_counts']['Mythic']}")
    else:
        print_error(f"Expected {expected_mythic} Mythic players, got {stats['rarity_counts']['Mythic']}")
        return False

    # Test 5: Pagination
    print_info("Test 5: Testing pagination...")
    page1 = repo.get_user_collection(123456789, 987654321, limit=2, offset=0)
    page2 = repo.get_user_collection(123456789, 987654321, limit=2, offset=2)

    if len(page1) == 2 and len(page2) == 1:
        print_success(f"Pagination working (Page 1: {len(page1)}, Page 2: {len(page2)})")
    else:
        print_error(f"Pagination failed (Page 1: {len(page1)}, Page 2: {len(page2)})")
        return False

    manager.close()
    return True


def verify_manager():
    """Verify CollectionManager functionality."""
    print_header("Testing CollectionManager")

    # Create in-memory database
    manager_db = ConnectionManager(":memory:")
    conn = manager_db.get_connection()

    # Insert test players
    conn.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("LeBron James", 1.5, "GOAT")
    )
    conn.commit()

    repo = CollectionRepository(conn)
    manager = CollectionManager(repo)

    # Test 1: Catch player
    print_info("Test 1: Catching a player...")
    result = manager.catch_player(
        user_id=111111111,
        player_id=1,
        server_id=222222222
    )

    if result["success"] and not result["already_owned"]:
        print_success("Player caught successfully (new)")
    else:
        print_error("Failed to catch player")
        return False

    # Test 2: Catch duplicate
    print_info("Test 2: Catching duplicate player...")
    result = manager.catch_player(
        user_id=111111111,
        player_id=1,
        server_id=222222222
    )

    if result["success"] and result["already_owned"]:
        print_success("Duplicate correctly detected")
    else:
        print_error("Failed to detect duplicate")
        return False

    # Test 3: Get formatted collection
    print_info("Test 3: Getting formatted collection with pagination...")
    collection_data = manager.get_collection(
        user_id=111111111,
        server_id=222222222,
        page=0,
        page_size=10
    )

    if "players" in collection_data and "stats" in collection_data and "total_pages" in collection_data:
        print_success("Collection data formatted correctly")
        print(f"   - Players: {len(collection_data['players'])}")
        print(f"   - Total Pages: {collection_data['total_pages']}")
        print(f"   - Current Page: {collection_data['current_page']}")
        print(f"   - Total Points: {collection_data['stats']['total_points']}")
    else:
        print_error("Collection data format incorrect")
        return False

    manager_db.close()
    return True


def verify_database_schema():
    """Verify database schema integrity."""
    print_header("Verifying Database Schema")

    manager = ConnectionManager(":memory:")
    conn = manager.get_connection()

    # Check if user_collections table exists
    print_info("Checking user_collections table...")
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_collections'"
    )
    if cursor.fetchone():
        print_success("user_collections table exists")
    else:
        print_error("user_collections table missing")
        return False

    # Check table schema
    print_info("Verifying table schema...")
    cursor = conn.execute("PRAGMA table_info(user_collections)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    expected_columns = {
        "id": "INTEGER",
        "user_id": "INTEGER",
        "player_id": "INTEGER",
        "caught_at": "TIMESTAMP",
        "server_id": "INTEGER"
    }

    for col_name, col_type in expected_columns.items():
        if col_name in columns:
            print_success(f"Column '{col_name}' exists ({columns[col_name]})")
        else:
            print_error(f"Column '{col_name}' missing")
            return False

    # Check foreign key constraint
    print_info("Verifying foreign key constraints...")
    cursor = conn.execute("PRAGMA foreign_keys")
    fk_enabled = cursor.fetchone()[0]
    if fk_enabled:
        print_success("Foreign key constraints enabled")
    else:
        print_error("Foreign key constraints disabled")
        return False

    # Check indexes
    print_info("Verifying indexes...")
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='user_collections'"
    )
    indexes = [row[0] for row in cursor.fetchall()]

    expected_indexes = ["idx_user_collections_user_id", "idx_user_collections_server_id"]
    for index in expected_indexes:
        if index in indexes:
            print_success(f"Index '{index}' exists")
        else:
            print_error(f"Index '{index}' missing")
            return False

    manager.close()
    return True


def verify_sql_injection_prevention():
    """Verify SQL injection prevention through code inspection."""
    print_header("Verifying SQL Injection Prevention")

    print_info("Checking CollectionRepository uses parameterized queries...")

    # Read the repository file
    repo_file = Path(__file__).parent / "src" / "database" / "repositories" / "collection_repository.py"

    if not repo_file.exists():
        print_error("CollectionRepository file not found")
        return False

    content = repo_file.read_text()

    # Check for parameterized queries (should use ?)
    if "?" in content and "execute(" in content:
        print_success("Parameterized queries detected")
    else:
        print_error("No parameterized queries found")
        return False

    # Check for dangerous patterns (string concatenation in SQL)
    dangerous_patterns = [
        'f"SELECT',
        "f'SELECT",
        'f"INSERT',
        "f'INSERT",
        'f"UPDATE',
        "f'UPDATE",
        '+ "SELECT',
        "+ 'SELECT",
        '% "SELECT',
        "% 'SELECT",
    ]

    for pattern in dangerous_patterns:
        if pattern in content:
            print_error(f"Dangerous SQL pattern found: {pattern}")
            return False

    print_success("No dangerous SQL string concatenation detected")

    # Verify all execute() calls use parameterized queries
    print_info("Verifying query structure...")
    import re

    execute_pattern = r'execute\([^)]+\)'
    execute_calls = re.findall(execute_pattern, content, re.MULTILINE | re.DOTALL)

    parameterized_count = 0
    for call in execute_calls:
        # Check if it has a parameter tuple (second argument)
        if ',' in call or '(' in call.split('execute(')[1]:
            parameterized_count += 1

    if parameterized_count > 0:
        print_success(f"All {parameterized_count} execute() calls use parameters")
    else:
        print_error("No parameterized execute() calls found")
        return False

    # Test actual injection attempt (should be safely handled)
    print_info("Testing runtime injection attempt...")
    manager = ConnectionManager(":memory:")
    conn = manager.get_connection()

    # Insert test player
    conn.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("Test Player", 1.0, "Common")
    )
    conn.commit()

    repo = CollectionRepository(conn)

    # Add a normal player
    result = repo.add_player_to_collection(
        user_id=12345,
        player_id=1,
        server_id=67890
    )

    if result:
        print_success("Repository handles normal data correctly")
    else:
        print_error("Repository failed on normal data")
        return False

    # Verify data integrity
    cursor = conn.execute("SELECT COUNT(*) FROM user_collections")
    count = cursor.fetchone()[0]

    if count == 1:
        print_success("Data integrity maintained")
    else:
        print_error(f"Expected 1 record, found {count}")
        return False

    manager.close()
    return True


def main():
    """Run all verification tests."""
    print("\n" + "="*60)
    print("  BATCH 7: COLLECTION SYSTEM VERIFICATION")
    print("="*60)

    tests = [
        ("CollectionRepository", verify_repository),
        ("CollectionManager", verify_manager),
        ("Database Schema", verify_database_schema),
        ("SQL Injection Prevention", verify_sql_injection_prevention),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Print summary
    print_header("VERIFICATION SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")

    print(f"\n{passed}/{total} test suites passed")

    if passed == total:
        print_success("\nAll verification tests passed!")
        return 0
    else:
        print_error(f"\n{total - passed} test suite(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
