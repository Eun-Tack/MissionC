"""Lightweight work graph links and closure-flow visualization."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..db import get_db

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

_RELATIONS = {"relates_to", "blocks", "depends_on", "supports", "duplicates", "parent_child"}
_REL_LABELS = {
    "relates_to": "연관",
    "blocks": "막음",
    "depends_on": "의존",
    "supports": "지원",
    "duplicates": "중복",
    "parent_child": "상하위",
}
_STATUS_LABELS = {
    "todo": "예정",
    "doing": "진행",
    "waiting": "대기",
    "done": "완료",
    "cancelled": "취소",
}
_NODE_TYPES = {"project", "item", "gh_issue", "gh_pr", "gcal_event", "drive_file"}


def _label_for(db: sqlite3.Connection, node_type: str, node_id: int) -> str:
    if node_type == "project":
        row = db.execute("SELECT title FROM projects WHERE id=?", (node_id,)).fetchone()
        return row["title"] if row else f"project:{node_id}"
    if node_type == "item":
        row = db.execute("SELECT title FROM items WHERE id=?", (node_id,)).fetchone()
        return row["title"] if row else f"item:{node_id}"
    if node_type in ("gh_issue", "gh_pr"):
        row = db.execute("SELECT number, title FROM github_cache WHERE id=?", (node_id,)).fetchone()
        return f"#{row['number']} {row['title']}" if row else f"{node_type}:{node_id}"
    if node_type == "gcal_event":
        row = db.execute("SELECT title, start_at FROM gcal_cache WHERE id=?", (node_id,)).fetchone()
        return f"{row['title']} ({row['start_at'][:10]})" if row else f"gcal:{node_id}"
    if node_type == "drive_file":
        row = db.execute("SELECT path FROM file_index WHERE rowid=?", (node_id,)).fetchone()
        return Path(row["path"]).name if row else f"file:{node_id}"
    return f"{node_type}:{node_id}"


def _url_for(db: sqlite3.Connection, node_type: str, node_id: int) -> str:
    if node_type == "project":
        return f"/project/{node_id}"
    if node_type == "item":
        return f"/?focus={node_id}"
    if node_type in ("gh_issue", "gh_pr"):
        row = db.execute("SELECT html_url FROM github_cache WHERE id=?", (node_id,)).fetchone()
        return row["html_url"] if row and row["html_url"] else "#"
    if node_type == "gcal_event":
        row = db.execute("SELECT start_at FROM gcal_cache WHERE id=?", (node_id,)).fetchone()
        return f"/calendar?mode=day&date_str={row['start_at'][:10]}" if row else "/calendar"
    if node_type == "drive_file":
        row = db.execute("SELECT path FROM file_index WHERE rowid=?", (node_id,)).fetchone()
        return f"/search?q={row['path']}" if row else "/search"
    return "#"


def _validate_node(db: sqlite3.Connection, node_type: str, node_id: int) -> None:
    if node_type not in _NODE_TYPES:
        raise HTTPException(422, "Invalid node type")
    if node_type == "project":
        exists = db.execute("SELECT 1 FROM projects WHERE id=?", (node_id,)).fetchone()
    elif node_type == "item":
        exists = db.execute("SELECT 1 FROM items WHERE id=?", (node_id,)).fetchone()
    elif node_type == "gh_issue":
        exists = db.execute("SELECT 1 FROM github_cache WHERE id=? AND type='issue'", (node_id,)).fetchone()
    elif node_type == "gh_pr":
        exists = db.execute("SELECT 1 FROM github_cache WHERE id=? AND type='pr'", (node_id,)).fetchone()
    elif node_type == "gcal_event":
        exists = db.execute("SELECT 1 FROM gcal_cache WHERE id=? AND visible=1", (node_id,)).fetchone()
    else:
        exists = db.execute("SELECT 1 FROM file_index WHERE rowid=?", (node_id,)).fetchone()
    if not exists:
        raise HTTPException(404, "Node not found")


def _node_kind_label(node_type: str) -> str:
    return {
        "project": "프로젝트",
        "item": "항목",
        "gh_issue": "GitHub 이슈",
        "gh_pr": "GitHub PR",
        "gcal_event": "캘린더",
        "drive_file": "Drive 파일",
    }.get(node_type, node_type)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _span_days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _node_key(node_type: str, node_id: int) -> str:
    return f"{node_type}:{node_id}"


def _project_choices(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute(
        """
        SELECT p.id, p.title, p.status, p.start_date, p.end_date,
               COUNT(DISTINCT CASE WHEN i.status!='done' AND i.status!='cancelled' THEN i.id END) AS open_count,
               COUNT(DISTINCT CASE WHEN i.status='done' THEN i.id END) AS done_count,
               COUNT(DISTINCT CASE
                   WHEN i.status NOT IN ('done','cancelled')
                    AND COALESCE(i.due_date, substr(i.due_at,1,10), substr(i.scheduled_at,1,10)) < date('now','localtime')
                   THEN i.id END) AS overdue_count,
               COUNT(DISTINCT CASE
                   WHEN i.status NOT IN ('done','cancelled')
                    AND i.updated_at < datetime('now','-3 days')
                   THEN i.id END) AS stale_count
        FROM projects p
        LEFT JOIN item_projects ip ON ip.project_id=p.id
        LEFT JOIN items i ON i.id=ip.item_id
        WHERE p.status!='archived'
        GROUP BY p.id
        ORDER BY overdue_count DESC, stale_count DESC, open_count DESC, p.created_at DESC
        LIMIT 40
        """
    ).fetchall()
    return [dict(r) for r in rows]


def _choose_project(projects: list[dict], project_id: str) -> dict | None:
    if project_id:
        for project in projects:
            if str(project["id"]) == str(project_id):
                return project
    return projects[0] if projects else None


def _project_items(db: sqlite3.Connection, project_id: int, include_done: bool) -> list[dict]:
    done_clause = "" if include_done else "AND i.status!='done'"
    rows = db.execute(
        f"""
        SELECT i.id, i.title, i.type, i.status, i.parent_id, i.start_date, i.due_date,
               i.scheduled_at, i.due_at, i.created_at, i.updated_at,
               parent.title AS parent_title,
               COUNT(DISTINCT child.id) AS sub_total,
               COUNT(DISTINCT CASE WHEN child.status='done' THEN child.id END) AS sub_done
        FROM items i
        JOIN item_projects ip ON ip.item_id=i.id
        LEFT JOIN items parent ON parent.id=i.parent_id
        LEFT JOIN items child ON child.parent_id=i.id AND child.status!='cancelled'
        WHERE ip.project_id=? AND i.status!='cancelled' {done_clause}
        GROUP BY i.id
        ORDER BY COALESCE(i.start_date, substr(i.scheduled_at,1,10), i.created_at),
                 i.parent_id IS NOT NULL, i.parent_id, i.id
        LIMIT 60
        """,
        (project_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _ensure_project_external_links(db: sqlite3.Connection, project_id: int) -> None:
    project = db.execute(
        "SELECT id, title, github_repo, folder_path FROM projects WHERE id=?",
        (project_id,),
    ).fetchone()
    if not project:
        return
    project_title = project["title"] or ""
    if project["github_repo"]:
        gh_rows = db.execute(
            """
            SELECT id, type, number, title, labels, state
            FROM github_cache
            WHERE repo=? AND state='open'
            ORDER BY fetched_at DESC, number DESC
            LIMIT 40
            """,
            (project["github_repo"],),
        ).fetchall()
        for gh in gh_rows:
            labels = (gh["labels"] or "").lower()
            title = (gh["title"] or "").lower()
            is_blocker = any(token in labels or token in title for token in ("block", "blocked", "blocker", "bug", "critical", "urgent"))
            is_pr = gh["type"] == "pr"
            if not is_blocker and not is_pr:
                continue
            dst_type = "gh_pr" if is_pr else "gh_issue"
            relation = "depends_on" if is_pr else "blocks"
            reason = "프로젝트 repo의 열린 PR" if is_pr else "프로젝트 repo의 blocker/bug 이슈"
            db.execute(
                """INSERT OR IGNORE INTO item_links(src_type, src_id, dst_type, dst_id, relation, reason)
                   VALUES ('project', ?, ?, ?, ?, ?)""",
                (project_id, dst_type, gh["id"], relation, reason),
            )

    if project_title:
        like = f"%{project_title}%"
        gcal_rows = db.execute(
            """
            SELECT id, title, start_at
            FROM gcal_cache
            WHERE visible=1
              AND date(start_at) BETWEEN date('now','localtime') AND date('now','localtime','+14 days')
              AND (title LIKE ? OR description LIKE ?)
            ORDER BY start_at ASC
            LIMIT 10
            """,
            (like, like),
        ).fetchall()
        for ev in gcal_rows:
            db.execute(
                """INSERT OR IGNORE INTO item_links(src_type, src_id, dst_type, dst_id, relation, reason)
                   VALUES ('project', ?, 'gcal_event', ?, 'depends_on', ?)""",
                (project_id, ev["id"], "프로젝트명과 일치하는 예정 캘린더 일정"),
            )

    file_rows = db.execute(
        """
        SELECT rowid AS file_id, path
        FROM file_index
        WHERE project_id=? AND state='present'
        ORDER BY last_seen_at DESC
        LIMIT 15
        """,
        (project_id,),
    ).fetchall()
    for f in file_rows:
        db.execute(
            """INSERT OR IGNORE INTO item_links(src_type, src_id, dst_type, dst_id, relation, reason)
               VALUES ('project', ?, 'drive_file', ?, 'supports', ?)""",
            (project_id, f["file_id"], "프로젝트에 연결된 산출물/참고 파일"),
        )


def _timeline_model(project: dict, rows: list[dict], external_edges: list[dict]) -> tuple[list[dict], list[date], dict, list[dict], list[dict]]:
    today = date.today()
    stale_before = datetime.now() - timedelta(days=3)
    starts: list[date] = []
    ends: list[date] = []

    p_start = _parse_date(project.get("start_date"))
    p_end = _parse_date(project.get("end_date"))
    if p_start:
        starts.append(p_start)
    if p_end:
        ends.append(p_end)

    items: list[dict] = []
    for row in rows:
        start = _parse_date(row.get("start_date")) or _parse_date(row.get("scheduled_at")) or _parse_date(row.get("created_at")) or today
        end = _parse_date(row.get("due_date")) or _parse_date(row.get("due_at")) or _parse_date(row.get("scheduled_at")) or start
        if end < start:
            end = start
        starts.append(start)
        ends.append(end)

        due = _parse_date(row.get("due_date")) or _parse_date(row.get("due_at")) or _parse_date(row.get("scheduled_at"))
        updated_raw = row.get("updated_at") or row.get("created_at") or ""
        try:
            updated_at = datetime.fromisoformat(updated_raw.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            updated_at = datetime.now()

        is_stale = row["status"] not in ("done", "cancelled") and updated_at < stale_before
        is_overdue = row["status"] not in ("done", "cancelled") and bool(due and due < today)
        if row["status"] == "done":
            state = "done"
            reason = "완료"
        elif is_overdue:
            state = "overdue"
            reason = "마감 지연"
        elif is_stale:
            state = "stale"
            reason = "3일 이상 정체"
        elif row["status"] == "waiting":
            state = "waiting"
            reason = "대기"
        elif row["status"] == "doing" or start <= today <= end:
            state = "doing"
            reason = "진행 중"
        else:
            state = "todo"
            reason = "예정"

        sub_total = int(row["sub_total"] or 0)
        sub_done = int(row["sub_done"] or 0)
        if sub_total:
            progress = round((sub_done / sub_total) * 100)
        elif row["status"] == "done":
            progress = 100
        elif state == "doing":
            progress = 50
        else:
            progress = 0

        items.append({
            **row,
            "start": start,
            "end": end,
            "due": due,
            "state": state,
            "state_label": reason,
            "status_label": _STATUS_LABELS.get(row["status"], row["status"]),
            "progress": progress,
            "is_subtask": bool(row["parent_id"]),
        })

    range_start = min(starts) if starts else today - timedelta(days=3)
    range_end = max(ends) if ends else today + timedelta(days=10)
    range_start = min(range_start, today - timedelta(days=2))
    range_end = max(range_end, today + timedelta(days=7))
    if (range_end - range_start).days < 10:
        range_end = range_start + timedelta(days=10)
    if (range_end - range_start).days > 90:
        range_end = range_start + timedelta(days=90)

    total_days = max((range_end - range_start).days + 1, 1)
    for item in items:
        left_days = max((item["start"] - range_start).days, 0)
        width_days = max((min(item["end"], range_end) - max(item["start"], range_start)).days + 1, 1)
        item["left_pct"] = round(left_days / total_days * 100, 4)
        item["width_pct"] = round(width_days / total_days * 100, 4)
        item["start_label"] = item["start"].strftime("%m.%d")
        item["end_label"] = item["end"].strftime("%m.%d")
        item["due_label"] = item["due"].strftime("%m.%d") if item["due"] else "-"

    insights = {
        "open": sum(1 for i in items if i["status"] not in ("done", "cancelled")),
        "overdue": sum(1 for i in items if i["state"] == "overdue"),
        "stale": sum(1 for i in items if i["state"] == "stale"),
        "waiting": sum(1 for i in items if i["state"] == "waiting"),
        "external_risk": sum(1 for e in external_edges if e["label"] in ("막음", "의존")),
        "today_due": sum(1 for i in items if i["due"] == today and i["status"] not in ("done", "cancelled")),
        "range_start": range_start.isoformat(),
        "range_end": range_end.isoformat(),
        "today_left_pct": round(max((today - range_start).days, 0) / total_days * 100, 4),
    }
    if insights["overdue"]:
        insights["hint"] = "먼저 지연 항목을 닫거나 연기/취소로 결정해야 합니다."
    elif insights["stale"]:
        insights["hint"] = "정체 항목에 다음 행동이나 담당자를 붙이면 흐름이 살아납니다."
    elif insights["waiting"]:
        insights["hint"] = "대기 사유를 외부 연결로 남기면 병목 원인을 추적할 수 있습니다."
    else:
        insights["hint"] = "현재 흐름은 닫기 가능한 상태입니다. 오늘 마감과 진행 중 항목을 우선 확인하세요."

    bottlenecks = [i for i in items if i["state"] in ("overdue", "stale", "waiting")][:8]
    decision_actions = []
    if insights["overdue"]:
        decision_actions.append({"label": "연기/완료/취소 결정", "text": "마감이 지난 항목은 그대로 두지 말고 날짜를 다시 잡거나 닫습니다."})
    if insights["stale"]:
        decision_actions.append({"label": "다음 행동 지정", "text": "정체 항목에는 다음 행동, 담당자, 또는 대기 사유를 남깁니다."})
    if insights["waiting"] or insights["external_risk"]:
        decision_actions.append({"label": "의존성 확인", "text": "외부 확인이나 선행 작업이 필요한 경우 연결 이유를 갱신합니다."})
    if insights["today_due"]:
        decision_actions.append({"label": "오늘 닫기", "text": "오늘 마감 항목은 완료, 연기, 취소 중 하나로 상태를 확정합니다."})
    if not decision_actions:
        decision_actions.append({"label": "흐름 유지", "text": "큰 병목은 없습니다. 진행 중 항목의 다음 마감만 확인하세요."})
    return items[:40], _span_days(range_start, range_end), insights, bottlenecks, decision_actions


def _external_flow(db: sqlite3.Connection, project_id: int) -> tuple[list[dict], list[dict]]:
    _ensure_project_external_links(db, project_id)
    item_rows = db.execute("SELECT item_id FROM item_projects WHERE project_id=?", (project_id,)).fetchall()
    item_ids = [int(r["item_id"]) for r in item_rows]
    internal = {_node_key("project", project_id), *{_node_key("item", item_id) for item_id in item_ids}}
    rows = db.execute(
        """
        SELECT * FROM item_links
        WHERE (src_type='project' AND src_id=?)
           OR (dst_type='project' AND dst_id=?)
           OR (src_type='item' AND src_id IN (SELECT item_id FROM item_projects WHERE project_id=?))
           OR (dst_type='item' AND dst_id IN (SELECT item_id FROM item_projects WHERE project_id=?))
        ORDER BY created_at DESC, id DESC
        LIMIT 80
        """,
        (project_id, project_id, project_id, project_id),
    ).fetchall()
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    for row in rows:
        src = _node_key(row["src_type"], row["src_id"])
        dst = _node_key(row["dst_type"], row["dst_id"])
        if src not in internal and dst not in internal:
            continue
        for node_type, node_id, key in ((row["src_type"], row["src_id"], src), (row["dst_type"], row["dst_id"], dst)):
            if key not in nodes:
                nodes[key] = {
                    "id": key,
                    "type": node_type,
                    "kind_label": _node_kind_label(node_type),
                    "label": _label_for(db, node_type, node_id),
                    "external": key not in internal,
                }
        edges.append({
            "source": src,
            "target": dst,
            "label": _REL_LABELS.get(row["relation"], row["relation"]),
            "reason": row["reason"] or "",
        })
    ordered_nodes = sorted(nodes.values(), key=lambda n: (not n["external"], n["type"], n["label"]))[:24]
    allowed = {n["id"] for n in ordered_nodes}
    return ordered_nodes, [e for e in edges if e["source"] in allowed and e["target"] in allowed][:40]


def _render_links(db: sqlite3.Connection, node_type: str, node_id: int) -> HTMLResponse:
    rows = db.execute(
        """
        SELECT * FROM item_links
        WHERE (src_type=? AND src_id=?) OR (dst_type=? AND dst_id=?)
        ORDER BY created_at DESC, id DESC
        LIMIT 40
        """,
        (node_type, node_id, node_type, node_id),
    ).fetchall()
    parts = ['<div class="kg-list">']
    if not rows:
        parts.append('<div class="kg-empty">아직 연결된 항목이 없습니다.</div>')
    for r in rows:
        other_type = r["dst_type"] if r["src_type"] == node_type and r["src_id"] == node_id else r["src_type"]
        other_id = r["dst_id"] if other_type == r["dst_type"] else r["src_id"]
        title = escape(_label_for(db, other_type, other_id))
        reason = escape(r["reason"] or "")
        rel = _REL_LABELS.get(r["relation"], r["relation"])
        url = _url_for(db, other_type, other_id)
        parts.append(
            f'<div class="kg-row" id="kg-link-{r["id"]}">'
            f'<a class="kg-title" href="{escape(url)}"><span class="kg-type">{escape(_node_kind_label(other_type))}</span>{title}</a>'
            f'<span class="kg-rel">{escape(rel)}</span>'
            f'<button class="kg-del" hx-delete="/api/links/{r["id"]}" hx-target="#kg-link-{r["id"]}" hx-swap="outerHTML">삭제</button>'
            f'<div class="kg-reason">{reason or "이유 없음"}</div>'
            '</div>'
        )
    parts.append('</div>')
    return HTMLResponse("\n".join(parts))


@router.get("/api/link-search")
async def link_search(q: str = "", scope: str = "all", db: sqlite3.Connection = Depends(get_db)):
    query = f"%{(q or '').strip()}%"
    out: list[dict] = []
    if scope in ("all", "project"):
        rows = db.execute(
            """SELECT p.id, p.title, b.name AS biz_name, o.name AS org_name
               FROM projects p
               LEFT JOIN businesses b ON b.id=p.business_id
               LEFT JOIN organizations o ON o.id=b.org_id
               WHERE p.status!='archived' AND p.title LIKE ?
               ORDER BY p.created_at DESC
               LIMIT 10""",
            (query,),
        ).fetchall()
        out.extend({"type": "project", **dict(r)} for r in rows)
    if scope in ("all", "item", "task", "subtask"):
        where = "i.title LIKE ? AND i.status!='cancelled'"
        params: list = [query]
        if scope == "task":
            where += " AND i.parent_id IS NULL"
        if scope == "subtask":
            where += " AND i.parent_id IS NOT NULL"
        rows = db.execute(
            f"""SELECT i.id, i.title, i.status, i.parent_id,
                       p.id AS project_id, p.title AS project_title,
                       parent.title AS parent_title
                FROM items i
                LEFT JOIN items parent ON parent.id=i.parent_id
                LEFT JOIN item_projects ip ON ip.item_id=i.id
                LEFT JOIN projects p ON p.id=ip.project_id
                WHERE {where}
                ORDER BY i.updated_at DESC
                LIMIT 15""",
            params,
        ).fetchall()
        out.extend({"type": "item", **dict(r)} for r in rows)
    if scope in ("all", "github", "external"):
        rows = db.execute(
            """SELECT id, type, repo, number, title, state, html_url
               FROM github_cache
               WHERE title LIKE ? OR repo LIKE ? OR CAST(number AS TEXT) LIKE ?
               ORDER BY fetched_at DESC, number DESC
               LIMIT 12""",
            (query, query, query),
        ).fetchall()
        for r in rows:
            d = dict(r)
            out.append({
                "type": "gh_pr" if d["type"] == "pr" else "gh_issue",
                "id": d["id"],
                "title": f"{d['repo']} #{d['number']} {d['title']}",
                "status": d["state"],
                "project_title": "GitHub",
            })
    if scope in ("all", "calendar", "external"):
        rows = db.execute(
            """SELECT id, title, start_at, location
               FROM gcal_cache
               WHERE visible=1 AND (title LIKE ? OR description LIKE ? OR location LIKE ?)
               ORDER BY start_at ASC
               LIMIT 12""",
            (query, query, query),
        ).fetchall()
        out.extend({
            "type": "gcal_event",
            "id": r["id"],
            "title": f"{r['start_at'][:10]} {r['title']}",
            "status": "calendar",
            "project_title": "Google Calendar",
        } for r in rows)
    if scope in ("all", "drive", "external"):
        rows = db.execute(
            """SELECT rowid AS id, path, state
               FROM file_index
               WHERE path LIKE ?
               ORDER BY last_seen_at DESC
               LIMIT 12""",
            (query,),
        ).fetchall()
        out.extend({
            "type": "drive_file",
            "id": r["id"],
            "title": r["path"],
            "status": r["state"],
            "project_title": "Drive/File",
        } for r in rows)
    return {"results": out[:20]}


@router.get("/api/link-browser")
async def link_browser(
    kind: str = "business",
    org_id: int | None = None,
    business_id: int | None = None,
    project_id: int | None = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Browsable local work targets for graph linking.

    This intentionally avoids fuzzy search for the local hierarchy:
    organization -> business -> project -> project items.
    """
    if kind == "org":
        rows = db.execute(
            """SELECT o.id, o.name,
                      (SELECT COUNT(*) FROM businesses b WHERE b.org_id=o.id) AS business_count,
                      (SELECT COUNT(*) FROM projects p
                       JOIN businesses b ON b.id=p.business_id
                       WHERE b.org_id=o.id AND p.status!='archived') AS project_count
               FROM organizations o
               WHERE EXISTS (
                   SELECT 1 FROM projects p
                   JOIN businesses b ON b.id=p.business_id
                   WHERE b.org_id=o.id AND p.status!='archived'
               )
               ORDER BY project_count=0, o.name"""
        ).fetchall()
        return {"results": [dict(r) for r in rows]}

    if kind == "business":
        params: list[int] = []
        where = "1=1"
        if org_id is not None:
            where += " AND b.org_id=?"
            params.append(org_id)
        rows = db.execute(
            """SELECT b.id, b.name, o.name AS org_name,
                      (SELECT COUNT(*) FROM projects p
                       WHERE p.business_id=b.id AND p.status!='archived') AS project_count
               FROM businesses b
               LEFT JOIN organizations o ON o.id=b.org_id
               WHERE """ + where + """
               ORDER BY o.name, b.name""",
            params,
        ).fetchall()
        return {"results": [dict(r) for r in rows]}

    if kind == "project":
        params: list[int] = []
        where = "p.status!='archived'"
        if org_id is not None:
            where += " AND o.id=?"
            params.append(org_id)
        if business_id is not None:
            where += " AND p.business_id=?"
            params.append(business_id)
        rows = db.execute(
            f"""SELECT p.id, p.title, p.business_id, b.name AS biz_name, o.name AS org_name,
                       (SELECT COUNT(*) FROM item_projects ip
                        JOIN items i ON i.id=ip.item_id
                        WHERE ip.project_id=p.id AND i.status!='cancelled') AS item_count
                FROM projects p
                LEFT JOIN businesses b ON b.id=p.business_id
                LEFT JOIN organizations o ON o.id=b.org_id
                WHERE {where}
                ORDER BY o.name, b.name, p.title""",
            params,
        ).fetchall()
        return {"results": [dict(r) for r in rows]}

    if kind == "item":
        if project_id is None:
            return {"results": []}
        rows = db.execute(
            """SELECT i.id, i.title, i.status, i.parent_id, parent.title AS parent_title
               FROM item_projects ip
               JOIN items i ON i.id=ip.item_id
               LEFT JOIN items parent ON parent.id=i.parent_id
               WHERE ip.project_id=? AND i.status!='cancelled'
               ORDER BY i.parent_id IS NOT NULL, i.status='done', COALESCE(i.due_at, i.due_date, '9999'), i.created_at""",
            (project_id,),
        ).fetchall()
        return {"results": [dict(r) for r in rows]}

    raise HTTPException(422, "Invalid browser kind")


