"""
API smoke tests for core_api — FR-CAP-01, FR-INBOX-01, FR-AI-SEARCH, FR-BACKUP-01.
Uses FastAPI TestClient with an isolated temp DB injected via dependency override.
"""

from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).parent.parent
SCHEMA_PATH  = PROJECT_ROOT / "Doc" / "phase4_design" / "schema" / "mc_schema.sql"

sys.path.insert(0, str(PROJECT_ROOT / "src"))


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """TestClient backed by a temporary isolated DB with schema + setup_completed."""
    from core_api.main import app
    from core_api.db import get_db

    db_path = tmp_path_factory.mktemp("db") / "test.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    # Mark setup as completed so the root redirect doesn't fire
    conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES ('setup_completed', 'true')")
    conn.commit()

    def _override():
        try:
            yield conn
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
    conn.close()


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ── Items CRUD (FR-CAP-01) ────────────────────────────────────────────────────

class TestItemsAPI:

    def test_create_task(self, client):
        r = client.post("/api/items", data={"title": "API 테스트 태스크", "type": "task"})
        assert r.status_code == 200
        assert "API 테스트 태스크" in r.text

    def test_create_memo(self, client):
        r = client.post("/api/items", data={"title": "메모 아이템", "type": "memo"})
        assert r.status_code == 200

    def test_create_invalid_type(self, client):
        r = client.post("/api/items", data={"title": "bad", "type": "invalid"})
        assert r.status_code == 422

    def test_patch_status(self, client):
        # Create then patch
        client.post("/api/items", data={"title": "Patchable", "type": "task"})
        r = client.get("/api/export")
        items = r.json()["items"]
        iid = next(i["id"] for i in items if i["title"] == "Patchable")
        r2 = client.patch(f"/api/items/{iid}", data={"status": "done"})
        assert r2.status_code == 200
        assert "done" in r2.text

    def test_patch_invalid_status(self, client):
        client.post("/api/items", data={"title": "PatchBad", "type": "task"})
        r = client.get("/api/export")
        items = r.json()["items"]
        iid = items[-1]["id"]
        r2 = client.patch(f"/api/items/{iid}", data={"status": "nonsense"})
        assert r2.status_code == 422

    def test_recurring_completion_spawns_recurrence_source(self, client):
        client.post(
            "/api/items",
            data={
                "title": "RecurringDaily",
                "type": "task",
                "due_date": "2026-05-27",
                "recurrence_rule": "DAILY",
            },
        )
        items = client.get("/api/export").json()["items"]
        iid = next(i["id"] for i in items if i["title"] == "RecurringDaily")

        r = client.patch(f"/api/items/{iid}", data={"status": "done"})
        assert r.status_code == 200

        items = client.get("/api/export").json()["items"]
        spawned = [
            i for i in items
            if i["title"] == "RecurringDaily" and i["recurrence_parent_id"] == iid
        ]
        assert spawned
        assert spawned[-1]["source"] == "recurrence"

    def test_delete_item(self, client):
        client.post("/api/items", data={"title": "ToDelete", "type": "task"})
        r = client.get("/api/export")
        iid = next(i["id"] for i in r.json()["items"] if i["title"] == "ToDelete")
        r2 = client.delete(f"/api/items/{iid}")
        assert r2.status_code == 204

    def test_carry_over(self, client):
        r = client.post("/api/carry-over", data={})
        assert r.status_code == 200
        assert "이월 완료" in r.text


# ── Tags (FR-CAP-02) ──────────────────────────────────────────────────────────

class TestTagsAPI:

    def test_add_tag(self, client):
        client.post("/api/items", data={"title": "Tagable", "type": "task"})
        r = client.get("/api/export")
        iid = next(i["id"] for i in r.json()["items"] if i["title"] == "Tagable")
        r2 = client.post(f"/api/items/{iid}/tags", data={"tag_name": "urgent"})
        assert r2.status_code == 200
        assert "urgent" in r2.text

    def test_add_empty_tag_rejected(self, client):
        client.post("/api/items", data={"title": "EmptyTag", "type": "task"})
        r = client.get("/api/export")
        iid = r.json()["items"][-1]["id"]
        r2 = client.post(f"/api/items/{iid}/tags", data={"tag_name": ""})
        assert r2.status_code == 422


