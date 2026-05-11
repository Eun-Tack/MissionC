"""
SC-15 WBS (Work Breakdown Structure) view — read-only Gantt-style timeline.
GET /wbs               — pick a business or project
GET /wbs?biz_id=N      — show all projects+tasks under business N as Gantt
GET /wbs?proj_id=N     — show one project's tasks+subtasks as Gantt
"""

from __future__ import annotations
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..db import get_db

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        return None


def _date_range(rows: list[dict]) -> tuple[date, date]:
    """Compute min/max date across all rows; returns (start, end). Defaults to ±1 month."""
    today = date.today()
    starts, ends = [], []
    for r in rows:
        s = _parse_date(r.get("start_date") or r.get("scheduled_at"))
        e = _parse_date(r.get("end_date") or r.get("due_date") or r.get("scheduled_at"))
        if s: starts.append(s)
        if e: ends.append(e)
    start = min(starts) if starts else today - timedelta(days=14)
    end = max(ends) if ends else today + timedelta(days=60)
    # add some padding
    start = start - timedelta(days=2)
    end = end + timedelta(days=7)
    return start, end


def _bar_offset_pct(item_start: date | None, item_end: date | None,
                    range_start: date, range_end: date) -> tuple[float, float]:
    """Returns (left_pct, width_pct) for a bar. None values fall back to today as point."""
    today = date.today()
    s = item_start or item_end or today
    e = item_end or item_start or today
    if e < s:
        s, e = e, s
    total = (range_end - range_start).days or 1
    left = max(0.0, (s - range_start).days / total * 100)
    width = max(1.5, ((e - s).days + 1) / total * 100)  # min 1.5% so even 1-day bars show
    return left, width


def _load_project_rows(db: sqlite3.Connection, project_id: int) -> tuple[dict, list[dict]]:
    """Return (project_dict, list_of_task_rows_with_children)."""
    proj = db.execute(
        """SELECT p.id, p.title, p.status, p.start_date, p.end_date,
                  b.name AS biz_name, o.name AS org_name
           FROM projects p
           LEFT JOIN businesses b ON b.id = p.business_id
           LEFT JOIN organizations o ON o.id = b.org_id
           WHERE p.id = ?""",
        (project_id,),
    ).fetchone()
    if not proj:
        return None, []
    proj_d = dict(proj)

    # Top-level tasks under this project
    top = db.execute(
        """SELECT i.id, i.title, i.status, i.start_date, i.due_date, i.scheduled_at
           FROM items i
           JOIN item_projects ip ON ip.item_id = i.id
           WHERE ip.project_id = ?
             AND i.status != 'cancelled'
             AND i.parent_id IS NULL
           ORDER BY COALESCE(i.start_date, i.due_date, i.scheduled_at, '9999')""",
        (project_id,),
    ).fetchall()

    rows = []
    for t in top:
        td = dict(t)
        td["depth"] = 1
        td["kind"] = "task"
        rows.append(td)
        # children
        children = db.execute(
            """SELECT id, title, status, start_date, due_date, scheduled_at
               FROM items WHERE parent_id = ? AND status != 'cancelled'
               ORDER BY COALESCE(start_date, due_date, scheduled_at, '9999')""",
            (td["id"],),
        ).fetchall()
        for c in children:
            cd = dict(c)
            cd["depth"] = 2
            cd["kind"] = "subtask"
            rows.append(cd)
    return proj_d, rows


