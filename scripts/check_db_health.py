"""Daily database health monitoring."""
import sqlite3
import os
import sys
from datetime import datetime

# Handle Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def check_database_health():
    """Run comprehensive database health checks."""
    db_path = os.getenv('DATABASE_PATH', 'data/hooper_two.db')

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check integrity
        integrity = cursor.execute('PRAGMA integrity_check').fetchone()[0]

        # Check mode
        journal_mode = cursor.execute('PRAGMA journal_mode').fetchone()[0]
        synchronous = cursor.execute('PRAGMA synchronous').fetchone()[0]

        # Check counts
        player_count = cursor.execute('SELECT COUNT(*) FROM players').fetchone()[0]
        collection_count = cursor.execute('SELECT COUNT(*) FROM user_collections').fetchone()[0]
        server_count = cursor.execute('SELECT COUNT(DISTINCT server_id) FROM server_configs').fetchone()[0]

        # Check database size
        db_size_mb = os.path.getsize(db_path) / (1024 * 1024)

        # Check for WAL file (should exist in WAL mode)
        wal_exists = os.path.exists(f"{db_path}-wal")
        wal_size_mb = 0
        if wal_exists:
            wal_size_mb = os.path.getsize(f"{db_path}-wal") / (1024 * 1024)

        print(f"\n{'='*60}")
        print(f"Database Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(f"✅ Integrity Check: {integrity}")
        print(f"📊 Journal Mode: {journal_mode}")
        print(f"🔒 Synchronous: {synchronous}")
        print(f"")
        print(f"📈 Database Statistics:")
        print(f"   👥 Players: {player_count:,}")
        print(f"   🏀 Collections: {collection_count:,}")
        print(f"   🖥️  Servers: {server_count:,}")
        print(f"")
        print(f"💾 Storage:")
        print(f"   Database: {db_size_mb:.2f} MB")
        if wal_exists:
            print(f"   WAL File: {wal_size_mb:.2f} MB")
            if wal_size_mb > 10:
                print(f"   ⚠️  WAL file large - consider checkpoint")
        else:
            print(f"   WAL File: Not present (expected in DELETE mode)")
        print(f"{'='*60}\n")

        conn.close()

        # Return health status
        is_healthy = integrity == "ok" and wal_size_mb < 50
        return is_healthy

    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


if __name__ == "__main__":
    healthy = check_database_health()
    exit(0 if healthy else 1)
