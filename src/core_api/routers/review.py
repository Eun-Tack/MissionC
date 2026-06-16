"""
SC-07 Morning Preview + Evening Review (FR-DAY-01~04).

GET  /morning   — 오늘 일정 미리보기
GET  /evening   — 저녁 회고 (미완료 항목 + 사유 캡처)
POST /api/evening-review  — 저녁 회고 저장 (incomplete_reasons)
POST /api/carry-over      — 이월 (routers/items.py에도 있으나 여기서도 처리 가능)
"""

from __future__ import annotations
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..db import get_db
from .items import _now_iso

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

_KO_WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]
_INCOMPLETE_CATEGORIES = [
    ("time_short",       "시간 부족"),
    ("priority_shift",   "우선순위 변경"),
    ("external_block",   "외부 차단"),
    ("motivation_low",   "동기 저하"),
    ("info_lack",        "정보 부족"),
    ("overestimated",    "과대 예측"),
    ("other",            "기타"),
]
_DECISION_OPTIONS = [
    ("carry_over",  "내일로 이월"),
    ("cancel",      "취소"),
    ("reschedule",  "일정 변경"),
    ("split",       "분리"),
]


def _date_label(d: date) -> tuple[str, str]:
    ko = f"{d.year}년 {d.month}월 {d.day}일"
    wd = _KO_WEEKDAY[d.weekday()]
    return ko, wd


