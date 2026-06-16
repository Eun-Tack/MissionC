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

EXPECTED_VERSION = 14  # v1.14: organization AI role/profile metadata


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
    _ensure_contacts_tables(conn)
    _ensure_item_links_table(conn)
    conn.commit()


def _ensure_contacts_tables(conn: sqlite3.Connection) -> None:
    """Repair contacts tables even when an older DB has an advanced user_version."""
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


def _ensure_item_links_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS item_links (
          id             INTEGER PRIMARY KEY AUTOINCREMENT,
          src_type       TEXT NOT NULL CHECK(src_type IN ('project','item','gh_issue','gh_pr','gcal_event','drive_file')),
          src_id         INTEGER NOT NULL,
          dst_type       TEXT NOT NULL CHECK(dst_type IN ('project','item','gh_issue','gh_pr','gcal_event','drive_file')),
          dst_id         INTEGER NOT NULL,
          relation       TEXT NOT NULL DEFAULT 'relates_to'
                         CHECK(relation IN ('relates_to','blocks','depends_on','supports','duplicates','parent_child')),
          reason         TEXT,
          created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
          UNIQUE(src_type, src_id, dst_type, dst_id, relation)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_item_links_src ON item_links(src_type, src_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_item_links_dst ON item_links(dst_type, dst_id)")


def _ensure_integration_state_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS integration_state (
          provider        TEXT PRIMARY KEY,
          status          TEXT NOT NULL DEFAULT 'unknown'
                          CHECK(status IN ('unknown','ok','not_configured','error')),
          last_success_at TEXT,
          last_error_at   TEXT,
          last_error      TEXT,
          last_run_at     TEXT,
          updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )


def _ensure_mobile_calendar_tables(conn: sqlite3.Connection) -> None:
    if not _column_exists(conn, "gcal_cache", "mc_item_id"):
        conn.execute("ALTER TABLE gcal_cache ADD COLUMN mc_item_id INTEGER REFERENCES items(id)")
    if not _column_exists(conn, "gcal_cache", "mc_kind"):
        conn.execute("ALTER TABLE gcal_cache ADD COLUMN mc_kind TEXT")
    if not _column_exists(conn, "gcal_cache", "mc_last_seen_status"):
        conn.execute("ALTER TABLE gcal_cache ADD COLUMN mc_last_seen_status TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gcal_cache_mc_item ON gcal_cache(mc_item_id)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mobile_sync_actions (
          id             INTEGER PRIMARY KEY AUTOINCREMENT,
          provider       TEXT NOT NULL DEFAULT 'gcal',
          external_id    TEXT NOT NULL,
          item_id        INTEGER REFERENCES items(id) ON DELETE SET NULL,
          action         TEXT NOT NULL CHECK(action IN ('mark_done','mark_waiting','cancel','reschedule','note')),
          title          TEXT NOT NULL,
          old_value      TEXT,
          new_value      TEXT,
          payload        TEXT,
          status         TEXT NOT NULL DEFAULT 'pending'
                         CHECK(status IN ('pending','accepted','rejected')),
          created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
          resolved_at    TEXT,
          UNIQUE(provider, external_id, action, new_value, status)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mobile_sync_actions_status ON mobile_sync_actions(status, created_at)")


def _ensure_organization_profiles_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organization_profiles (
          org_id                INTEGER PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
          purpose               TEXT,
          operating_scope       TEXT,
          stakeholders          TEXT,
          role_title            TEXT,
          role_responsibilities TEXT,
          decision_rights       TEXT,
          role_kpis             TEXT,
          ai_guidance           TEXT,
          constraints           TEXT,
          updated_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )


def _rebuild_item_links_for_external_nodes(conn: sqlite3.Connection) -> None:
    """Recreate item_links when an older CHECK constraint only allows project/item."""
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='item_links'"
    ).fetchone()
    if not sql or "gh_issue" in (sql[0] or ""):
        _ensure_item_links_table(conn)
        return
    conn.execute("ALTER TABLE item_links RENAME TO item_links_old")
    _ensure_item_links_table(conn)
    old_cols = {r[1] for r in conn.execute("PRAGMA table_info(item_links_old)").fetchall()}
    cols = [
        "id", "src_type", "src_id", "dst_type", "dst_id", "relation", "reason", "created_at",
    ]
    cols = [c for c in cols if c in old_cols]
    conn.execute(
        f"INSERT OR IGNORE INTO item_links ({', '.join(cols)}) "
        f"SELECT {', '.join(cols)} FROM item_links_old"
    )
    conn.execute("DROP TABLE item_links_old")


def _migrate_8_to_9(conn: sqlite3.Connection) -> None:
    """v8 -> v9: rename Google OAuth key setting to the actual GCal token key."""
    conn.execute(
        """UPDATE settings
           SET key='keyring_target_gcal_token', value='MC_GCAL_TOKEN'
           WHERE key='keyring_target_google_oauth'"""
    )
    conn.commit()


def _migrate_9_to_10(conn: sqlite3.Connection) -> None:
    """v9 -> v10: allow source='recurrence' on items."""
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("PRAGMA legacy_alter_table=ON")
    conn.execute("ALTER TABLE items RENAME TO items_old")
    conn.execute(
        """
        CREATE TABLE items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            type         TEXT    NOT NULL CHECK(type IN ('schedule','task','memo','project_ref')),
            title        TEXT    NOT NULL,
            body         TEXT,
            body_inline  INTEGER NOT NULL DEFAULT 0,
            status       TEXT    NOT NULL DEFAULT 'todo'
                                 CHECK(status IN ('todo','doing','done','waiting','cancelled')),
            location     TEXT    NOT NULL DEFAULT 'hot'
                                 CHECK(location IN ('hot','cold')),
            scheduled_at TEXT,
            due_at       TEXT,
            start_date   TEXT,
            due_date     TEXT,
            parent_id              INTEGER REFERENCES items(id) ON DELETE CASCADE,
            folder_path            TEXT,
            recurrence_rule        TEXT,
            recurrence_parent_id   INTEGER REFERENCES items(id),
            created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            source       TEXT    NOT NULL DEFAULT 'manual'
                                 CHECK(source IN ('manual','telegram','voice','github','recurrence')),
            cold_path    TEXT
        )
        """
    )
    old_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(items_old)").fetchall()
    }
    new_cols = [
        "id", "type", "title", "body", "body_inline", "status", "location",
        "scheduled_at", "due_at", "start_date", "due_date", "parent_id",
        "folder_path", "recurrence_rule", "recurrence_parent_id",
        "created_at", "updated_at", "source", "cold_path",
    ]
    cols = [col for col in new_cols if col in old_cols]
    conn.execute(
        f"INSERT INTO items ({', '.join(cols)}) SELECT {', '.join(cols)} FROM items_old"
    )
    conn.execute("DROP TABLE items_old")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_items_parent ON items(parent_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_items_status ON items(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_items_scheduled_at ON items(scheduled_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_items_updated_at ON items(updated_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_items_location ON items(location)")
    conn.execute("DROP TRIGGER IF EXISTS items_ai")
    conn.execute("DROP TRIGGER IF EXISTS items_ad")
    conn.execute("DROP TRIGGER IF EXISTS items_au")
    conn.execute(
        """CREATE TRIGGER items_ai AFTER INSERT ON items BEGIN
               INSERT INTO items_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
           END"""
    )
    conn.execute(
        """CREATE TRIGGER items_ad AFTER DELETE ON items BEGIN
               INSERT INTO items_fts(items_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
           END"""
    )
    conn.execute(
        """CREATE TRIGGER items_au AFTER UPDATE ON items BEGIN
               INSERT INTO items_fts(items_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
               INSERT INTO items_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
           END"""
    )
    try:
        conn.execute("INSERT INTO items_fts(items_fts) VALUES ('rebuild')")
    except sqlite3.DatabaseError:
        pass
    conn.commit()
    conn.execute("PRAGMA legacy_alter_table=OFF")
    conn.execute("PRAGMA foreign_keys=ON")


def _migrate_10_to_11(conn: sqlite3.Connection) -> None:
    """v10 -> v11: lightweight relation graph between projects and items."""
    _ensure_item_links_table(conn)
    conn.commit()


def _migrate_11_to_12(conn: sqlite3.Connection) -> None:
    """v11 -> v12: external GitHub/GCal/Drive nodes + sync state."""
    _rebuild_item_links_for_external_nodes(conn)
    _ensure_integration_state_table(conn)
    conn.commit()


def _migrate_12_to_13(conn: sqlite3.Connection) -> None:
    """v12 -> v13: Google Calendar mobile round-trip metadata and review queue."""
    _ensure_mobile_calendar_tables(conn)
    conn.commit()


def _migrate_13_to_14(conn: sqlite3.Connection) -> None:
    """v13 -> v14: organization metadata and role metadata for AI context."""
    _ensure_organization_profiles_table(conn)
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
            current_ver = 8
        if current_ver == 8:
            print("[MIG]   v8 → v9 (normalize Google Calendar secret key setting)")
            _migrate_8_to_9(conn)
            current_ver = 9
        if current_ver == 9:
            print("[MIG]   v9 → v10 (allow recurrence item source)")
            _migrate_9_to_10(conn)
            current_ver = 10
        if current_ver == 10:
            print("[MIG]   v10 -> v11 (lightweight work graph item links)")
            _migrate_10_to_11(conn)
            current_ver = 11
        if current_ver == 11:
            print("[MIG]   v11 -> v12 (external integration graph nodes)")
            _migrate_11_to_12(conn)
            current_ver = 12
        if current_ver == 12:
            print("[MIG]   v12 -> v13 (mobile calendar review queue)")
            _migrate_12_to_13(conn)
            current_ver = 13
        if current_ver == 13:
            print("[MIG]   v13 -> v14 (organization role/profile metadata)")
            _migrate_13_to_14(conn)
        conn.execute(f"PRAGMA user_version = {EXPECTED_VERSION}")
        conn.commit()
        print(f"[OK]    user_version={EXPECTED_VERSION}")
    else:
        print(f"[SKIP]  DB already at version {current_ver}, no changes needed.")

    _ensure_contacts_tables(conn)
    _ensure_item_links_table(conn)
    _ensure_integration_state_table(conn)
    _ensure_mobile_calendar_tables(conn)
    _ensure_organization_profiles_table(conn)
    conn.commit()

    # Verify critical tables
    required = [
        "items", "tags", "item_tags", "projects", "project_stages",
        "organizations", "businesses", "schedules", "labels", "item_labels",
        "gcal_cache", "capture_inbox", "incomplete_reasons",
        "file_index", "settings", "contacts", "item_contacts", "item_links",
        "integration_state", "mobile_sync_actions",
        "organization_profiles",
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
