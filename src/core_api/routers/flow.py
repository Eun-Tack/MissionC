"""
Today's Flow views — SC-01 main screen (FR-FLOW-01~03).

GET  /                      → full page (SC-01)
GET  /partial/flow          → flow list partial (htmx swap)
GET  /partial/context/{id}  → context panel partial (≤500ms, FR-FLOW-03)
"""

from __future__ import annotations
import sqlite3
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ..db import get_db

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Korean weekday names
_KO_WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]
# Korean month/section buckets
_SECTION_LABELS = {
    "morning":   "오전",
    "afternoon": "오후",
    "evening":   "저녁",
    "anytime":   "Anytime",
}


def _today_label() -> tuple[str, str]:
    """Returns (date_korean, weekday_korean)."""
    today = date.today()
    ko = f"{today.year}년 {today.month}월 {today.day}일"
    wd = _KO_WEEKDAY[today.weekday()]
    return ko, wd


def _bucket(start_at: str | None) -> str:
    if not start_at:
        return "anytime"
    try:
        h = int(start_at[11:13])
        if h < 12:
            return "morning"
        if h < 18:
            return "afternoon"
        return "evening"
    except (IndexError, ValueError):
        return "anytime"


def _query_today_items(
    db: sqlite3.Connection,
    org_id: int | None = None,
    tag: str = "",
    unassigned: bool = False,
) -> list[dict]:
    today_str = date.today().isoformat()
    params: list = [today_str]

    org_join = ""
    org_where = ""
    if org_id is not None:
        org_join = (
            "LEFT JOIN item_projects ip2 ON ip2.item_id = i.id "
            "LEFT JOIN projects      p2  ON p2.id = ip2.project_id "
            "LEFT JOIN businesses    b2  ON b2.id = p2.business_id "
        )
        org_where = "AND b2.org_id = ?"
        params.append(org_id)

    tag_join = ""
    tag_where = ""
    if tag:
        tag_join = (
            "JOIN item_tags it2  ON it2.item_id = i.id "
            "JOIN tags      t2   ON t2.id = it2.tag_id AND t2.name = ? "
        )
        params.insert(0, tag)  # tag param comes before today_str — adjust below

    unassigned_join = ""
    unassigned_where = ""
    if unassigned:
        unassigned_join = "LEFT JOIN item_projects ip_unassigned ON ip_unassigned.item_id = i.id "
        unassigned_where = "AND ip_unassigned.item_id IS NULL"

    # rebuild params in correct query order
    params = []
    if tag:
        params.append(tag)
    params.extend([today_str, today_str, today_str, today_str, today_str])
    if org_id is not None:
        params.append(org_id)

    rows = db.execute(
        f"""
        SELECT
            i.id, i.type, i.title, i.body, i.status, i.source,
            i.scheduled_at, i.due_at, i.start_date, i.due_date,
            s.start_at, s.end_at,
            GROUP_CONCAT(DISTINCT t.name)                AS tag_names,
            GROUP_CONCAT(DISTINCT l.name || '|' || l.color) AS label_info,
            fi.evolution_count,
            fi.last_morphed_to,
            gc.title  AS gcal_title
        FROM items i
        LEFT JOIN schedules      s   ON s.item_id  = i.id
        LEFT JOIN item_tags      it  ON it.item_id = i.id
        LEFT JOIN tags           t   ON t.id       = it.tag_id
        LEFT JOIN item_labels    il  ON il.item_id = i.id
        LEFT JOIN labels         l   ON l.id       = il.label_id
        LEFT JOIN gcal_cache     gc  ON gc.gcal_event_id = i.source
            AND gc.visible = 1
        LEFT JOIN file_index     fi  ON fi.item_id = i.id
        {org_join}
        {tag_join}
        {unassigned_join}
        WHERE i.location = 'hot'
          AND i.status NOT IN ('cancelled')
          AND (
              date(COALESCE(s.start_at, i.scheduled_at)) = ?
              OR date(i.due_at) = ?
              OR date(i.due_date) = ?
              OR (date(i.start_date) <= ? AND (i.due_date IS NULL OR date(i.due_date) >= ?))
              OR (i.scheduled_at IS NULL AND s.start_at IS NULL
                  AND i.start_date IS NULL AND i.due_date IS NULL
                  AND i.status NOT IN ('done'))
          )
          {org_where}
          {unassigned_where}
        GROUP BY i.id
        ORDER BY COALESCE(s.start_at, i.scheduled_at) ASC NULLS LAST,
                 i.created_at ASC
        """,
        params,
    ).fetchall()

    items: list[dict] = []
    for r in rows:
        d = dict(r)
        d["tags"] = [t for t in (d["tag_names"] or "").split(",") if t]
        d["labels"] = _parse_labels(d["label_info"])
        effective_start = d.get("start_at") or d.get("scheduled_at") or d.get("due_at")
        d["section"] = _bucket(effective_start)
        d["time_display"] = _fmt_time(effective_start)
        d["due_time_display"] = _fmt_time(d.get("due_at")) if d.get("due_at") else ""
        d["evolution_count"] = d["evolution_count"] or 0
        items.append(d)
    return items


