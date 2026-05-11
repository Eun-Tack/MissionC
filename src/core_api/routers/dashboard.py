"""
Dashboard view — weekly progress, project status, streaks.

GET /dashboard  → full page (dashboard.html)
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


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: sqlite3.Connection = Depends(get_db)):
    today = date.today()

    # --- Last 7 days by day ---
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    week_data = []
    for d in days:
        done = db.execute(
            "SELECT COUNT(*) FROM items WHERE date(updated_at)=? AND status='done'",
            (d.isoformat(),),
        ).fetchone()[0]
        total = db.execute(
            "SELECT COUNT(*) FROM items WHERE date(updated_at)=? AND status!='cancelled'",
            (d.isoformat(),),
        ).fetchone()[0]
        week_data.append({
            "date": d.strftime("%m/%d"),
            "day": _KO_WEEKDAY[d.weekday()],
            "done": done,
            "total": total,
            "pct": round(done / total * 100) if total else 0,
        })

    # --- Today totals ---
    today_done = week_data[-1]["done"]
    today_total = week_data[-1]["total"]

    # --- Projects (top 10, active first) ---
    rows = db.execute("""
        SELECT p.title, p.status, p.id,
               COUNT(CASE WHEN i.status != 'cancelled' THEN 1 END) AS total,
               COUNT(CASE WHEN i.status = 'done'       THEN 1 END) AS done
        FROM projects p
        LEFT JOIN item_projects ip ON ip.project_id = p.id
        LEFT JOIN items i ON i.id = ip.item_id
        WHERE p.status != 'archived'
        GROUP BY p.id
        ORDER BY (p.status = 'active') DESC, total DESC
        LIMIT 10
    """).fetchall()
    projects = [
        {
            "id": r[2],
            "title": r[0],
            "status": r[1],
            "total": r[3],
            "done": r[4],
            "pct": round(r[4] / r[3] * 100) if r[3] else 0,
        }
        for r in rows
    ]

    # --- Overdue ---
    overdue_count = db.execute(
        "SELECT COUNT(*) FROM items WHERE due_date < ? AND status NOT IN ('done','cancelled')",
        (today.isoformat(),),
    ).fetchone()[0]

    # --- Streak ---
    streak = 0
    for d in [today - timedelta(days=i) for i in range(30)]:
        c = db.execute(
            "SELECT COUNT(*) FROM items WHERE date(updated_at)=? AND status='done'",
            (d.isoformat(),),
        ).fetchone()[0]
        if c > 0:
            streak += 1
        else:
            break

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "week_data": week_data,
            "today_done": today_done,
            "today_total": today_total,
            "projects": projects,
            "overdue_count": overdue_count,
            "streak": streak,
            "today": today.isoformat(),
        },
    )
