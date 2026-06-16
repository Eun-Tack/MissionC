"""
Smoke tests for migrate.py and DB layer — TB-M1-01 Done definition.

Covers:
  - Schema application creates all required tables
  - Settings seed is present
  - System labels are seeded
  - items CRUD (insert / update / delete)
  - FTS5 trigger fires on insert
  - FK enforcement works
"""

import sqlite3
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SCHEMA_PATH  = PROJECT_ROOT / "Doc" / "phase4_design" / "schema" / "mc_schema.sql"

REQUIRED_TABLES = [
    "items", "tags", "item_tags", "schedules",
    "projects", "project_stages", "businesses", "organizations",
    "labels", "item_labels",
    "github_cache", "gcal_cache",
    "capture_inbox", "incomplete_reasons",
    "notification_events", "retry_queue",
    "review_memos", "file_index",
    "settings", "item_links", "integration_state", "mobile_sync_actions",
    "organization_profiles",
]

REQUIRED_SETTINGS = [
    "github_cache_interval_min",
    "embedding_model",
    "ai_capability_level",
    "mc_notes_root",
    "gcal_poll_interval_min",
    "tag_normalize_threshold",
    "memo_inbox_default_path",
    "memo_editor",
    "secret_bridge_url",
]


# ─── Schema / migrate tests ───────────────────────────────────────────────────

class TestSchemaMigrate:

    def test_all_required_tables_exist(self, tmp_db: sqlite3.Connection):
        existing = {
            r[0] for r in tmp_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for table in REQUIRED_TABLES:
            assert table in existing, f"Missing table: {table}"

    def test_settings_seed(self, tmp_db: sqlite3.Connection):
        settings = {
            r[0] for r in tmp_db.execute("SELECT key FROM settings").fetchall()
        }
        for key in REQUIRED_SETTINGS:
            assert key in settings, f"Missing setting: {key}"

    def test_system_labels_seeded(self, tmp_db: sqlite3.Connection):
        count = tmp_db.execute(
            "SELECT COUNT(*) FROM labels WHERE type='system'"
        ).fetchone()[0]
        assert count >= 5, f"Expected ≥5 system labels, got {count}"

    def test_migrate_py_idempotent(self, tmp_db_path: Path, monkeypatch):
        """Running migrate twice should not raise."""
        import migrate as m
        monkeypatch.setattr(m, "DB_PATH", tmp_db_path)
        assert m.migrate() is True
        assert m.migrate() is True  # second run: already at version


# ─── Items CRUD ───────────────────────────────────────────────────────────────

class TestItemsCRUD:

    def test_insert_task(self, tmp_db: sqlite3.Connection):
        tmp_db.execute(
            "INSERT INTO items(type, title) VALUES ('task', '테스트 태스크')"
        )
        tmp_db.commit()
        row = tmp_db.execute(
            "SELECT title, status, location FROM items WHERE title='테스트 태스크'"
        ).fetchone()
        assert row is not None
        assert row["status"] == "todo"
        assert row["location"] == "hot"

    def test_item_status_update(self, tmp_db: sqlite3.Connection):
        tmp_db.execute("INSERT INTO items(type, title) VALUES ('task', 'X')")
        tmp_db.commit()
        item_id = tmp_db.execute("SELECT id FROM items WHERE title='X'").fetchone()["id"]
        tmp_db.execute("UPDATE items SET status='done' WHERE id=?", (item_id,))
        tmp_db.commit()
        status = tmp_db.execute(
            "SELECT status FROM items WHERE id=?", (item_id,)
        ).fetchone()["status"]
        assert status == "done"

    def test_item_type_check(self, tmp_db: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            tmp_db.execute(
                "INSERT INTO items(type, title) VALUES ('invalid_type', 'bad')"
            )

    def test_fts5_trigger_on_insert(self, tmp_db: sqlite3.Connection):
        tmp_db.execute(
            "INSERT INTO items(type, title, body, body_inline) "
            "VALUES ('memo', 'NPU 벤치마크', '여기에 메모 내용', 1)"
        )
        tmp_db.commit()
        results = tmp_db.execute(
            "SELECT rowid FROM items_fts WHERE items_fts MATCH 'NPU'"
        ).fetchall()
        assert len(results) >= 1

    def test_cascade_delete_item_tags(self, tmp_db: sqlite3.Connection):
        tmp_db.execute("INSERT INTO items(type, title) VALUES ('task', 'CascadeTest')")
        tmp_db.commit()
        item_id = tmp_db.execute(
            "SELECT id FROM items WHERE title='CascadeTest'"
        ).fetchone()["id"]
        tmp_db.execute("INSERT INTO tags(name) VALUES ('test-tag')")
        tag_id = tmp_db.execute("SELECT id FROM tags WHERE name='test-tag'").fetchone()["id"]
        tmp_db.execute(
            "INSERT INTO item_tags(item_id, tag_id) VALUES (?,?)", (item_id, tag_id)
        )
        tmp_db.commit()
        tmp_db.execute("DELETE FROM items WHERE id=?", (item_id,))
        tmp_db.commit()
        count = tmp_db.execute(
            "SELECT COUNT(*) FROM item_tags WHERE item_id=?", (item_id,)
        ).fetchone()[0]
        assert count == 0


# ─── FK enforcement ───────────────────────────────────────────────────────────

class TestForeignKeys:

    def test_business_requires_existing_org(self, tmp_db: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            tmp_db.execute(
                "INSERT INTO businesses(org_id, name) VALUES (9999, 'no-org')"
            )

    def test_project_stage_cascades_on_project_delete(self, tmp_db: sqlite3.Connection):
        tmp_db.execute("INSERT INTO organizations(name) VALUES ('TestOrg')")
        org_id = tmp_db.execute(
            "SELECT id FROM organizations WHERE name='TestOrg'"
        ).fetchone()["id"]
        tmp_db.execute(
            "INSERT INTO businesses(org_id, name) VALUES (?, 'TestBiz')", (org_id,)
        )
        biz_id = tmp_db.execute(
            "SELECT id FROM businesses WHERE name='TestBiz'"
        ).fetchone()["id"]
        tmp_db.execute(
            "INSERT INTO projects(business_id, title) VALUES (?, 'TestProj')", (biz_id,)
        )
        proj_id = tmp_db.execute(
            "SELECT id FROM projects WHERE title='TestProj'"
        ).fetchone()["id"]
        tmp_db.execute(
            "INSERT INTO project_stages(project_id, name, order_idx) VALUES (?,?,0)",
            (proj_id, "Phase 1"),
        )
        tmp_db.commit()
        tmp_db.execute("DELETE FROM projects WHERE id=?", (proj_id,))
        tmp_db.commit()
        stages = tmp_db.execute(
            "SELECT COUNT(*) FROM project_stages WHERE project_id=?", (proj_id,)
        ).fetchone()[0]
        assert stages == 0
