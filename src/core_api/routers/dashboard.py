"""Closure dashboard view.

GET /dashboard -> full page (dashboard.html)
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from ..db import get_db

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

_WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_OPEN_STATUSES = ("todo", "doing", "waiting")


def _count(db: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    return int(db.execute(sql, params).fetchone()[0])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: sqlite3.Connection = Depends(get_db)):
    today = date.today()
    today_str = today.isoformat()
    stale_before = (today - timedelta(days=3)).isoformat()

    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    week_data = []
    for d in days:
        done = _count(
            db,
            "SELECT COUNT(*) FROM items WHERE date(updated_at)=? AND status='done'",
            (d.isoformat(),),
        )
        touched = _count(
            db,
            "SELECT COUNT(*) FROM items WHERE date(updated_at)=? AND status!='cancelled'",
            (d.isoformat(),),
        )
        week_data.append({
            "date": d.strftime("%m/%d"),
            "day": _WEEKDAY[d.weekday()],
            "done": done,
            "total": touched,
            "pct": round(done / touched * 100) if touched else 0,
        })

    open_count = _count(
        db,
        "SELECT COUNT(*) FROM items WHERE status IN ('todo','doing','waiting')",
    )
    due_today_count = _count(
        db,
        """SELECT COUNT(*) FROM items
           WHERE (
             due_date = ?
             OR date(due_at) = ?
           ) AND status IN ('todo','doing','waiting')""",
        (today_str, today_str),
    )
    overdue_count = _count(
        db,
        """SELECT COUNT(*) FROM items
           WHERE (
             due_date < ?
             OR datetime(due_at) < datetime(?)
           ) AND status IN ('todo','doing','waiting')""",
        (today_str, f"{today_str}T00:00:00Z"),
    )
    stale_count = _count(
        db,
        """SELECT COUNT(*) FROM items
           WHERE date(updated_at) < ? AND status IN ('todo','doing','waiting')""",
        (stale_before,),
    )

    rows = db.execute(
        """
        SELECT p.id, p.title, p.status,
               COUNT(CASE WHEN i.status != 'cancelled' THEN 1 END) AS total,
               COUNT(CASE WHEN i.status = 'done' THEN 1 END) AS done,
               COUNT(CASE WHEN i.status IN ('todo','doing','waiting') THEN 1 END) AS open,
               COUNT(CASE WHEN (i.due_date < ? OR datetime(i.due_at) < datetime(?)) AND i.status IN ('todo','doing','waiting') THEN 1 END) AS overdue,
               COUNT(CASE WHEN date(i.updated_at) < ? AND i.status IN ('todo','doing','waiting') THEN 1 END) AS stale,
               MIN(CASE WHEN i.status IN ('todo','doing','waiting') THEN COALESCE(i.due_at, i.due_date) END) AS next_due
        FROM projects p
        LEFT JOIN item_projects ip ON ip.project_id = p.id
        LEFT JOIN items i ON i.id = ip.item_id
        WHERE p.status != 'archived'
        GROUP BY p.id
        ORDER BY overdue DESC,
                 stale DESC,
                 open DESC,
                 (p.status = 'active') DESC,
                 next_due IS NULL,
                 next_due ASC
        LIMIT 12
        """,
        (today_str, f"{today_str}T00:00:00Z", stale_before),
    ).fetchall()

    closing_items = [
        dict(r) for r in db.execute(
            """
            SELECT i.id, i.title, i.type, i.status, i.due_at, i.due_date, i.start_date, i.updated_at,
                   p.id AS project_id, p.title AS project_title
            FROM items i
            LEFT JOIN item_projects ip ON ip.item_id = i.id
            LEFT JOIN projects p ON p.id = ip.project_id
            WHERE i.location='hot'
              AND i.status IN ('todo','doing','waiting')
              AND (
                date(i.due_at) <= ?
                OR i.due_date <= ?
                OR date(i.updated_at) < ?
              )
            ORDER BY
              CASE
                WHEN datetime(i.due_at) < datetime(?) OR i.due_date < ? THEN 0
                WHEN date(i.due_at) = ? OR i.due_date = ? THEN 1
                ELSE 2
              END,
              COALESCE(i.due_at, i.due_date, i.updated_at) ASC
            LIMIT 12
            """,
            (
                today_str,
                today_str,
                stale_before,
                f"{today_str}T00:00:00Z",
                today_str,
                today_str,
                today_str,
            ),
        ).fetchall()
    ]
    mobile_actions = [
        dict(r) for r in db.execute(
            """
            SELECT msa.id, msa.action, msa.title, msa.old_value, msa.new_value,
                   msa.created_at, i.title AS item_title, i.status AS item_status
            FROM mobile_sync_actions msa
            LEFT JOIN items i ON i.id=msa.item_id
            WHERE msa.status='pending'
            ORDER BY msa.created_at DESC
            LIMIT 8
            """
        ).fetchall()
    ]
    for item in closing_items:
        if (item.get("due_at") and item["due_at"][:10] < today_str) or (item.get("due_date") and item["due_date"] < today_str):
            item["closure_reason"] = "지연"
        elif (item.get("due_at") and item["due_at"][:10] == today_str) or item.get("due_date") == today_str:
            item["closure_reason"] = "오늘 마감"
        else:
            item["closure_reason"] = "정체"

    status_labels = {
        "active": "진행",
        "planning": "기획",
        "review": "검토",
        "done": "완료",
        "paused": "중단",
    }
    projects = []
    closure_actions = []
    for row in rows:
        total = int(row["total"] or 0)
        done = int(row["done"] or 0)
        overdue = int(row["overdue"] or 0)
        stale = int(row["stale"] or 0)
        open_items = int(row["open"] or 0)
        pct = round(done / total * 100) if total else 0

        if overdue:
            action = "지연 항목을 연기, 완료, 취소 중 하나로 결정"
            risk = f"지연 {overdue}"
        elif stale:
            action = "정체 항목에 다음 행동 또는 대기 사유 추가"
            risk = f"정체 {stale}"
        elif open_items:
            action = "다음 닫기 단계 선택"
            risk = "진행 중"
        else:
            action = "완료 검토 가능"
            risk = "정상"

        project = {
            "id": row["id"],
            "title": row["title"],
            "status": row["status"],
            "status_label": status_labels.get(row["status"], row["status"]),
            "total": total,
            "done": done,
            "open": open_items,
            "overdue": overdue,
            "stale": stale,
            "next_due": row["next_due"],
            "pct": pct,
            "risk": risk,
            "action": action,
        }
        projects.append(project)
        if overdue or stale:
            closure_actions.append(project)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "week_data": week_data,
            "today_done": week_data[-1]["done"],
            "today_total": week_data[-1]["total"],
            "open_count": open_count,
            "due_today_count": due_today_count,
            "overdue_count": overdue_count,
            "stale_count": stale_count,
            "projects": projects,
            "closure_actions": closure_actions[:5],
            "closing_items": closing_items,
            "mobile_actions": mobile_actions,
            "today": today_str,
            "stale_before": stale_before,
            "open_statuses": _OPEN_STATUSES,
        },
    )


@router.post("/api/mobile-sync-actions/{action_id}/accept")
def accept_mobile_action(action_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT * FROM mobile_sync_actions WHERE id=? AND status='pending'",
        (action_id,),
    ).fetchone()
    if not row:
        return Response(status_code=404)
    if row["item_id"]:
        if row["action"] in ("mark_done", "mark_waiting", "cancel"):
            status = {"mark_done": "done", "mark_waiting": "waiting", "cancel": "cancelled"}[row["action"]]
            db.execute("UPDATE items SET status=?, updated_at=datetime('now') WHERE id=?", (status, row["item_id"]))
        elif row["action"] == "reschedule" and row["new_value"]:
            item = db.execute("SELECT scheduled_at, due_at, start_date, due_date FROM items WHERE id=?", (row["item_id"],)).fetchone()
            if item:
                target_col = "scheduled_at" if item["scheduled_at"] else "due_at" if item["due_at"] else "start_date" if item["start_date"] else "due_date"
                new_value = row["new_value"]
                if target_col in ("scheduled_at", "due_at"):
                    old = item[target_col] or ""
                    time_part = old[10:] if len(old) > 10 and "T" in old else "T09:00:00Z"
                    new_value = f"{new_value}{time_part}"
                db.execute(f"UPDATE items SET {target_col}=?, updated_at=datetime('now') WHERE id=?", (new_value, row["item_id"]))
    db.execute(
        "UPDATE mobile_sync_actions SET status='accepted', resolved_at=datetime('now') WHERE id=?",
        (action_id,),
    )
    return Response(status_code=204)


@router.post("/api/mobile-sync-actions/{action_id}/reject")
def reject_mobile_action(action_id: int, db: sqlite3.Connection = Depends(get_db)):
    db.execute(
        "UPDATE mobile_sync_actions SET status='rejected', resolved_at=datetime('now') WHERE id=? AND status='pending'",
        (action_id,),
    )
    return Response(status_code=204)