def _parse_labels(raw: str | None) -> list[dict]:
    if not raw:
        return []
    result = []
    for part in raw.split(","):
        if "|" in part:
            name, color = part.split("|", 1)
            result.append({"name": name, "color": color})
    return result


def _fmt_time(start_at: str | None) -> str:
    if not start_at:
        return "—"
    try:
        return start_at[11:16]  # HH:MM
    except IndexError:
        return "—"


def _query_sidebar(db: sqlite3.Connection) -> dict:
    orgs = db.execute(
        """SELECT o.id, o.name, o.color,
                  COUNT(DISTINCT p.id) as project_count
           FROM organizations o
           LEFT JOIN businesses b ON b.org_id = o.id
           LEFT JOIN projects   p ON p.business_id = b.id AND p.status NOT IN ('archived')
           GROUP BY o.id ORDER BY o.name"""
    ).fetchall()

    tags = db.execute(
        """SELECT t.name, COUNT(it.item_id) as cnt
           FROM tags t
           JOIN item_tags it ON it.tag_id = t.id
           JOIN items i ON i.id = it.item_id AND i.location='hot' AND i.status NOT IN ('cancelled')
           GROUP BY t.id ORDER BY cnt DESC LIMIT 12"""
    ).fetchall()

    workers = db.execute(
        "SELECT key, value FROM settings WHERE key LIKE 'worker_status_%'"
    ).fetchall()

    return {
        "organizations": [dict(r) for r in orgs],
        "tags": [dict(r) for r in tags],
        "worker_statuses": {
            r["key"].removeprefix("worker_status_"): r["value"]
            for r in workers
        },
    }


def _build_context(item_id: int, db: sqlite3.Connection) -> dict[str, Any] | None:
    item = db.execute(
        """SELECT i.*, s.start_at, s.end_at
           FROM items i
           LEFT JOIN schedules s ON s.item_id = i.id
           WHERE i.id = ?""",
        (item_id,),
    ).fetchone()
    if not item:
        return None

    ctx: dict[str, Any] = {"item": dict(item)}

    ctx["tags"] = [
        dict(r) for r in db.execute(
            "SELECT t.id, t.name, t.color_hue FROM tags t "
            "JOIN item_tags it ON it.tag_id=t.id WHERE it.item_id=?",
            (item_id,),
        ).fetchall()
    ]
    ctx["labels"] = [
        dict(r) for r in db.execute(
            "SELECT l.id, l.name, l.color FROM labels l "
            "JOIN item_labels il ON il.label_id=l.id WHERE il.item_id=?",
            (item_id,),
        ).fetchall()
    ]
    ctx["project"] = db.execute(
        """SELECT p.id, p.title, p.status, p.start_date, p.end_date, p.github_repo,
                  p.folder_path, b.folder_path AS business_folder_path,
                  b.name AS business_name, o.name AS org_name,
                  (SELECT COUNT(*) FROM item_projects ip2
                   JOIN items i2 ON i2.id=ip2.item_id
                   WHERE ip2.project_id=p.id AND i2.status='done') * 100.0 /
                  NULLIF((SELECT COUNT(*) FROM item_projects ip3
                          WHERE ip3.project_id=p.id), 0) AS progress_pct
           FROM item_projects ip
           JOIN projects     p ON p.id=ip.project_id
           LEFT JOIN businesses b ON b.id=p.business_id
           LEFT JOIN organizations o ON o.id=b.org_id
           WHERE ip.item_id=? LIMIT 1""",
        (item_id,),
    ).fetchone()
    if ctx["project"]:
        ctx["project"] = dict(ctx["project"])

    ctx["memos"] = [
        dict(r) for r in db.execute(
            "SELECT path, evolution_count, last_morphed_to "
            "FROM file_index WHERE item_id=?",
            (item_id,),
        ).fetchall()
    ]
    ctx["github_issues"] = [
        dict(r) for r in db.execute(
            """SELECT gc.number, gc.title, gc.state, gc.html_url
               FROM item_github_links igl
               JOIN github_cache gc ON gc.id=igl.github_cache_id
               WHERE igl.item_id=? LIMIT 5""",
            (item_id,),
        ).fetchall()
    ]
    # All projects (for the project selector dropdown)
    ctx["all_projects"] = [
        dict(r) for r in db.execute(
            """SELECT p.id, p.title, b.name AS biz_name, o.name AS org_name
               FROM projects p
               LEFT JOIN businesses b ON b.id = p.business_id
               LEFT JOIN organizations o ON o.id = b.org_id
               WHERE p.status != 'archived'
               ORDER BY o.name, b.name, p.title"""
        ).fetchall()
    ]
    # All labels (for the label selector)
    ctx["all_labels"] = [
        dict(r) for r in db.execute(
            "SELECT id, name, color FROM labels ORDER BY name"
        ).fetchall()
    ]
    return ctx


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT value FROM settings WHERE key='setup_completed'").fetchone()
    if not row or row[0] != "true":
        return RedirectResponse("/setup", status_code=302)

    items = _query_today_items(db)
    sidebar = _query_sidebar(db)
    date_ko, weekday_ko = _today_label()

    sections: dict[str, list] = {k: [] for k in _SECTION_LABELS}
    for item in items:
        sections[item["section"]].append(item)

    inbox_count = db.execute(
        "SELECT COUNT(*) FROM capture_inbox WHERE status='pending'"
    ).fetchone()[0]

    projects = db.execute(
        """SELECT p.id, p.title, b.name AS biz_name, o.name AS org_name
           FROM projects p
           LEFT JOIN businesses b ON b.id = p.business_id
           LEFT JOIN organizations o ON o.id = b.org_id
           WHERE p.status != 'archived'
           ORDER BY o.name, b.name, p.title"""
    ).fetchall()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "date_korean": date_ko,
            "weekday_korean": weekday_ko,
            "total_items": len(items),
            "unscheduled_count": len(sections["anytime"]),
            "sections": sections,
            "section_labels": _SECTION_LABELS,
            "inbox_count": inbox_count,
            "projects": [dict(p) for p in projects],
            **sidebar,
        },
    )


