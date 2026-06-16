"""
API smoke tests for core_api — FR-CAP-01, FR-INBOX-01, FR-AI-SEARCH, FR-BACKUP-01.
Uses FastAPI TestClient with an isolated temp DB injected via dependency override.
"""

from __future__ import annotations
from datetime import date, timedelta
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
        "/hierarchy", "/wbs", "/dashboard", "/settings",
        "/partial/calendar?mode=week&date_str=2026-05-07",
        "/partial/search?q=", "/partial/flow?unassigned=1",
        "/api/voice/status",
    ])
    def test_page_ok(self, client, path):
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}: {r.text[:200]}"

    def test_flow_row_context_partial_ok(self, client):
        client.post("/api/items", data={"title": "Context smoke", "type": "task"})
        items = client.get("/api/export").json()["items"]
        iid = next(i["id"] for i in items if i["title"] == "Context smoke")
        r = client.get(f"/partial/context/{iid}")
        assert r.status_code == 200
        assert "Context smoke" in r.text

    def test_context_panel_has_close_edit_delete_actions(self, client):
        client.post("/api/items", data={"title": "Action smoke", "type": "task"})
        items = client.get("/api/export").json()["items"]
        iid = next(i["id"] for i in items if i["title"] == "Action smoke")

        r = client.get(f"/partial/context/{iid}")
        assert r.status_code == 200
        assert "ctx-action-bar" in r.text
        assert "완료" in r.text
        assert "진행" in r.text
        assert "수정" in r.text
        assert "삭제" in r.text
        assert "ctxAfterStatusAction" in r.text
        assert "ctxAfterDelete" in r.text

    def test_context_panel_has_lightweight_graph_links(self, client):
        client.post("/api/items", data={"title": "Graph source", "type": "task"})
        item = next(i for i in client.get("/api/export").json()["items"] if i["title"] == "Graph source")
        r = client.get(f"/partial/context/{item['id']}")
        assert r.status_code == 200
        assert "연관 연결" in r.text
        assert "160자 이하" in r.text
        assert "kg-query" in r.text
        assert "kg-business" in r.text
        assert "kg-org" in r.text
        assert "kg-project" in r.text
        assert "kg-item" in r.text
        assert "proj-org" in r.text
        assert "proj-business" in r.text
        assert "proj-project" in r.text

    def test_item_links_create_list_and_search(self, client):
        client.post("/api/items", data={"title": "Graph source", "type": "task"})
        client.post("/api/items", data={"title": "Graph target", "type": "task"})
        items = client.get("/api/export").json()["items"]
        src = next(i["id"] for i in items if i["title"] == "Graph source")
        dst = next(i["id"] for i in items if i["title"] == "Graph target")

        s = client.get("/api/link-search?q=Graph&scope=task")
        assert s.status_code == 200
        assert any(r["title"] == "Graph target" for r in s.json()["results"])

        r = client.post(
            "/api/links",
            data={
                "src_type": "item",
                "src_id": src,
                "dst_type": "item",
                "dst_id": dst,
                "relation": "depends_on",
                "reason": "마감 판단에 필요",
            },
        )
        assert r.status_code == 200
        assert "Graph target" in r.text
        assert "마감 판단에 필요" in r.text

        g = client.get("/graph")
        assert g.status_code == 200
        assert "닫기 흐름" in g.text

    def test_graph_nav_is_visible(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert 'href="/graph"' in r.text
        assert ">흐름<" in r.text

    def test_link_browser_lists_business_project_and_project_items(self, client):
        client.post("/settings/org", data={"name": "Browser Org", "color": "#6366f1"})
        org_id = next(o["id"] for o in client.get("/api/export").json()["organizations"] if o["name"] == "Browser Org")
        client.post("/api/businesses", data={"name": "Browser Biz", "org_id": org_id})
        biz_id = next(b["id"] for b in client.get("/api/export").json()["businesses"] if b["name"] == "Browser Biz")
        client.post("/api/projects", data={"title": "Browser Project", "business_id": biz_id, "status": "active"})
        proj_id = next(p["id"] for p in client.get("/api/export").json()["projects"] if p["title"] == "Browser Project")
        client.post("/api/items", data={"title": "Browser Task", "type": "task", "project_id": proj_id})

        businesses = client.get("/api/link-browser?kind=business").json()["results"]
        assert any(b["name"] == "Browser Biz" for b in businesses)
        orgs = client.get("/api/link-browser?kind=org").json()["results"]
        assert any(o["name"] == "Browser Org" for o in orgs)

        projects = client.get(f"/api/link-browser?kind=project&business_id={biz_id}").json()["results"]
        assert projects == [p for p in projects if p["business_id"] == biz_id]
        assert any(p["title"] == "Browser Project" for p in projects)

        items = client.get(f"/api/link-browser?kind=item&project_id={proj_id}").json()["results"]
        assert any(i["title"] == "Browser Task" for i in items)

    def test_graph_closure_flow_shows_timeline_and_bottlenecks(self, client):
        client.post("/settings/org", data={"name": "Graph Flow Org", "color": "#6366f1"})
        org_id = next(o["id"] for o in client.get("/api/export").json()["organizations"] if o["name"] == "Graph Flow Org")
        client.post("/api/businesses", data={"name": "Graph Flow Biz", "org_id": org_id})
        biz_id = next(b["id"] for b in client.get("/api/export").json()["businesses"] if b["name"] == "Graph Flow Biz")
        client.post(
            "/api/projects",
            data={
                "title": "Graph Flow Project",
                "business_id": biz_id,
                "status": "active",
                "start_date": "2026-05-25",
                "end_date": "2026-06-05",
            },
        )
        proj_id = next(p["id"] for p in client.get("/api/export").json()["projects"] if p["title"] == "Graph Flow Project")
        client.post(
            "/api/items",
            data={
                "title": "Graph Flow Late Task",
                "type": "task",
                "project_id": proj_id,
                "start_date": "2026-05-25",
                "due_date": "2026-05-26",
            },
        )

        r = client.get(f"/graph?project_id={proj_id}")
        assert r.status_code == 200
        assert "닫기 흐름" in r.text
        assert "Graph Flow Project" in r.text
        assert "Graph Flow Late Task" in r.text
        assert "병목" in r.text
        assert "외부 흐름" in r.text

    def test_external_integration_nodes_can_join_closure_graph(self, client):
        client.post("/settings/org", data={"name": "External Org", "color": "#6366f1"})
        org_id = next(o["id"] for o in client.get("/api/export").json()["organizations"] if o["name"] == "External Org")
        client.post("/api/businesses", data={"name": "External Biz", "org_id": org_id})
        biz_id = next(b["id"] for b in client.get("/api/export").json()["businesses"] if b["name"] == "External Biz")
        client.post(
            "/api/projects",
            data={"title": "External Project", "business_id": biz_id, "status": "active", "github_repo": "iet03/mc"},
        )
        proj_id = next(p["id"] for p in client.get("/api/export").json()["projects"] if p["title"] == "External Project")
        from core_api.db import get_db
        db = next(client.app.dependency_overrides[get_db]())
        db.execute(
            """INSERT INTO github_cache(repo, number, type, title, state, labels, html_url)
               VALUES ('iet03/mc', 77, 'issue', 'blocking bug', 'open', 'blocker,bug', 'https://github.com/iet03/mc/issues/77')"""
        )
        db.commit()
        gh_id = db.execute("SELECT id FROM github_cache WHERE repo='iet03/mc' AND number=77").fetchone()["id"]

        r = client.post(
            "/api/links",
            data={
                "src_type": "project",
                "src_id": proj_id,
                "dst_type": "gh_issue",
                "dst_id": gh_id,
                "relation": "blocks",
                "reason": "닫기 전 확인할 blocker",
            },
        )
        assert r.status_code == 200
        assert "GitHub 이슈" in r.text

        g = client.get(f"/graph?project_id={proj_id}")
        assert g.status_code == 200
        assert "외부 의존" in g.text
        assert "blocking bug" in g.text

    def test_context_panel_done_item_can_reopen(self, client):
        client.post("/api/items", data={"title": "Done action smoke", "type": "task"})
        items = client.get("/api/export").json()["items"]
        iid = next(i["id"] for i in items if i["title"] == "Done action smoke")
        client.patch(f"/api/items/{iid}", data={"status": "done"})

        r = client.get(f"/partial/context/{iid}")
        assert r.status_code == 200
        assert "다시 진행" in r.text
        assert 'hx-vals=\'{"status": "doing"}\'' in r.text

    def test_item_contacts_partial_ok(self, client):
        client.post("/api/items", data={"title": "Contacts smoke", "type": "task"})
        items = client.get("/api/export").json()["items"]
        iid = next(i["id"] for i in items if i["title"] == "Contacts smoke")
        r = client.get(f"/api/items/{iid}/contacts/partial")
        assert r.status_code == 200
        assert f"att-inp-{iid}" in r.text

    def test_context_meta_command_endpoints(self, client):
        client.post("/api/items", data={"title": "Meta smoke", "type": "task"})
        items = client.get("/api/export").json()["items"]
        iid = next(i["id"] for i in items if i["title"] == "Meta smoke")

        r1 = client.post(f"/api/items/{iid}/tags/by-name", data={"name": "rnd"})
        assert r1.status_code == 200
        assert "#rnd" in r1.text

        r2 = client.post(f"/api/items/{iid}/labels/by-name", data={"name": "확인필요"})
        assert r2.status_code == 200
        assert "확인필요" in r2.text

        assert client.request("DELETE", f"/api/items/{iid}/tags/by-name", data={"name": "rnd"}).status_code == 200
        assert client.request("DELETE", f"/api/items/{iid}/labels/by-name", data={"name": "확인필요"}).status_code == 200

    def test_context_existing_label_delete_url_has_id(self, client):
        client.post("/api/items", data={"title": "Label delete smoke", "type": "task"})
        items = client.get("/api/export").json()["items"]
        iid = next(i["id"] for i in items if i["title"] == "Label delete smoke")
        client.post(f"/api/items/{iid}/labels/by-name", data={"name": "삭제테스트"})

        r = client.get(f"/partial/context/{iid}")
        assert r.status_code == 200
        assert f'/api/items/{iid}/labels/' in r.text
        assert f'/api/items/{iid}/labels/"' not in r.text

    def test_wbs_has_week_and_scroll_timeline(self, client):
        client.post("/settings/org", data={"name": "WBS Org", "color": "#6366f1"})
        export = client.get("/api/export").json()
        org_id = next(o["id"] for o in export["organizations"] if o["name"] == "WBS Org")
        client.post("/api/businesses", data={"name": "WBS Biz", "org_id": org_id})
        export = client.get("/api/export").json()
        biz_id = next(b["id"] for b in export["businesses"] if b["name"] == "WBS Biz")
        client.post("/api/projects", data={"title": "WBS Project", "business_id": biz_id, "status": "active"})
        export = client.get("/api/export").json()
        proj_id = next(p["id"] for p in export["projects"] if p["title"] == "WBS Project")
        client.post(
            "/api/items",
            data={
                "title": "Long task",
                "type": "task",
                "project_id": proj_id,
                "start_date": "2026-05-01",
                "due_date": "2026-07-15",
            },
        )

        r = client.get(f"/wbs?proj_id={proj_id}")
        assert r.status_code == 200
        assert "WBS · 작업 분해" in r.text
        assert "프로젝트 날짜 + 작업 날짜 추론" in r.text
        assert "gantt-week" in r.text
        assert "gantt-day" in r.text
        assert "data-left-day" in r.text
        assert "wbsZoomBy" in r.text
        assert "쨌" not in r.text
        assert "??" not in r.text
        assert "timeline_width" not in r.text
        assert "bar_left_px" not in r.text

    def test_calendar_new_event_has_org_project_chain(self, client):
        r = client.get("/calendar")
        assert r.status_code == 200
        assert 'id="ne-org"' in r.text
        assert 'id="ne-business"' in r.text
        assert 'id="ne-project"' in r.text
        assert "NE_BUSINESSES" in r.text
        assert "NE_PROJECTS" in r.text
        assert "소속에 연결하려면 프로젝트까지 선택하세요" not in r.text
        assert "미연결로 저장" in r.text

    def test_calendar_schedule_can_be_saved_without_project_as_orphan(self, client):
        r = client.post(
            "/api/items",
            data={
                "title": "Unknown meeting to classify later",
                "type": "schedule",
                "scheduled_at": "2026-06-01T14:00:00Z",
            },
        )
        assert r.status_code == 200

        export = client.get("/api/export").json()
        item = next(i for i in export["items"] if i["title"] == "Unknown meeting to classify later")
        assert item["type"] == "schedule"
        assert not any(ip["item_id"] == item["id"] for ip in export["item_projects"])

        orphans = client.get("/api/items/orphans").json()
        assert any(o["id"] == item["id"] for o in orphans)

    def test_settings_org_profile_two_axis_metadata(self, client):
        client.post("/settings/org", data={"name": "AI Context Org", "color": "#6366f1"})
        org_id = next(o["id"] for o in client.get("/api/export").json()["organizations"] if o["name"] == "AI Context Org")

        r = client.get("/settings")
        assert r.status_code == 200
        assert "소속 메타데이터" in r.text
        assert "역할 메타데이터" in r.text
        assert f"/settings/org/{org_id}/profile" in r.text

        save = client.patch(
            f"/settings/org/{org_id}/profile",
            data={
                "purpose": "고객 운영 성과를 관리한다",
                "operating_scope": "계약, 일정, 실행, 보고",
                "stakeholders": "고객사, 내부 PM",
                "role_title": "운영 PM",
                "role_responsibilities": "일정 조율과 마감 관리",
                "decision_rights": "일정 우선순위 조정 가능",
                "role_kpis": "응답 24시간 이내, 마감 준수율 95%",
                "ai_guidance": "마감 리스크를 먼저 알려준다",
                "constraints": "고객 확정 전 범위 변경 금지",
            },
        )
        assert save.status_code == 200
        assert "저장됨" in save.text

        export = client.get("/api/export").json()
        profile = next(p for p in export["organization_profiles"] if p["org_id"] == org_id)
        assert profile["purpose"] == "고객 운영 성과를 관리한다"
        assert profile["role_title"] == "운영 PM"
        assert "마감 준수율" in profile["role_kpis"]

    def test_calendar_expands_date_range_task_across_all_days(self, client):
        client.post(
            "/api/items",
            data={
                "title": "Range task visible every day",
                "type": "task",
                "start_date": "2026-05-29",
                "due_date": "2026-06-01",
            },
        )
        items = client.get("/api/export").json()["items"]
        item = next(i for i in items if i["title"] == "Range task visible every day")
        assert item["scheduled_at"] is None

        first_week = client.get("/partial/calendar?mode=week&date_str=2026-05-29")
        assert first_week.status_code == 200
        assert first_week.text.count(f'hx-get="/partial/context/{item["id"]}"') == 3

        next_week = client.get("/partial/calendar?mode=week&date_str=2026-06-01")
        assert next_week.status_code == 200
        assert next_week.text.count(f'hx-get="/partial/context/{item["id"]}"') == 1

    def test_calendar_date_only_task_is_allday_not_timed(self, client):
        client.post(
            "/api/items",
            data={
                "title": "Date only task",
                "type": "task",
                "start_date": "2026-05-29",
            },
        )

        r = client.get("/partial/calendar?mode=day&date_str=2026-05-29")
        assert r.status_code == 200
        assert "Date only task" in r.text
        assert "timed-title\">Date only task" not in r.text

    def test_calendar_week_navigation_normalizes_anchor(self, client):
        r = client.get("/partial/calendar?mode=week&date_str=2026-05-29")
        assert r.status_code == 200
        assert "calSyncToolbar('week', '2026-05-25', '2026-05-18', '2026-06-01'" in r.text

    def test_calendar_uses_js_navigation_state(self, client):
        r = client.get("/calendar?mode=week&date_str=2026-05-29")
        assert r.status_code == 200
        assert "function calStateFor" in r.text
        assert "function calRenderToolbar" in r.text
        assert "onclick=\"calGo('prev')\"" in r.text
        assert "onclick=\"calSetMode('month')\"" in r.text

    def test_calendar_time_grid_supports_drag_create(self, client):
        r = client.get("/partial/calendar?mode=week&date_str=2026-05-29")
        assert r.status_code == 200
        assert "wg-drag-select" in r.text
        assert "wg-hover-cue" in r.text
        page = client.get("/calendar?mode=week&date_str=2026-05-29")
        assert page.status_code == 200
        assert "function openNewEvent(dateStr, timeStr, endTimeStr)" in page.text
        assert "function calInitDragCreate" in page.text
        assert "window._calDragCreateDelegated" in page.text
        assert "드래그" in page.text
        assert "neSetType('schedule'" in page.text
        assert "window.calRefresh" in page.text

    def test_calendar_schedule_time_patch_updates_schedule_join(self, client):
        client.post(
            "/api/items",
            data={
                "title": "Moveable meeting",
                "type": "schedule",
                "scheduled_at": "2026-06-03T09:00:00Z",
            },
        )
        item = next(i for i in client.get("/api/export").json()["items"] if i["title"] == "Moveable meeting")

        r = client.patch(
            f"/api/items/{item['id']}",
            data={"scheduled_at": "2026-06-04T15:30"},
        )
        assert r.status_code == 200

        export = client.get("/api/export").json()
        updated = next(i for i in export["items"] if i["id"] == item["id"])
        schedule = next(s for s in export["schedules"] if s["item_id"] == item["id"])
        assert updated["scheduled_at"] == "2026-06-04T15:30:00Z"
        assert schedule["start_at"] == "2026-06-04T15:30:00Z"

        old_day = client.get("/partial/calendar?mode=day&date_str=2026-06-03")
        new_day = client.get("/partial/calendar?mode=day&date_str=2026-06-04")
        assert "Moveable meeting" not in old_day.text
        assert "Moveable meeting" in new_day.text
        assert "15:30" in new_day.text

    def test_context_schedule_end_time_can_be_patched(self, client):
        client.post(
            "/api/items",
            data={
                "title": "Meeting with editable end",
                "type": "schedule",
                "scheduled_at": "2026-06-03T09:00:00Z",
                "end_at": "2026-06-03T10:00:00Z",
            },
        )
        item = next(i for i in client.get("/api/export").json()["items"] if i["title"] == "Meeting with editable end")

        panel = client.get(f"/partial/context/{item['id']}")
        assert panel.status_code == 200
        assert 'name="end_at"' in panel.text
        assert "2026-06-03T10:00" in panel.text

        r = client.patch(
            f"/api/items/{item['id']}",
            data={"end_at": "2026-06-03T11:30"},
        )
        assert r.status_code == 200

        export = client.get("/api/export").json()
        schedule = next(s for s in export["schedules"] if s["item_id"] == item["id"])
        assert schedule["start_at"] == "2026-06-03T09:00:00Z"
        assert schedule["end_at"] == "2026-06-03T11:30:00Z"

    def test_calendar_context_edits_request_grid_refresh(self, client):
        client.post(
            "/api/items",
            data={
                "title": "Refreshable meeting",
                "type": "schedule",
                "scheduled_at": "2026-06-03T09:00:00Z",
            },
        )
        item = next(i for i in client.get("/api/export").json()["items"] if i["title"] == "Refreshable meeting")

        r = client.get(f"/partial/context/{item['id']}")
        assert r.status_code == 200
        assert "ctxAfterItemChanged" in r.text
        assert 'hx-on::after-request="ctxAfterItemChanged' in r.text

    def test_flow_includes_active_date_range_item(self, client):
        today = date.today()
        client.post(
            "/api/items",
            data={
                "title": "Active range visible in flow",
                "type": "task",
                "start_date": today.isoformat(),
                "due_date": (today + timedelta(days=3)).isoformat(),
            },
        )

        r = client.get("/partial/flow")
        assert r.status_code == 200
        assert "Active range visible in flow" in r.text

    def test_today_quick_create_rules_are_encoded(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "function qsSyncTypeFields" in r.text
        assert "fd.append('start_date', date)" in r.text
        assert "fd.append('due_date', date)" in r.text
        assert "fd.append('due_at', `${date}T${time}:00Z`)" in r.text

    def test_timed_task_uses_due_at_in_today_bucket(self, client):
        today = date.today().isoformat()
        client.post(
            "/api/items",
            data={
                "title": "Timed task in afternoon",
                "type": "task",
                "due_at": f"{today}T14:30:00Z",
            },
        )

        r = client.get("/partial/flow")
        assert r.status_code == 200
        assert "Timed task in afternoon" in r.text
        assert "14:30" in r.text

    def test_due_at_round_trips_and_feeds_closing_dashboard(self, client):
        today = date.today().isoformat()
        client.post(
            "/api/items",
            data={
                "title": "Deadline close queue",
                "type": "task",
                "start_date": today,
                "due_date": today,
                "due_at": f"{today}T17:00:00Z",
            },
        )
        item = next(i for i in client.get("/api/export").json()["items"] if i["title"] == "Deadline close queue")
        assert item["due_at"] == f"{today}T17:00:00Z"

        r = client.get("/dashboard")
        assert r.status_code == 200
        assert "Deadline close queue" in r.text
        assert "닫기 큐" in r.text

    def test_calendar_marks_timed_conflicts(self, client):
        day = "2026-06-02"
        client.post("/api/items", data={"title": "Conflict meeting", "type": "schedule", "scheduled_at": f"{day}T14:00:00Z"})
        client.post("/api/items", data={"title": "Conflict deadline", "type": "task", "due_at": f"{day}T14:30:00Z"})

        r = client.get(f"/partial/calendar?mode=day&date_str={day}")
        assert r.status_code == 200
        assert "has-conflict" in r.text
        assert "Conflict meeting" in r.text
        assert "Conflict deadline" in r.text

    def test_calendar_marks_date_range_task_due_at_conflict(self, client):
        day = "2026-06-02"
        client.post("/api/items", data={"title": "Range task deadline", "type": "task", "start_date": "2026-06-01", "due_date": day, "due_at": f"{day}T14:30:00Z"})
        client.post("/api/items", data={"title": "Meeting near deadline", "type": "schedule", "scheduled_at": f"{day}T14:00:00Z"})

        r = client.get(f"/partial/calendar?mode=day&date_str={day}")
        assert r.status_code == 200
        item = next(i for i in client.get("/api/export").json()["items"] if i["title"] == "Range task deadline")
        assert r.text.count(f'hx-get="/partial/context/{item["id"]}"') == 1
        assert "Meeting near deadline" in r.text

    def test_evening_separates_in_progress_date_range(self, client):
        today = date.today()
        client.post(
            "/api/items",
            data={
                "title": "Range appears as in progress",
                "type": "task",
                "start_date": today.isoformat(),
                "due_date": (today + timedelta(days=2)).isoformat(),
            },
        )

        r = client.get("/evening")
        assert r.status_code == 200
        assert "Range appears as in progress" in r.text

    def test_search_all_filter_lists_existing_items(self, client):
        client.post("/api/items", data={"title": "Search all visible", "type": "task"})

        r = client.get("/search")
        assert r.status_code == 200
        assert "Search all visible" in r.text

    def test_search_scopes_project_task_subtask(self, client):
        client.post("/settings/org", data={"name": "Scope Org", "color": "#6366f1"})
        org_id = next(o["id"] for o in client.get("/api/export").json()["organizations"] if o["name"] == "Scope Org")
        client.post("/api/businesses", data={"name": "Scope Biz", "org_id": org_id})
        biz_id = next(b["id"] for b in client.get("/api/export").json()["businesses"] if b["name"] == "Scope Biz")
        client.post("/api/projects", data={"title": "Scope Project", "business_id": biz_id, "status": "active"})
        proj_id = next(p["id"] for p in client.get("/api/export").json()["projects"] if p["title"] == "Scope Project")
        client.post("/api/items", data={"title": "Scope Task", "type": "task", "project_id": proj_id})
        parent_id = next(i["id"] for i in client.get("/api/export").json()["items"] if i["title"] == "Scope Task")
        client.post(f"/api/items/{parent_id}/subtasks", data={"title": "Scope Subtask"})

        project = client.get("/search?q=Scope&scope=project")
        assert project.status_code == 200
        assert "연결 할 일" in project.text
        task = client.get("/search?q=Scope&scope=task")
        assert task.status_code == 200
        assert "Scope Subtask" in task.text
        subtask = client.get("/search?q=Scope&scope=subtask")
        assert subtask.status_code == 200
        assert "상위 할 일" in subtask.text

    def test_subtask_due_extends_parent_due_date(self, client):
        client.post(
            "/api/items",
            data={"title": "Parent date bounds", "type": "task", "due_date": "2026-06-08"},
        )
        items = client.get("/api/export").json()["items"]
        parent_id = next(i["id"] for i in items if i["title"] == "Parent date bounds")

        r = client.post(
            f"/api/items/{parent_id}/subtasks",
            data={"title": "Child outside parent", "due_date": "2026-06-09"},
        )
        assert r.status_code == 200

        items = client.get("/api/export").json()["items"]
        parent = next(i for i in items if i["id"] == parent_id)
        assert parent["due_date"] == "2026-06-09"

    def test_subtask_partial_supports_detailed_editing(self, client):
        client.post("/api/items", data={"title": "Detailed sub parent", "type": "task"})
        items = client.get("/api/export").json()["items"]
        parent_id = next(i["id"] for i in items if i["title"] == "Detailed sub parent")

        r = client.post(
            f"/api/items/{parent_id}/subtasks",
            data={
                "title": "Detailed child",
                "start_date": "2026-06-01",
                "due_date": "2026-06-03",
                "due_at": "2026-06-03T17:30",
                "assignee_name": "Alice",
                "body": "Finish criteria",
            },
        )
        assert r.status_code == 200
        assert "sub-title-input" in r.text
        assert "sub-status-select" in r.text
        assert 'name="start_date"' in r.text
        assert 'name="due_at"' in r.text
        assert "2026-06-03T17:30" in r.text

        child = next(i for i in client.get("/api/export").json()["items"] if i["title"] == "Detailed child")
        assert child["start_date"] == "2026-06-01"
        assert child["due_date"] == "2026-06-03"
        assert child["due_at"] == "2026-06-03T17:30:00Z"
        assert child["body"] == "Finish criteria"

        contacts = client.get(f"/api/items/{child['id']}/contacts").json()
        assert contacts[0]["name"] == "Alice"
        assert contacts[0]["role"] == "assignee"

    def test_context_subtask_creation_uses_modal(self, client):
        client.post("/api/items", data={"title": "Sub modal parent", "type": "task"})
        items = client.get("/api/export").json()["items"]
        parent_id = next(i["id"] for i in items if i["title"] == "Sub modal parent")

        r = client.get(f"/partial/context/{parent_id}")
        assert r.status_code == 200
        assert "sub-modal-backdrop" in r.text
        assert "하위 작업 생성" in r.text
        assert 'name="assignee_name"' in r.text
        assert 'name="body"' in r.text
        assert "sub-add-row" in r.text

    def test_subtask_partial_exposes_completion_delay_cancel_states(self, client):
        client.post("/api/items", data={"title": "Sub state parent", "type": "task"})
        parent_id = next(i["id"] for i in client.get("/api/export").json()["items"] if i["title"] == "Sub state parent")
        client.post(
            f"/api/items/{parent_id}/subtasks",
            data={"title": "Late child", "due_date": "2026-01-01"},
        )

        r = client.get(f"/api/items/{parent_id}/subtasks")
        assert r.status_code == 200
        assert "완료" in r.text
        assert "지연" in r.text
        assert "취소" in r.text

    def test_exact_duplicate_item_create_returns_existing_item(self, client):
        payload = {
            "title": "Duplicate guard",
            "type": "task",
            "start_date": "2026-05-30",
            "due_date": "2026-05-30",
            "scheduled_at": "2026-05-30T09:00:00Z",
        }
        client.post("/api/items", data=payload)
        client.post("/api/items", data=payload)
        items = [i for i in client.get("/api/export").json()["items"] if i["title"] == "Duplicate guard"]
        assert len(items) == 1

    def test_schedule_duplicate_normalizes_datetime_and_updates_end(self, client):
        client.post(
            "/api/items",
            data={
                "title": "Normalized duplicate meeting",
                "type": "schedule",
                "scheduled_at": "2026-06-10T09:00",
                "end_at": "2026-06-10T10:00",
            },
        )
        client.post(
            "/api/items",
            data={
                "title": "Normalized duplicate meeting",
                "type": "schedule",
                "scheduled_at": "2026-06-10T09:00:00Z",
                "end_at": "2026-06-10T10:30",
            },
        )
        export = client.get("/api/export").json()
        items = [i for i in export["items"] if i["title"] == "Normalized duplicate meeting"]
        assert len(items) == 1
        schedule = next(s for s in export["schedules"] if s["item_id"] == items[0]["id"])
        assert schedule["start_at"] == "2026-06-10T09:00:00Z"
        assert schedule["end_at"] == "2026-06-10T10:30:00Z"

    def test_wbs_includes_due_at_only_task_dates(self, client):
        client.post("/settings/org", data={"name": "DueAt Org", "color": "#6366f1"})
        org_id = next(o["id"] for o in client.get("/api/export").json()["organizations"] if o["name"] == "DueAt Org")
        client.post("/api/businesses", data={"name": "DueAt Biz", "org_id": org_id})
        biz_id = next(b["id"] for b in client.get("/api/export").json()["businesses"] if b["name"] == "DueAt Biz")
        client.post("/api/projects", data={"title": "DueAt Project", "business_id": biz_id, "status": "active"})
        proj_id = next(p["id"] for p in client.get("/api/export").json()["projects"] if p["title"] == "DueAt Project")
        client.post("/api/items", data={"title": "DueAt only task", "type": "task", "project_id": proj_id, "due_at": "2026-06-10T17:00"})

        r = client.get(f"/wbs?proj_id={proj_id}")
        assert r.status_code == 200
        assert "DueAt only task" in r.text
        assert "2026-06-10" in r.text

    def test_subtask_due_at_extends_parent_due_date(self, client):
        client.post("/api/items", data={"title": "Parent due at bounds", "type": "task", "due_date": "2026-06-08"})
        items = client.get("/api/export").json()["items"]
        parent_id = next(i["id"] for i in items if i["title"] == "Parent due at bounds")

        r = client.post(
            f"/api/items/{parent_id}/subtasks",
            data={"title": "Child timed outside parent", "due_at": "2026-06-09T09:00"},
        )
        assert r.status_code == 200

        parent = next(i for i in client.get("/api/export").json()["items"] if i["id"] == parent_id)
        assert parent["due_date"] == "2026-06-09"

    def test_voice_status_structure(self, client):
        r = client.get("/api/voice/status")
        assert r.status_code == 200
        d = r.json()
        assert "available" in d
        assert "loaded" in d
        assert "model" in d

    def test_mobile_sync_action_accept_marks_item_done(self, client):
        client.post("/api/items", data={"title": "Mobile done candidate", "type": "task"})
        item = next(i for i in client.get("/api/export").json()["items"] if i["title"] == "Mobile done candidate")
        from core_api.db import get_db
        db = next(client.app.dependency_overrides[get_db]())
        cur = db.execute(
            """INSERT INTO mobile_sync_actions
               (external_id, item_id, action, title, old_value, new_value)
               VALUES ('evt-mobile-1', ?, 'mark_done', 'Mobile done candidate 완료', 'todo', 'done')""",
            (item["id"],),
        )
        action_id = cur.lastrowid
        db.commit()

        r = client.post(f"/api/mobile-sync-actions/{action_id}/accept")
        assert r.status_code == 204
        updated = next(i for i in client.get("/api/export").json()["items"] if i["id"] == item["id"])
        assert updated["status"] == "done"
