"""
MC Database initializer — applies mc_schema.sql to data/mc.db.

Usage:
    python migrate.py           # initialize (idempotent)
    python migrate.py --check   # only verify, no changes
"""

import sqlite3
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
SCHEMA_PATH  = PROJECT_ROOT / "Doc" / "phase4_design" / "schema" / "mc_schema.sql"
DB_DIR       = PROJECT_ROOT / "data"
DB_PATH      = Path(os.environ.get("MC_DB_PATH", DB_DIR / "mc.db"))

EXPECTED_VERSION = 8   # v1.8: contacts + item_contacts


def _user_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _table_count(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
    ).fetchone()[0]


def _column_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    return any(
        r[1] == col
        for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
    )


def _migrate_5_to_6(conn: sqlite3.Connection) -> None:
    """v5 → v6: hierarchical items (parent_id, start_date, due_date) + businesses.folder_path."""
    if not _column_exists(conn, "items", "parent_id"):
        conn.execute("ALTER TABLE items ADD COLUMN parent_id INTEGER REFERENCES items(id) ON DELETE CASCADE")
    if not _column_exists(conn, "items", "start_date"):
        conn.execute("ALTER TABLE items ADD COLUMN start_date TEXT")
    if not _column_exists(conn, "items", "due_date"):
        conn.execute("ALTER TABLE items ADD COLUMN due_date TEXT")
    if not _column_exists(conn, "items", "folder_path"):
        conn.execute("ALTER TABLE items ADD COLUMN folder_path TEXT")
    if not _column_exists(conn, "businesses", "folder_path"):
        conn.execute("ALTER TABLE businesses ADD COLUMN folder_path TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_items_parent ON items(parent_id)")
    conn.commit()


def _migrate_6_to_7(conn: sqlite3.Connection) -> None:
    """v6 → v7: recurring items (notification_events already exists from schema v0)."""
    if not _column_exists(conn, "items", "recurrence_rule"):
        conn.execute("ALTER TABLE items ADD COLUMN recurrence_rule TEXT")
    if not _column_exists(conn, "items", "recurrence_parent_id"):
        conn.execute(
            "ALTER TABLE items ADD COLUMN recurrence_parent_id INTEGER REFERENCES items(id)"
        )
    conn.commit()


def _migrate_7_to_8(conn: sqlite3.Connection) -> None:
    """v7 → v8: contacts + item_contacts (people for meetings)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
          id           INTEGER PRIMARY KEY,
          name         TEXT NOT NULL,
          email        TEXT,
          phone        TEXT,
          org          TEXT,
          notes        TEXT,
          created_at   TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS item_contacts (
          item_id     INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
          contact_id  INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
          role        TEXT NOT NULL DEFAULT 'attendee',
          PRIMARY KEY (item_id, contact_id)
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_item_contacts_item ON item_contacts(item_id)")
    conn.commit()


def migrate(check_only: bool = False) -> bool:
    DB_DIR.mkdir(parents=True, exist_ok=True)

    if not SCHEMA_PATH.exists():
        print(f"[ERROR] Schema not found: {SCHEMA_PATH}", file=sys.stderr)
        return False

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    current_ver = _user_version(conn)

    if check_only:
        tables = _table_count(conn)
        print(f"[CHECK] user_version={current_ver}  tables={tables}  db={DB_PATH}")
        conn.close()
        return current_ver >= EXPECTED_VERSION

    if current_ver == 0:
        print(f"[INIT]  Applying schema v{EXPECTED_VERSION} → {DB_PATH}")
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute(f"PRAGMA user_version = {EXPECTED_VERSION}")
        conn.commit()
        print(f"[OK]    user_version={EXPECTED_VERSION}  tables={_table_count(conn)}")
    elif current_ver < EXPECTED_VERSION:
        # Incremental migrations preserve user data.
        if current_ver == 5:
            print("[MIG]   v5 → v6 (hierarchical items + business folders)")
            _migrate_5_to_6(conn)
            current_ver = 6
        if current_ver == 6:
            print("[MIG]   v6 → v7 (recurring items + notification events)")
            _migrate_6_to_7(conn)
            current_ver = 7
        if current_ver == 7:
            print("[MIG]   v7 → v8 (contacts + item_contacts)")
            _migrate_7_to_8(conn)
        conn.execute(f"PRAGMA user_version = {EXPECTED_VERSION}")
        conn.commit()
        print(f"[OK]    user_version={EXPECTED_VERSION}")
    else:
        print(f"[SKIP]  DB already at version {current_ver}, no changes needed.")

    # Verify critical tables
    required = [
        "items", "tags", "item_tags", "projects", "project_stages",
        "organizations", "businesses", "schedules", "labels", "item_labels",
        "gcal_cache", "capture_inbox", "incomplete_reasons",
        "file_index", "settings",
    ]
    for table in required:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not row:
            print(f"[ERROR] Missing table: {table}", file=sys.stderr)
            conn.close()
            return False

    # Verify settings seed
    count = conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
    print(f"[OK]    settings rows: {count}")

    conn.close()
    return True


if __name__ == "__main__":
    check_only = "--check" in sys.argv
    ok = migrate(check_only=check_only)
    sys.exit(0 if ok else 1)