@router.get("/partial/flow", response_class=HTMLResponse)
async def partial_flow(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    org_id: int | None = None,
    tag: str = "",
    unassigned: int = 0,
):
    items = _query_today_items(db, org_id=org_id, tag=tag, unassigned=bool(unassigned))
    sections: dict[str, list] = {k: [] for k in _SECTION_LABELS}
    for item in items:
        sections[item["section"]].append(item)

    return templates.TemplateResponse(
        request,
        "partials/flow_list.html",
        {
            "sections": sections,
            "section_labels": _SECTION_LABELS,
        },
    )



@router.get("/orphans", response_class=HTMLResponse)
async def orphans_page(request: Request, db: sqlite3.Connection = Depends(get_db)):
    """Page showing all items with no project link — captured but un-triaged."""
    items = db.execute(
        """
        SELECT i.id, i.type, i.title, i.body, i.status, i.scheduled_at, i.created_at,
               GROUP_CONCAT(t.name) AS tag_names
        FROM items i
        LEFT JOIN item_projects ip ON ip.item_id = i.id
        LEFT JOIN item_tags it ON it.item_id = i.id
        LEFT JOIN tags t ON t.id = it.tag_id
        WHERE ip.item_id IS NULL
          AND i.status NOT IN ('cancelled', 'done')
          AND i.location = 'hot'
        GROUP BY i.id
        ORDER BY i.created_at DESC
        """
    ).fetchall()
    items_list = []
    for r in items:
        d = dict(r)
        d["tags"] = [t for t in (d["tag_names"] or "").split(",") if t]
        items_list.append(d)

    projects = db.execute(
        """SELECT p.id, p.title, b.name AS biz_name, o.name AS org_name
           FROM projects p
           LEFT JOIN businesses b ON b.id = p.business_id
           LEFT JOIN organizations o ON o.id = b.org_id
           WHERE p.status != 'archived'
           ORDER BY o.name, b.name, p.title"""
    ).fetchall()

    return templates.TemplateResponse(
        request,
        "orphans.html",
        {
            "items": items_list,
            "projects": [dict(p) for p in projects],
            "count": len(items_list),
        },
    )


@router.get("/partial/context/{item_id}", response_class=HTMLResponse)
async def partial_context(
    request: Request,
    item_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    ctx = _build_context(item_id, db)
    if not ctx:
        return HTMLResponse(
            '<div id="context-panel" class="panel-empty">선택된 항목 없음</div>'
        )
    return templates.TemplateResponse(
        request,
        "partials/context_panel.html",
        ctx,
    )