def _load_business_rows(db: sqlite3.Connection, biz_id: int) -> tuple[dict, list[dict]]:
    biz = db.execute(
        """SELECT b.id, b.name AS title, b.description, o.name AS org_name
           FROM businesses b LEFT JOIN organizations o ON o.id = b.org_id
           WHERE b.id = ?""",
        (biz_id,),
    ).fetchone()
    if not biz:
        return None, []
    biz_d = dict(biz)

    projects = db.execute(
        """SELECT id, title, status, start_date, end_date
           FROM projects
           WHERE business_id = ? AND status != 'archived'
           ORDER BY COALESCE(start_date, '9999')""",
        (biz_id,),
    ).fetchall()

    rows = []
    for p in projects:
        pd = dict(p)
        pd["depth"] = 1
        pd["kind"] = "project"
        # Aggregate item_count and done_count for project bar coloring
        agg = db.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN i.status='done' THEN 1 ELSE 0 END) AS done
               FROM item_projects ip
               JOIN items i ON i.id = ip.item_id
               WHERE ip.project_id = ? AND i.status != 'cancelled'""",
            (pd["id"],),
        ).fetchone()
        pd["total"] = agg["total"] or 0
        pd["done"] = agg["done"] or 0
        pd["pct"] = round(pd["done"] * 100 / pd["total"]) if pd["total"] else 0
        rows.append(pd)

        # Top-level tasks under this project
        tasks = db.execute(
            """SELECT i.id, i.title, i.status, i.start_date, i.due_date, i.scheduled_at
               FROM items i
               JOIN item_projects ip ON ip.item_id = i.id
               WHERE ip.project_id = ?
                 AND i.status != 'cancelled'
                 AND i.parent_id IS NULL
               ORDER BY COALESCE(i.start_date, i.due_date, '9999')""",
            (pd["id"],),
        ).fetchall()
        for t in tasks:
            td = dict(t)
            td["depth"] = 2
            td["kind"] = "task"
            rows.append(td)
    return biz_d, rows


def _enrich_with_bars(rows: list[dict], range_start: date, range_end: date) -> list[dict]:
    out = []
    for r in rows:
        d = dict(r)
        s = _parse_date(d.get("start_date") or d.get("scheduled_at"))
        e = _parse_date(d.get("end_date") or d.get("due_date") or d.get("scheduled_at"))
        d["bar_start"] = s.isoformat() if s else None
        d["bar_end"] = e.isoformat() if e else None
        d["has_dates"] = bool(s or e)
        if d["has_dates"]:
            left, width = _bar_offset_pct(s, e, range_start, range_end)
            d["bar_left"] = left
            d["bar_width"] = width
        out.append(d)
    return out


def _month_markers(start: date, end: date) -> list[dict]:
    """Generate month-start position markers across the range."""
    markers = []
    total = (end - start).days or 1
    cur = date(start.year, start.month, 1)
    if cur < start:
        cur = (cur + timedelta(days=32)).replace(day=1)
    while cur <= end:
        offset = (cur - start).days / total * 100
        markers.append({"label": f"{cur.year % 100}.{cur.month:02d}", "left": offset})
        # next month
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return markers


@router.get("/wbs", response_class=HTMLResponse)
async def wbs_page(
    request: Request,
    biz_id: Optional[int] = None,
    proj_id: Optional[int] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Render WBS / Gantt view for a business or project."""
    selectors = {
        "businesses": [
            dict(r) for r in db.execute(
                """SELECT b.id, b.name, o.name AS org_name
                   FROM businesses b LEFT JOIN organizations o ON o.id=b.org_id
                   ORDER BY o.name, b.name"""
            ).fetchall()
        ],
        "projects": [
            dict(r) for r in db.execute(
                """SELECT p.id, p.title, b.name AS biz_name, o.name AS org_name
                   FROM projects p
                   LEFT JOIN businesses b ON b.id=p.business_id
                   LEFT JOIN organizations o ON o.id=b.org_id
                   WHERE p.status != 'archived'
                   ORDER BY o.name, b.name, p.title"""
            ).fetchall()
        ],
    }

    header = None
    rows: list[dict] = []
    today = date.today()

    if proj_id:
        header, rows = _load_project_rows(db, proj_id)
        scope = "project"
    elif biz_id:
        header, rows = _load_business_rows(db, biz_id)
        scope = "business"
    else:
        scope = "none"

    if rows:
        range_start, range_end = _date_range(rows)
        rows = _enrich_with_bars(rows, range_start, range_end)
        markers = _month_markers(range_start, range_end)
        today_offset = (today - range_start).days / max(1, (range_end - range_start).days) * 100
    else:
        range_start = today - timedelta(days=14)
        range_end = today + timedelta(days=60)
        markers = []
        today_offset = None

    return templates.TemplateResponse(
        request,
        "wbs.html",
        {
            "selectors": selectors,
            "header": header,
            "rows": rows,
            "scope": scope,
            "biz_id": biz_id,
            "proj_id": proj_id,
            "range_start": range_start.isoformat(),
            "range_end": range_end.isoformat(),
            "markers": markers,
            "today_offset": today_offset,
            "today": today.isoformat(),
        },
    )
