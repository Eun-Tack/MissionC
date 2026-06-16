"""
SC-09 Capture Inbox (FR-INBOX-01).

GET  /inbox                   — triage UI
POST /inbox/{id}/accept       — create item from inbox entry
POST /inbox/{id}/reject       — mark as rejected/archived
GET  /api/inbox/count         — unread badge count
POST /api/inbox/add           — manual quick-add to inbox (dev/TG stub)
"""

from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..db import get_db

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _load_projects(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute(
        "SELECT p.id, p.title, o.name AS org_name FROM projects p "
        "LEFT JOIN businesses b ON b.id=p.business_id "
        "LEFT JOIN organizations o ON o.id=b.org_id "
        "WHERE p.status != 'archived' ORDER BY p.title"
    ).fetchall()
    return [dict(r) for r in rows]


def _load_inbox(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute(
        """SELECT id, source, raw_text, suggested_type, suggested_tags,
                  status, received_at
           FROM capture_inbox
           WHERE status = 'pending'
           ORDER BY received_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def _load_processed(db: sqlite3.Connection, limit: int = 20) -> list[dict]:
    rows = db.execute(
        """SELECT ci.id, ci.source, ci.raw_text, ci.suggested_type,
                  ci.status, ci.received_at, ci.processed_at,
                  i.title AS accepted_title
           FROM capture_inbox ci
           LEFT JOIN items i ON i.id = ci.accepted_item_id
           WHERE ci.status != 'pending'
           ORDER BY ci.processed_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/inbox", response_class=HTMLResponse)
async def inbox_page(request: Request, db: sqlite3.Connection = Depends(get_db)):
    from ..integrations import poll_telegram, schedule_integration_sync

    schedule_integration_sync("telegram", poll_telegram())
    pending  = _load_inbox(db)
    processed = _load_processed(db, limit=10)
    return templates.TemplateResponse(
        request,
        "inbox.html",
        {
            "pending": pending,
            "processed": processed,
            "projects": _load_projects(db),
            "pending_count": len(pending),
        },
    )


@router.post("/inbox/{inbox_id}/accept", response_class=HTMLResponse)
async def accept_inbox(
    request: Request,
    inbox_id: int,
    title: Annotated[str, Form()] = "",
    type_: Annotated[str, Form(alias="type")] = "task",
    project_id: Annotated[int | None, Form()] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute(
        "SELECT raw_text, suggested_type FROM capture_inbox WHERE id=? AND status='pending'",
        (inbox_id,),
    ).fetchone()
    if not row:
        return HTMLResponse("", status_code=404)

    use_title = title.strip() or row["raw_text"]
    use_type  = type_ or row["suggested_type"] or "task"

    now = _now()
    cur = db.execute(
        """INSERT INTO items (type, title, body_inline, status, location, created_at, updated_at, source)
           VALUES (?,?,0,'todo','hot',?,?,'manual')""",
        (use_type, use_title, now, now),
    )
    item_id = cur.lastrowid

    if project_id:
        db.execute(
            "INSERT OR IGNORE INTO item_projects(item_id, project_id, is_primary) VALUES(?,?,1)",
            (item_id, project_id),
        )

    db.execute(
        "UPDATE capture_inbox SET status='accepted', accepted_item_id=?, processed_at=? WHERE id=?",
        (item_id, now, inbox_id),
    )

    # Re-render the pending list
    pending = _load_inbox(db)
    return templates.TemplateResponse(
        request,
        "partials/inbox_list.html",
        {"pending": pending, "projects": _load_projects(db)},
    )


@router.post("/inbox/{inbox_id}/reject", response_class=HTMLResponse)
async def reject_inbox(
    request: Request,
    inbox_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute(
        "UPDATE capture_inbox SET status='rejected', processed_at=? WHERE id=?",
        (_now(), inbox_id),
    )
    pending = _load_inbox(db)
    return templates.TemplateResponse(
        request,
        "partials/inbox_list.html",
        {"pending": pending, "projects": _load_projects(db)},
    )


@router.get("/api/inbox/count")
async def inbox_count(db: sqlite3.Connection = Depends(get_db)):
    count = db.execute(
        "SELECT COUNT(*) FROM capture_inbox WHERE status='pending'"
    ).fetchone()[0]
    return JSONResponse({"count": count})


@router.post("/api/inbox/add")
async def inbox_add(
    text: Annotated[str, Form()],
    source: Annotated[str, Form()] = "quick",
    db: sqlite3.Connection = Depends(get_db),
):
    """Add text directly to inbox — used by Telegram polling and manual testing."""
    _VALID_SOURCES = {"telegram", "voice", "quick", "gmail"}
    use_source = source if source in _VALID_SOURCES else "quick"
    db.execute(
        """INSERT INTO capture_inbox(source, raw_text, suggested_type, status, received_at)
           VALUES (?,?,'task','pending',?)""",
        (use_source, text.strip(), _now()),
    )
    return JSONResponse({"ok": True})