def _query_today_schedule(db: sqlite3.Connection, today: str) -> list[dict]:
    rows = db.execute(
        """
        SELECT i.id, i.type, i.title, i.status,
               s.start_at, s.end_at,
               GROUP_CONCAT(DISTINCT t.name) AS tag_names
        FROM items i
        LEFT JOIN schedules s ON s.item_id = i.id
        LEFT JOIN item_tags it ON it.item_id = i.id
        LEFT JOIN tags t ON t.id = it.tag_id
        WHERE i.location = 'hot'
          AND i.status NOT IN ('cancelled')
          AND date(COALESCE(s.start_at, i.scheduled_at)) = ?
        GROUP BY i.id
        ORDER BY COALESCE(s.start_at, i.scheduled_at) ASC NULLS LAST
        """,
        (today,),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["tags"] = [t for t in (d["tag_names"] or "").split(",") if t]
        d["time_display"] = (d["start_at"] or "")[ 11:16] if d["start_at"] else "—"
        result.append(d)
    return result


def _query_incomplete(db: sqlite3.Connection, today: str) -> list[dict]:
    rows = db.execute(
        """
        SELECT i.id, i.type, i.title, i.status,
               s.start_at,
               GROUP_CONCAT(DISTINCT t.name) AS tag_names,
               ir.category, ir.decision
        FROM items i
        LEFT JOIN schedules s ON s.item_id = i.id
        LEFT JOIN item_tags it ON it.item_id = i.id
        LEFT JOIN tags t ON t.id = it.tag_id
        LEFT JOIN incomplete_reasons ir
               ON ir.item_id = i.id AND ir.review_date = ?
        WHERE i.location = 'hot'
          AND i.status NOT IN ('done', 'cancelled')
          AND i.status NOT IN ('doing', 'in_progress')
          AND (
              date(COALESCE(s.start_at, i.scheduled_at)) <= ?
              OR date(i.due_date) <= ?
              OR (i.scheduled_at IS NULL AND s.start_at IS NULL
                  AND i.start_date IS NULL AND i.due_date IS NULL)
          )
          AND NOT (date(i.start_date) <= ? AND (i.due_date IS NULL OR date(i.due_date) >= ?))
        GROUP BY i.id
        ORDER BY COALESCE(s.start_at, i.scheduled_at) ASC NULLS LAST
        """,
        (today, today, today, today, today),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["tags"] = [t for t in (d["tag_names"] or "").split(",") if t]
        result.append(d)
    return result


def _query_in_progress(db: sqlite3.Connection, today: str) -> list[dict]:
    rows = db.execute(
        """
        SELECT i.id, i.type, i.title, i.status,
               s.start_at,
               GROUP_CONCAT(DISTINCT t.name) AS tag_names
        FROM items i
        LEFT JOIN schedules s ON s.item_id = i.id
        LEFT JOIN item_tags it ON it.item_id = i.id
        LEFT JOIN tags t ON t.id = it.tag_id
        WHERE i.location = 'hot'
          AND i.status NOT IN ('done', 'cancelled')
          AND (
              i.status IN ('doing', 'in_progress')
              OR (date(i.start_date) <= ? AND (i.due_date IS NULL OR date(i.due_date) >= ?))
          )
        GROUP BY i.id
        ORDER BY COALESCE(i.due_date, s.start_at, i.scheduled_at, i.created_at) ASC
        """,
        (today, today),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["tags"] = [t for t in (d["tag_names"] or "").split(",") if t]
        result.append(d)
    return result


def _query_done_today(db: sqlite3.Connection, today: str) -> int:
    return db.execute(
        """
        SELECT COUNT(*) FROM items i
        LEFT JOIN schedules s ON s.item_id = i.id
        WHERE i.status = 'done'
          AND date(COALESCE(s.start_at, i.updated_at)) = ?
        """,
        (today,),
    ).fetchone()[0]


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/morning", response_class=HTMLResponse)
async def morning(request: Request, db: sqlite3.Connection = Depends(get_db)):
    today = date.today()
    today_str = today.isoformat()
    date_ko, weekday_ko = _date_label(today)

    items = _query_today_schedule(db, today_str)
    total = len(items)
    done_yesterday = _query_done_today(db, (today - timedelta(days=1)).isoformat())
    incomplete_count = db.execute(
        """SELECT COUNT(*) FROM items
           WHERE location='hot' AND status NOT IN ('done','cancelled')
             AND (scheduled_at IS NULL OR date(scheduled_at) < ?)""",
        (today_str,),
    ).fetchone()[0]

    return templates.TemplateResponse(
        request,
        "morning.html",
        {
            "date_korean": date_ko,
            "weekday_korean": weekday_ko,
            "today_str": today_str,
            "items": items,
            "total": total,
            "done_yesterday": done_yesterday,
            "carryover_count": incomplete_count,
        },
    )


@router.get("/evening", response_class=HTMLResponse)
async def evening(request: Request, db: sqlite3.Connection = Depends(get_db)):
    today = date.today()
    today_str = today.isoformat()
    date_ko, weekday_ko = _date_label(today)

    incomplete = _query_incomplete(db, today_str)
    in_progress = _query_in_progress(db, today_str)
    done_count = _query_done_today(db, today_str)
    total = done_count + len(in_progress) + len(incomplete)

    return templates.TemplateResponse(
        request,
        "evening.html",
        {
            "date_korean": date_ko,
            "weekday_korean": weekday_ko,
            "today_str": today_str,
            "incomplete": incomplete,
            "in_progress": in_progress,
            "done_count": done_count,
            "total": total,
            "categories": _INCOMPLETE_CATEGORIES,
            "decisions": _DECISION_OPTIONS,
        },
    )


@router.post("/api/evening-review", response_class=HTMLResponse)
async def save_evening_review(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
):
    """Save incomplete reason for one item (FR-DAY-04). Called per-item via htmx."""
    form = await request.form()
    item_id  = int(form.get("item_id", 0))
    review_date = form.get("review_date", date.today().isoformat())
    category = form.get("category", "other")
    decision = form.get("decision", "carry_over")
    free_text = form.get("free_text", "")

    if not item_id:
        return HTMLResponse('<span style="color:red">항목 ID 필요</span>', status_code=422)

    db.execute(
        """INSERT INTO incomplete_reasons(item_id, review_date, category, free_text, decision, recorded_at)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT DO NOTHING""",
        (item_id, review_date, category, free_text or None, decision, _now_iso()),
    )

    # Apply decision
    if decision == "carry_over":
        from datetime import date as _date, timedelta as _td
        tomorrow = (_date.fromisoformat(review_date) + _td(days=1)).isoformat()
        db.execute(
            "UPDATE items SET scheduled_at=?, updated_at=? WHERE id=?",
            (tomorrow + "T00:00:00Z", _now_iso(), item_id),
        )
    elif decision == "cancel":
        db.execute(
            "UPDATE items SET status='cancelled', updated_at=? WHERE id=?",
            (_now_iso(), item_id),
        )

    return HTMLResponse(
        f'<div id="review-{item_id}" class="review-row-saved">'
        f'  <span style="color:var(--st-done)">✓ 저장됨 ({dict(_DECISION_OPTIONS).get(decision, decision)})</span>'
        f'</div>'
    )
