"""
SC-02 Search (FR-AI-SEARCH) — FTS5 full-text search.

GET  /search?q=...             — search results page
GET  /partial/search?q=...     — htmx results partial
"""

from __future__ import annotations
import sqlite3
from html import escape
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..db import get_db

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

def _safe_snippet(raw: str) -> str:
    """Escape HTML from FTS5 snippet, then restore only <mark> tags."""
    escaped = escape(raw)
    return escaped.replace("&lt;mark&gt;", "<mark>").replace("&lt;/mark&gt;", "</mark>")


_STATUS_ICON = {
    "todo": "☐", "in_progress": "●", "doing": "●",
    "done": "✓", "waiting": "⏸", "cancelled": "✕",
}
_STATUS_KO = {
    "todo": "할 일", "in_progress": "진행중", "doing": "진행중",
    "done": "완료", "waiting": "대기", "cancelled": "취소",
}


def _fts_search(
    db: sqlite3.Connection,
    query: str,
    limit: int = 50,
    type_filter: str = "",
    status_filter: str = "",
    project_id: int | None = None,
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    q = (query or "").strip()
    safe_q = q.replace('"', '""')

    # Build filter clauses
    extra_where: list[str] = ["i.status != 'cancelled'"]
    params: list = []

    if type_filter:
        extra_where.append("i.type = ?")
        params.append(type_filter)
    if status_filter:
        if status_filter == "doing":
            extra_where.append("i.status IN ('doing', 'in_progress')")
        else:
            extra_where.append("i.status = ?")
            params.append(status_filter)
    if project_id:
        extra_where.append(
            "EXISTS(SELECT 1 FROM item_projects ip WHERE ip.item_id=i.id AND ip.project_id=?)"
        )
        params.append(project_id)
    if date_from:
        extra_where.append(
            "date(COALESCE(i.due_date, i.scheduled_at, i.start_date, i.created_at)) >= ?"
        )
        params.append(date_from)
    if date_to:
        extra_where.append(
            "date(COALESCE(i.start_date, i.scheduled_at, i.due_date, i.created_at)) <= ?"
        )
        params.append(date_to)

    where_sql = " AND ".join(extra_where)

    rows = []
    if q:
        try:
            fts_params = [f'"{safe_q}"*'] + params + [limit]
            rows = db.execute(
                f"""SELECT i.id, i.title, i.type, i.status, i.scheduled_at, i.due_date,
                          snippet(items_fts, 1, '<mark>', '</mark>', '…', 20) AS snippet
                   FROM items_fts
                   JOIN items i ON i.id = items_fts.rowid
                   WHERE items_fts MATCH ? AND {where_sql}
                   ORDER BY rank
                   LIMIT ?""",
                fts_params,
            ).fetchall()
        except Exception:
            like_params = [f"%{q}%", f"%{q}%"] + params + [limit]
            rows = db.execute(
                f"""SELECT i.id, i.title, i.type, i.status, i.scheduled_at, i.due_date,
                          i.title AS snippet
                   FROM items i
                   WHERE (i.title LIKE ? OR i.body LIKE ?) AND {where_sql}
                   ORDER BY i.created_at DESC LIMIT ?""",
                like_params,
            ).fetchall()
    elif extra_where:
        # Filter-only mode (no text query)
        filter_params = params + [limit]
        rows = db.execute(
            f"""SELECT i.id, i.title, i.type, i.status, i.scheduled_at, i.due_date,
                      i.title AS snippet
               FROM items i
               WHERE {where_sql}
               ORDER BY COALESCE(i.scheduled_at, i.due_date, i.created_at) DESC LIMIT ?""",
            filter_params,
        ).fetchall()

    results = []
    for r in rows:
        d = dict(r)
        d["status_icon"] = _STATUS_ICON.get(d["status"], "?")
        d["status_ko"]   = _STATUS_KO.get(d["status"], d["status"])
        if d.get("snippet"):
            d["snippet"] = _safe_snippet(d["snippet"])
        results.append(d)
    return results


def _hierarchical_search(db: sqlite3.Connection, q: str, scope: str, limit: int = 40) -> list[dict]:
    like = f"%{(q or '').strip()}%"
    if scope == "project":
        rows = db.execute(
            """SELECT p.id, p.title, p.status,
                      (SELECT COUNT(*) FROM item_projects ip JOIN items i ON i.id=ip.item_id
                       WHERE ip.project_id=p.id AND i.status!='cancelled') AS item_count,
                      (SELECT GROUP_CONCAT(i.title, ' · ') FROM (
                         SELECT i.title FROM item_projects ip JOIN items i ON i.id=ip.item_id
                         WHERE ip.project_id=p.id AND i.status!='cancelled' ORDER BY i.updated_at DESC LIMIT 4
                       ) i) AS child_summary
               FROM projects p
               WHERE p.status!='archived' AND p.title LIKE ?
               ORDER BY p.created_at DESC
               LIMIT ?""",
            (like, limit),
        ).fetchall()
        return [{**dict(r), "scope": "project", "url": f"/project/{r['id']}"} for r in rows]
    if scope == "subtask":
        rows = db.execute(
            """SELECT i.id, i.title, i.status, parent.title AS parent_title, p.title AS project_title
               FROM items i
               LEFT JOIN items parent ON parent.id=i.parent_id
               LEFT JOIN item_projects ip ON ip.item_id=i.id
               LEFT JOIN projects p ON p.id=ip.project_id
               WHERE i.status!='cancelled' AND i.parent_id IS NOT NULL AND i.title LIKE ?
               ORDER BY i.updated_at DESC LIMIT ?""",
            (like, limit),
        ).fetchall()
        return [{**dict(r), "scope": "subtask", "url": f"/?focus={r['id']}"} for r in rows]
    rows = db.execute(
        """SELECT i.id, i.title, i.status, p.title AS project_title,
                  (SELECT GROUP_CONCAT(c.title, ' · ') FROM (
                     SELECT c.title FROM items c
                     WHERE c.parent_id=i.id AND c.status!='cancelled' ORDER BY c.updated_at DESC LIMIT 4
                   ) c) AS child_summary
           FROM items i
           LEFT JOIN item_projects ip ON ip.item_id=i.id
           LEFT JOIN projects p ON p.id=ip.project_id
           WHERE i.status!='cancelled' AND i.parent_id IS NULL AND i.title LIKE ?
           ORDER BY i.updated_at DESC LIMIT ?""",
        (like, limit),
    ).fetchall()
    return [{**dict(r), "scope": "task", "url": f"/?focus={r['id']}"} for r in rows]


def _external_search(db: sqlite3.Connection, q: str, scope: str, limit: int = 40) -> list[dict]:
    query = (q or "").strip()
    like = f"%{query}%"
    out: list[dict] = []

    if scope in ("external", "github"):
        where = "WHERE title LIKE ? OR repo LIKE ? OR CAST(number AS TEXT) LIKE ?"
        params: list = [like, like, like]
        if not query:
            where = ""
            params = []
        rows = db.execute(
            f"""SELECT id, repo, number, type, title, state, labels, html_url, fetched_at
                FROM github_cache
                {where}
                ORDER BY fetched_at DESC, state='open' DESC, number DESC
                LIMIT ?""",
            [*params, limit],
        ).fetchall()
        for r in rows:
            d = dict(r)
            kind = "GitHub PR" if d["type"] == "pr" else "GitHub 이슈"
            out.append({
                "id": d["id"],
                "scope": "github",
                "type": "gh_pr" if d["type"] == "pr" else "gh_issue",
                "title": f"{d['repo']} #{d['number']} {d['title']}",
                "status": d["state"] or "",
                "status_ko": kind,
                "project_title": d["labels"] or d["repo"],
                "snippet": "",
                "url": d["html_url"] or "#",
                "external_url": d["html_url"] or "",
            })

    if scope in ("external", "calendar"):
        where = "WHERE visible=1 AND (title LIKE ? OR description LIKE ? OR location LIKE ?)"
        params = [like, like, like]
        if not query:
            where = "WHERE visible=1"
            params = []
        rows = db.execute(
            f"""SELECT id, title, start_at, end_at, location, description
                FROM gcal_cache
                {where}
                ORDER BY start_at ASC
                LIMIT ?""",
            [*params, limit],
        ).fetchall()
        for r in rows:
            d = dict(r)
            day = (d["start_at"] or "")[:10]
            out.append({
                "id": d["id"],
                "scope": "calendar",
                "type": "gcal_event",
                "title": d["title"],
                "status": day,
                "status_ko": "캘린더",
                "project_title": d["location"] or "",
                "snippet": d["description"] or "",
                "scheduled_at": d["start_at"],
                "url": f"/calendar?mode=day&date_str={day}" if day else "/calendar",
            })

    if scope in ("external", "drive"):
        where = "WHERE path LIKE ?"
        params = [like]
        if not query:
            where = ""
            params = []
        rows = db.execute(
            f"""SELECT rowid AS id, path, state, project_id, item_id, last_seen_at
                FROM file_index
                {where}
                ORDER BY last_seen_at DESC
                LIMIT ?""",
            [*params, limit],
        ).fetchall()
        for r in rows:
            d = dict(r)
            path = d["path"] or ""
            out.append({
                "id": d["id"],
                "scope": "drive",
                "type": "drive_file",
                "title": Path(path).name or path,
                "status": d["state"] or "",
                "status_ko": "Drive/파일",
                "project_title": str(Path(path).parent) if path else "",
                "snippet": path,
                "url": "#",
                "file_path": path,
                "open_url": f"/api/folder-open?path={quote(path)}" if path else "",
            })

    return out[:limit]


def _search_results(
    db: sqlite3.Connection,
    q: str,
    scope: str,
    type_filter: str = "",
    status_filter: str = "",
    project_id: int | None = None,
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    if scope in ("project", "task", "subtask"):
        return _hierarchical_search(db, q, scope)
    if scope in ("github", "calendar", "drive", "external"):
        return _external_search(db, q, scope)
    internal = _fts_search(
        db,
        q,
        type_filter=type_filter,
        status_filter=status_filter,
        project_id=project_id,
        date_from=date_from,
        date_to=date_to,
    )
    if (q or "").strip():
        return [*internal, *_external_search(db, q, "external", limit=20)][:60]
    return internal


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str = "",
    type_filter: str = "",
    status_filter: str = "",
    project_id: str = "",
    date_from: str = "",
    date_to: str = "",
    scope: str = "all",
    db: sqlite3.Connection = Depends(get_db),
):
    pid = int(project_id) if project_id.strip() else None
    results = _search_results(
        db, q, scope, type_filter=type_filter, status_filter=status_filter,
        project_id=pid, date_from=date_from, date_to=date_to
    )
    projects = [dict(r) for r in db.execute(
        "SELECT id, title FROM projects WHERE status!='archived' ORDER BY title"
    ).fetchall()]
    return templates.TemplateResponse(
        request, "search.html",
        {"q": q, "results": results, "count": len(results),
         "type_filter": type_filter, "status_filter": status_filter,
         "project_id": pid, "date_from": date_from, "date_to": date_to, "scope": scope,
         "projects": projects},
    )


@router.get("/partial/search", response_class=HTMLResponse)
async def search_partial(
    request: Request,
    q: str = "",
    type_filter: str = "",
    status_filter: str = "",
    project_id: str = "",
    date_from: str = "",
    date_to: str = "",
    scope: str = "all",
    db: sqlite3.Connection = Depends(get_db),
):
    pid = int(project_id) if project_id.strip() else None
    has_filter = any([q, type_filter, status_filter, pid, date_from, date_to, scope != "all"])
    results = _search_results(
        db, q, scope, type_filter=type_filter, status_filter=status_filter,
        project_id=pid, date_from=date_from, date_to=date_to
    ) if has_filter else []
    return templates.TemplateResponse(
        request, "partials/search_results.html",
        {"q": q, "results": results, "count": len(results),
         "type_filter": type_filter, "status_filter": status_filter, "scope": scope},
    )


@router.get("/api/cmdk")
async def cmdk_search(q: str = "", db: sqlite3.Connection = Depends(get_db)):
    """JSON endpoint for Command Palette — searches items + projects."""
    out: list[dict] = []
    qs = (q or "").strip()
    if not qs:
        return {"results": []}

    items = _fts_search(db, qs, limit=8)
    for it in items:
        out.append({
            "kind": "item",
            "id": it["id"],
            "title": it["title"],
            "subtitle": f'{_STATUS_KO.get(it["status"], it["status"])} · {it["type"]}',
            "icon": _STATUS_ICON.get(it["status"], "?"),
            "url": f"/?focus={it['id']}",
        })

    projs = db.execute(
        """SELECT p.id, p.title, b.name AS biz, o.name AS org
           FROM projects p
           LEFT JOIN businesses b ON b.id = p.business_id
           LEFT JOIN organizations o ON o.id = b.org_id
           WHERE p.title LIKE ? AND p.status != 'archived'
           LIMIT 5""",
        (f"%{qs}%",),
    ).fetchall()
    for p in projs:
        out.append({
            "kind": "project",
            "id": p["id"],
            "title": p["title"],
            "subtitle": " / ".join(filter(None, [p["org"], p["biz"]])) or "프로젝트",
            "icon": "📂",
            "url": f"/project/{p['id']}",
        })

    return {"results": out}
