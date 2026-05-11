"""
Notification endpoints — browser push reminders for upcoming items.

GET  /api/notifications/due      — items due in the next N minutes (JSON)
POST /api/notifications/mark-sent — mark item notification as sent (prevents re-firing)
"""

from __future__ import annotations
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse

from ..db import get_db

router = APIRouter(prefix="/api/notifications")

_LOOKAHEAD_MINUTES = 30


@router.get("/due")
async def notifications_due(db: sqlite3.Connection = Depends(get_db)):
    """
    Return items whose scheduled_at or due_date falls within the next 30 minutes
    and that are not yet done/cancelled. Client de-dupes with sessionStorage.
    """
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(minutes=_LOOKAHEAD_MINUTES)
    now_s = now.strftime("%Y-%m-%dT%H:%M")
    end_s = window_end.strftime("%Y-%m-%dT%H:%M")

    rows = db.execute(
        """SELECT i.id, i.title, i.type,
                  COALESCE(i.scheduled_at, i.due_date) AS notify_at,
                  p.title AS project_title
           FROM items i
           LEFT JOIN item_projects ip ON ip.item_id = i.id
           LEFT JOIN projects p ON p.id = ip.project_id
           WHERE i.status NOT IN ('done', 'cancelled')
             AND COALESCE(i.scheduled_at, i.due_date) BETWEEN ? AND ?
           ORDER BY notify_at""",
        (now_s, end_s),
    ).fetchall()

    return JSONResponse([dict(r) for r in rows])


@router.post("/mark-sent")
async def mark_sent(
    item_id: int = Form(...),
    db: sqlite3.Connection = Depends(get_db),
):
    """Record that a browser notification was shown."""
    db.execute(
        """INSERT INTO notification_events(item_id, kind, channel)
           VALUES(?, 'lead', 'os_toast')""",
        (item_id,),
    )
    return JSONResponse({"ok": True})
