"""
SC-13 Calendar (FR-CAL-01) — week / month / day view with time grid.

GET  /calendar                        — calendar page (default week)
GET  /partial/calendar?mode=week&date_str=YYYY-MM-DD — htmx partial
"""

from __future__ import annotations
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..db import get_db

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

_KO_WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]
_KO_MONTH   = ["1월", "2월", "3월", "4월", "5월", "6월",
               "7월", "8월", "9월", "10월", "11월", "12월"]

_GRID_START_H = 7
_GRID_END_H   = 23
_HOUR_PX      = 64


def _item_grid_pos(item: dict) -> tuple[int, int, bool]:
    """(top_px, height_px, is_allday). Clamps item to [GRID_START, GRID_END)."""
    start = (item.get("effective_start") or item.get("scheduled_at") or "")
    end   = (item.get("end_at") or "")

    if len(start) < 13:
        return 0, 32, True
    try:
        h = int(start[11:13])
        m = int(start[14:16]) if len(start) >= 16 else 0
    except (ValueError, IndexError):
        return 0, 32, True

    # Midnight with no end_at → treat as all-day (date-only scheduling)
    if h == 0 and m == 0 and not end:
        return 0, 32, True

    start_min    = h * 60 + m
    grid_start_m = _GRID_START_H * 60
    grid_end_m   = _GRID_END_H * 60

    if start_min >= grid_end_m:
        return 0, 32, True

    if len(end) >= 16:
        try:
            end_min = int(end[11:13]) * 60 + int(end[14:16])
            if end_min <= start_min:
                end_min = start_min + 60
        except (ValueError, IndexError):
            end_min = start_min + 60
    else:
        end_min = start_min + 60

    clamped_start = max(start_min, grid_start_m)
    clamped_end   = min(end_min, grid_end_m)
    top    = (clamped_start - grid_start_m) * _HOUR_PX // 60
    height = max(24, (clamped_end - clamped_start) * _HOUR_PX // 60)
    return top, height, False


def _week_dates(anchor: date) -> list[date]:
    monday = anchor - timedelta(days=anchor.weekday())
    return [monday + timedelta(days=i) for i in range(7)]


def _month_weeks(anchor: date) -> list[list[date | None]]:
    first    = anchor.replace(day=1)
    last_day = (first.replace(month=first.month % 12 + 1, day=1) - timedelta(days=1)).day
    last     = anchor.replace(day=last_day)
    start    = first - timedelta(days=first.weekday())
    end      = last + timedelta(days=6 - last.weekday())
    weeks, current = [], start
    while current <= end:
        weeks.append([current + timedelta(days=i) for i in range(7)])
        current += timedelta(days=7)
    return weeks


def _load_range_items(db: sqlite3.Connection, start: date, end: date) -> dict[str, list[dict]]:
    """Returns {date_str: [items]} for the range, joining schedules for time data."""
    rows = db.execute(
        """SELECT i.id, i.title, i.type, i.status, i.scheduled_at,
                  COALESCE(s.start_at, i.scheduled_at) AS effective_start,
                  s.end_at
           FROM items i
           LEFT JOIN schedules s ON s.item_id = i.id
             AND s.id = (SELECT id FROM schedules WHERE item_id = i.id
                         ORDER BY start_at ASC LIMIT 1)
           WHERE date(COALESCE(s.start_at, i.scheduled_at)) BETWEEN ? AND ?
             AND i.status != 'cancelled'
           ORDER BY COALESCE(s.start_at, i.scheduled_at) ASC NULLS LAST""",
        (start.isoformat(), end.isoformat()),
    ).fetchall()

    result: dict[str, list[dict]] = {}
    for r in rows:
        d = dict(r)
        day_key = (d.get("effective_start") or "")[:10]
        if day_key:
            result.setdefault(day_key, []).append(d)

    gcal = db.execute(
        """SELECT id, title, start_at, end_at, mc_status
           FROM gcal_cache
           WHERE date(start_at) BETWEEN ? AND ? AND visible=1
           ORDER BY start_at ASC""",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    for g in gcal:
        d = dict(g)
        d["type"] = "gcal"
        d["status"] = d.get("mc_status") or "todo"
        d["scheduled_at"] = d["start_at"]
        d["effective_start"] = d["start_at"]
        day_key = (d.get("start_at") or "")[:10]
        if day_key:
            result.setdefault(day_key, []).append(d)

    return result


def _parse_date(date_str: str | None) -> date:
    try:
        return date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        return date.today()


@router.get("/calendar", response_class=HTMLResponse)
async def calendar_page(
    request: Request,
    mode: str = "week",
    date_str: str = "",
    db: sqlite3.Connection = Depends(get_db),
):
    from ..integrations import sync_gcal
    await sync_gcal()
    anchor = _parse_date(date_str)
    ctx = _build_calendar_context(db, mode, anchor)
    return templates.TemplateResponse(request, "calendar.html", ctx)


@router.get("/partial/calendar", response_class=HTMLResponse)
async def calendar_partial(
    request: Request,
    mode: str = "week",
    date_str: str = "",
    db: sqlite3.Connection = Depends(get_db),
):
    anchor = _parse_date(date_str)
    ctx = _build_calendar_context(db, mode, anchor)
    return templates.TemplateResponse(request, "partials/calendar_grid.html", ctx)


def _build_calendar_context(db: sqlite3.Connection, mode: str, anchor: date) -> dict:
    today = date.today()

    if mode == "week":
        days         = _week_dates(anchor)
        items_by_day = _load_range_items(db, days[0], days[-1])
        prev_anchor  = anchor - timedelta(weeks=1)
        next_anchor  = anchor + timedelta(weeks=1)
        label = f"{days[0].month}월 {days[0].day}일 – {days[-1].month}월 {days[-1].day}일"
    elif mode == "month":
        days  = []
        weeks = _month_weeks(anchor)
        all_days     = [d for w in weeks for d in w]
        items_by_day = _load_range_items(db, all_days[0], all_days[-1])
        prev_anchor  = (anchor.replace(day=1) - timedelta(days=1)).replace(day=1)
        next_anchor  = (anchor.replace(day=28) + timedelta(days=4)).replace(day=1)
        label = f"{anchor.year}년 {_KO_MONTH[anchor.month - 1]}"
    else:  # day
        days         = [anchor]
        items_by_day = _load_range_items(db, anchor, anchor)
        prev_anchor  = anchor - timedelta(days=1)
        next_anchor  = anchor + timedelta(days=1)
        label = f"{anchor.year}년 {anchor.month}월 {anchor.day}일 ({_KO_WEEKDAY[anchor.weekday()]})"

    # Split into all-day vs timed (for week/day time grid)
    allday_by_day: dict[str, list] = {}
    timed_by_day:  dict[str, list] = {}
    for day_str, day_items in items_by_day.items():
        allday, timed = [], []
        for item in day_items:
            top, height, is_allday = _item_grid_pos(item)
            if is_allday:
                allday.append(item)
            else:
                timed.append({**item, "top_px": top, "height_px": height})
        allday_by_day[day_str] = allday
        timed_by_day[day_str]  = timed

    organizations = db.execute(
        "SELECT id, name FROM organizations ORDER BY name"
    ).fetchall()
    businesses = db.execute(
        """SELECT b.id, b.name, b.org_id, o.name AS org_name
           FROM businesses b
           LEFT JOIN organizations o ON o.id = b.org_id
           ORDER BY o.name, b.name"""
    ).fetchall()
    projects = db.execute(
        """SELECT p.id, p.title, p.business_id, b.name AS biz_name,
                  b.org_id, o.name AS org_name
           FROM projects p
           LEFT JOIN businesses b ON b.id = p.business_id
           LEFT JOIN organizations o ON o.id = b.org_id
           WHERE p.status != 'archived'
           ORDER BY o.name, b.name, p.title"""
    ).fetchall()

    return {
        "mode":          mode,
        "anchor":        anchor.isoformat(),
        "anchor_date":   anchor,
        "label":         label,
        "today":         today.isoformat(),
        "days":          [d.isoformat() for d in (days if mode != "month" else [])],
        "weeks":         [[d.isoformat() for d in w] for w in (_month_weeks(anchor) if mode == "month" else [])],
        "weekday_names": _KO_WEEKDAY,
        "items_by_day":  items_by_day,
        "allday_by_day": allday_by_day,
        "timed_by_day":  timed_by_day,
        "prev_anchor":   prev_anchor.isoformat(),
        "next_anchor":   next_anchor.isoformat(),
        "organizations": [dict(o) for o in organizations],
        "businesses":    [dict(b) for b in businesses],
        "projects":      [dict(p) for p in projects],
        # Time grid constants
        "grid_start_h":  _GRID_START_H,
        "grid_end_h":    _GRID_END_H,
        "grid_hours":    list(range(_GRID_START_H, _GRID_END_H)),
        "grid_height":   (_GRID_END_H - _GRID_START_H) * _HOUR_PX,
        "hour_px":       _HOUR_PX,
    }
