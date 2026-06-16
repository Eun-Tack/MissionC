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
        end_min = start_min + (15 if item.get("due_at") and not item.get("scheduled_at") else 60)

    clamped_start = max(start_min, grid_start_m)
    clamped_end   = min(end_min, grid_end_m)
    top    = (clamped_start - grid_start_m) * _HOUR_PX // 60
    height = max(24, (clamped_end - clamped_start) * _HOUR_PX // 60)
    return top, height, False


def _time_window(item: dict) -> tuple[int, int] | None:
    start = item.get("effective_start") or item.get("scheduled_at") or item.get("due_at") or ""
    if len(start) < 16:
        return None
    try:
        start_min = int(start[11:13]) * 60 + int(start[14:16])
    except (ValueError, IndexError):
        return None
    end = item.get("end_at") or ""
    if len(end) >= 16:
        try:
            end_min = int(end[11:13]) * 60 + int(end[14:16])
        except (ValueError, IndexError):
            end_min = start_min + 60
    else:
        # A due_at deadline is a point pressure, not a full meeting block.
        end_min = start_min + (15 if item.get("due_at") and not item.get("scheduled_at") else 60)
    if end_min <= start_min:
        end_min = start_min + 15
    return start_min, end_min


def _mark_conflicts(items: list[dict]) -> list[dict]:
    windows: list[tuple[int, int, dict]] = []
    for item in items:
        window = _time_window(item)
        if window:
            windows.append((window[0], window[1], item))
    for idx, (start_a, end_a, item_a) in enumerate(windows):
        conflicts = []
        for jdx, (start_b, end_b, item_b) in enumerate(windows):
            if idx == jdx:
                continue
            if start_a < end_b and start_b < end_a:
                conflicts.append(item_b["title"])
        if conflicts:
            item_a["conflict_count"] = len(conflicts)
            item_a["conflict_titles"] = ", ".join(conflicts[:3])
    return items


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


def _date_only(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _append_item_for_day(result: dict[str, list[dict]], day: date, item: dict) -> None:
    day_key = day.isoformat()
    bucket = result.setdefault(day_key, [])
    kind = item.get("_cal_kind") or ("deadline" if item.get("due_at") and item.get("effective_start") == item.get("due_at") else "item")
    dedupe_key = (
        item.get("id"),
        kind,
        (item.get("effective_start") or item.get("scheduled_at") or "")[:16],
        item.get("start_date") or "",
        item.get("due_date") or "",
    )
    if any(existing.get("_cal_dedupe_key") == dedupe_key for existing in bucket):
        return
    bucket.append({**item, "_cal_dedupe_key": dedupe_key})


def _load_range_items(db: sqlite3.Connection, start: date, end: date) -> dict[str, list[dict]]:
    """Returns {date_str: [items]} for the range, joining schedules for time data."""
    rows = db.execute(
        """SELECT i.id, i.title, i.type, i.status,
                  i.scheduled_at, i.due_at, i.start_date, i.due_date,
                  COALESCE(s.start_at, i.scheduled_at, i.due_at) AS effective_start,
                  s.end_at
           FROM items i
           LEFT JOIN schedules s ON s.item_id = i.id
             AND s.id = (SELECT id FROM schedules WHERE item_id = i.id
                         ORDER BY start_at ASC LIMIT 1)
           WHERE i.status != 'cancelled'
             AND (
               date(COALESCE(s.start_at, i.scheduled_at, i.due_at)) BETWEEN ? AND ?
               OR (
                 date(COALESCE(i.start_date, i.due_date)) <= ?
                 AND date(COALESCE(i.due_date, i.start_date)) >= ?
               )
             )
           ORDER BY COALESCE(s.start_at, i.scheduled_at, i.due_at, i.start_date, i.due_date) ASC NULLS LAST""",
        (start.isoformat(), end.isoformat(), end.isoformat(), start.isoformat()),
    ).fetchall()

    result: dict[str, list[dict]] = {}
    for r in rows:
        d = dict(r)
        range_start = _date_only(d.get("start_date") or d.get("due_date"))
        range_end = _date_only(d.get("due_date") or d.get("start_date"))
        has_date_range = bool(range_start or range_end)

        # Date-range tasks are all-day work. Show them on every calendar day
        # in the inclusive start_date -> due_date span instead of only start.
        if d.get("type") == "task" and has_date_range:
            cur = max(range_start or range_end, start)
            last = min(range_end or range_start, end)
            while cur <= last:
                item_for_day = {**d, "effective_start": f"{cur.isoformat()}T00:00:00Z", "end_at": None, "_cal_kind": "range"}
                _append_item_for_day(result, cur, item_for_day)
                cur += timedelta(days=1)
            continue

        day = _date_only(d.get("effective_start"))
        if day:
            _append_item_for_day(result, day, d)

    gcal = db.execute(
        """SELECT id, title, start_at, end_at, mc_status
           FROM gcal_cache
           WHERE date(start_at) BETWEEN ? AND ? AND visible=1
             AND mc_item_id IS NULL
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
    from ..integrations import schedule_integration_sync, sync_gcal

    schedule_integration_sync("gcal", sync_gcal())
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
        view_anchor  = days[0]
        prev_anchor  = view_anchor - timedelta(weeks=1)
        next_anchor  = view_anchor + timedelta(weeks=1)
        label = f"{days[0].month}월 {days[0].day}일 – {days[-1].month}월 {days[-1].day}일"
    elif mode == "month":
        days  = []
        view_anchor = anchor.replace(day=1)
        weeks = _month_weeks(view_anchor)
        all_days     = [d for w in weeks for d in w]
        items_by_day = _load_range_items(db, all_days[0], all_days[-1])
        prev_anchor  = (view_anchor - timedelta(days=1)).replace(day=1)
        next_anchor  = (view_anchor.replace(day=28) + timedelta(days=4)).replace(day=1)
        label = f"{view_anchor.year}년 {_KO_MONTH[view_anchor.month - 1]}"
    else:  # day
        days         = [anchor]
        items_by_day = _load_range_items(db, anchor, anchor)
        view_anchor  = anchor
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
        timed_by_day[day_str] = _mark_conflicts(timed)

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
        "anchor":        view_anchor.isoformat(),
        "anchor_date":   view_anchor,
        "label":         label,
        "today":         today.isoformat(),
        "days":          [d.isoformat() for d in (days if mode != "month" else [])],
        "weeks":         [[d.isoformat() for d in w] for w in (_month_weeks(view_anchor) if mode == "month" else [])],
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
