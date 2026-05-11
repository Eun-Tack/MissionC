"""
SC-02 Search (FR-AI-SEARCH) — FTS5 full-text search.

GET  /search?q=...             — search results page
GET  /partial/search?q=...     — htmx results partial
"""

from __future__ import annotations
import sqlite3
from html import escape
from pathlib import Path

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
        extra_where.append("COALESCE(i.scheduled_at, i.due_date, i.created_at) >= ?")
        params.append(date_from)
    if date_to:
        extra_where.append("COALESCE(i.scheduled_at, i.due_date, i.created_at) <= ?")
        params.append(date_to + "T23:59:59Z")

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


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str = "",
    type_filter: str = "",
    status_filter: str = "",
    project_id: str = "",
    date_from: str = "",
    date_to: str = "",
    db: sqlite3.Connection = Depends(get_db),
):
    pid = int(project_id) if project_id.strip() else None
    has_filter = any([q, type_filter, status_filter, pid, date_from, date_to])
    results = _fts_search(db, q, type_filter=type_filter, status_filter=status_filter,
                          project_id=pid, date_from=date_from, date_to=date_to) if has_filter else []
    projects = [dict(r) for r in db.execute(
        "SELECT id, title FROM projects WHERE status!='archived' ORDER BY title"
    ).fetchall()]
    return templates.TemplateResponse(
        request, "search.html",
        {"q": q, "results": results, "count": len(results),
         "type_filter": type_filter, "status_filter": status_filter,
         "project_id": pid, "date_from": date_from, "date_to": date_to,
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
    db: sqlite3.Connection = Depends(get_db),
):
    pid = int(project_id) if project_id.strip() else None
    has_filter = any([q, type_filter, status_filter, pid, date_from, date_to])
    results = _fts_search(db, q, type_filter=type_filter, status_filter=status_filter,
                          project_id=pid, date_from=date_from, date_to=date_to) if has_filter else []
    return templates.TemplateResponse(
        request, "partials/search_results.html",
        {"q": q, "results": results, "count": len(results),
         "type_filter": type_filter, "status_filter": status_filter},
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