# ── Labels (FR-LABEL-01) ──────────────────────────────────────────────────────

class TestLabelsAPI:

    def test_list_labels(self, client):
        r = client.get("/api/labels")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_add_label_to_item(self, client):
        client.post("/api/items", data={"title": "LabelTest", "type": "task"})
        export = client.get("/api/export").json()
        iid = next(i["id"] for i in export["items"] if i["title"] == "LabelTest")
        labels = client.get("/api/labels").json()
        if labels:
            lid = labels[0]["id"]
            r = client.post(f"/api/items/{iid}/labels", data={"label_id": str(lid)})
            assert r.status_code == 200


# ── Inbox (FR-INBOX-01) ───────────────────────────────────────────────────────

class TestInboxAPI:

    def test_inbox_count(self, client):
        r = client.get("/api/inbox/count")
        assert r.status_code == 200
        assert "count" in r.json()

    def test_add_to_inbox(self, client):
        r = client.post("/api/inbox/add", data={"text": "Inbox test entry"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_inbox_count_increases(self, client):
        before = client.get("/api/inbox/count").json()["count"]
        client.post("/api/inbox/add", data={"text": "Count test"})
        after = client.get("/api/inbox/count").json()["count"]
        assert after == before + 1

    def test_accept_inbox(self, client):
        client.post("/api/inbox/add", data={"text": "Accept test"})
        export = client.get("/api/export").json()
        pending = [i for i in export["capture_inbox"] if i["status"] == "pending"]
        assert pending
        iid = pending[-1]["id"]
        r = client.post(f"/inbox/{iid}/accept", data={"title": "Accepted item"})
        assert r.status_code == 200

    def test_reject_inbox(self, client):
        client.post("/api/inbox/add", data={"text": "Reject test"})
        export = client.get("/api/export").json()
        pending = [i for i in export["capture_inbox"] if i["status"] == "pending"]
        iid = pending[-1]["id"]
        r = client.post(f"/inbox/{iid}/reject", data={})
        assert r.status_code == 200


# ── Search (FR-AI-SEARCH) ─────────────────────────────────────────────────────

class TestSearchAPI:

    def test_search_page_loads(self, client):
        r = client.get("/search")
        assert r.status_code == 200
        assert "search-form" in r.text

    def test_search_with_query(self, client):
        # Insert a searchable item
        client.post("/api/items", data={"title": "FTS5 검색 테스트 아이템", "type": "task"})
        r = client.get("/search?q=FTS5")
        assert r.status_code == 200

    def test_partial_search(self, client):
        r = client.get("/partial/search?q=테스트")
        assert r.status_code == 200

    def test_search_empty_query(self, client):
        r = client.get("/partial/search?q=")
        assert r.status_code == 200
        assert "검색어를 입력하세요" in r.text


# ── Export (FR-BACKUP-01) ─────────────────────────────────────────────────────

class TestExportAPI:

    def test_export_structure(self, client):
        r = client.get("/api/export")
        assert r.status_code == 200
        data = r.json()
        assert "schema_version" in data
        assert data["schema_version"] == 5
        for key in ["items", "projects", "organizations", "capture_inbox"]:
            assert key in data, f"Missing key in export: {key}"


# ── Pages smoke (all must return 200) ────────────────────────────────────────

class TestPageSmoke:

    @pytest.mark.parametrize("path", [
        "/", "/morning", "/evening", "/inbox", "/diag", "/alerts",
        "/search", "/calendar", "/calendar?mode=week",
        "/calendar?mode=month", "/calendar?mode=day",
        "/hierarchy", "/settings",
        "/partial/calendar?mode=week&date_str=2026-05-07",
        "/partial/search?q=",
        "/api/voice/status",
    ])
    def test_page_ok(self, client, path):
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}: {r.text[:200]}"

    def test_calendar_new_event_has_org_project_chain(self, client):
        r = client.get("/calendar")
        assert r.status_code == 200
        assert 'id="ne-org"' in r.text
        assert 'id="ne-business"' in r.text
        assert 'id="ne-project"' in r.text
        assert "NE_BUSINESSES" in r.text
        assert "NE_PROJECTS" in r.text

    def test_voice_status_structure(self, client):
        r = client.get("/api/voice/status")
        assert r.status_code == 200
        d = r.json()
        assert "available" in d
        assert "loaded" in d
        assert "model" in d