@router.get("/api/links/{node_type}/{node_id}", response_class=HTMLResponse)
async def list_links(node_type: str, node_id: int, db: sqlite3.Connection = Depends(get_db)):
    _validate_node(db, node_type, node_id)
    return _render_links(db, node_type, node_id)


@router.post("/api/links", response_class=HTMLResponse)
async def create_link(
    src_type: Annotated[str, Form()],
    src_id: Annotated[int, Form()],
    dst_type: Annotated[str, Form()],
    dst_id: Annotated[int, Form()],
    relation: Annotated[str, Form()] = "relates_to",
    reason: Annotated[str, Form()] = "",
    db: sqlite3.Connection = Depends(get_db),
):
    if relation not in _RELATIONS:
        raise HTTPException(422, "Invalid relation")
    reason_clean = " ".join((reason or "").split())[:160]
    if len(reason_clean) < 2:
        raise HTTPException(422, "Reason required")
    _validate_node(db, src_type, src_id)
    _validate_node(db, dst_type, dst_id)
    if src_type == dst_type and src_id == dst_id:
        raise HTTPException(422, "Cannot link a node to itself")
    db.execute(
        """INSERT OR IGNORE INTO item_links(src_type, src_id, dst_type, dst_id, relation, reason)
           VALUES(?,?,?,?,?,?)""",
        (src_type, src_id, dst_type, dst_id, relation, reason_clean),
    )
    return _render_links(db, src_type, src_id)


@router.delete("/api/links/{link_id}", response_class=HTMLResponse)
async def delete_link(link_id: int, db: sqlite3.Connection = Depends(get_db)):
    db.execute("DELETE FROM item_links WHERE id=?", (link_id,))
    return HTMLResponse("")


@router.get("/graph", response_class=HTMLResponse)
async def graph_page(
    request: Request,
    project_id: str = "",
    include_done: str = "",
    db: sqlite3.Connection = Depends(get_db),
):
    projects = _project_choices(db)
    selected_project = _choose_project(projects, project_id)
    if not selected_project:
        return templates.TemplateResponse(
            request,
            "graph.html",
            {
                "projects": [],
                "selected_project": None,
                "items": [],
                "timeline_days": [],
                "insights": {},
                "bottlenecks": [],
                "decision_actions": [],
                "external_nodes": [],
                "external_edges": [],
                "include_done": include_done,
            },
        )

    external_nodes, external_edges = _external_flow(db, int(selected_project["id"]))
    rows = _project_items(db, int(selected_project["id"]), include_done == "1")
    items, timeline_days, insights, bottlenecks, decision_actions = _timeline_model(selected_project, rows, external_edges)
    return templates.TemplateResponse(
        request,
        "graph.html",
        {
            "projects": projects,
            "selected_project": selected_project,
            "items": items,
            "timeline_days": timeline_days,
            "insights": insights,
            "bottlenecks": bottlenecks,
            "decision_actions": decision_actions,
            "external_nodes": external_nodes,
            "external_edges": external_edges,
            "include_done": include_done,
        },
    )
