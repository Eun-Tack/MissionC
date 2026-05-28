"""
SC-10 Diagnostics (FR-DIAG-01) + SC-11 Notification Center (FR-NOTIFY-CTR-01).

GET  /diag                     — system health dashboard
GET  /alerts                   — notification & retry center
POST /alerts/{id}/dismiss      — dismiss a notification event
POST /api/alerts/dismiss-all   — dismiss all
"""

from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..db import get_db, DB_PATH
from ..config import get_config

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _secret_status(key: str) -> str:
    try:
        import keyring
        val = keyring.get_password(key, "iet03")
        return "set" if val and val.strip() else "notset"
    except Exception:
        return "error"


def _db_stats(db: sqlite3.Connection) -> dict:
    tables = ["items", "projects", "organizations", "businesses",
              "capture_inbox", "notification_events", "retry_queue",
              "file_index", "github_cache", "gcal_cache"]
    counts = {}
    for t in tables:
        try:
            counts[t] = db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except Exception:
            counts[t] = -1

    db_size_mb = 0
    try:
        db_size_mb = round(DB_PATH.stat().st_size / 1024 / 1024, 2)
    except Exception:
        pass

    return {"counts": counts, "size_mb": db_size_mb}


@router.get("/diag", response_class=HTMLResponse)
async def diagnostics(request: Request, db: sqlite3.Connection = Depends(get_db)):
    cfg = get_config()
    db_stats = _db_stats(db)

    # Credential status
    creds = {
        "GitHub PAT": _secret_status("MC_GH_PAT"),
        "Telegram Bot": _secret_status("MC_TG_BOT_TOKEN"),
        "Google Calendar": _secret_status("MC_GCAL_TOKEN"),
    }

    # Last GitHub sync
    gh_last = db.execute(
        "SELECT MAX(fetched_at) FROM github_cache"
    ).fetchone()[0]

    # Last GCal sync
    gcal_last = db.execute(
        "SELECT MAX(fetched_at) FROM gcal_cache"
    ).fetchone()[0]

    # Worker status from settings
    def setting(key: str, default: str = "—") -> str:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    worker_status = {
        "ai_worker":      setting("worker_status_ai", "not_started"),
        "notifier":       setting("worker_status_notifier", "not_started"),
        "embed_model":    setting("worker_status_embed", "not_installed"),
        "whisper_model":  setting("worker_status_whisper", "not_installed"),
    }

    # Recent errors
    recent_errors = db.execute(
        """SELECT id, target, operation, last_error, next_attempt_at, attempts
           FROM retry_queue WHERE resolved=0 ORDER BY created_at DESC LIMIT 10"""
    ).fetchall()

    # Recent notifications
    recent_notifs = db.execute(
        """SELECT id, kind, channel, sent_at, dismissed
           FROM notification_events ORDER BY sent_at DESC LIMIT 10"""
    ).fetchall()

    return templates.TemplateResponse(
        request,
        "diagnostics.html",
        {
            "db_stats": db_stats,
            "creds": creds,
            "gh_last": gh_last,
            "gcal_last": gcal_last,
            "worker_status": worker_status,
            "recent_errors": [dict(r) for r in recent_errors],
            "recent_notifs": [dict(r) for r in recent_notifs],
            "notes_root": str(cfg.notes_root) if cfg.mc_notes_root else "—",
            "setup_done": setting("setup_completed") == "true",
        },
    )


@router.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request, db: sqlite3.Connection = Depends(get_db)):
    notifs = db.execute(
        """SELECT ne.id, ne.kind, ne.channel, ne.sent_at, ne.dismissed,
                  i.title AS item_title
           FROM notification_events ne
           LEFT JOIN items i ON i.id = ne.item_id
           ORDER BY ne.sent_at DESC
           LIMIT 50"""
    ).fetchall()

    retries = db.execute(
        """SELECT id, target, operation, attempts, last_error,
                  next_attempt_at, created_at, resolved
           FROM retry_queue
           ORDER BY resolved ASC, created_at DESC
           LIMIT 30"""
    ).fetchall()

    undismissed = db.execute(
        "SELECT COUNT(*) FROM notification_events WHERE dismissed=0"
    ).fetchone()[0]

    return templates.TemplateResponse(
        request,
        "alerts.html",
        {
            "notifs": [dict(n) for n in notifs],
            "retries": [dict(r) for r in retries],
            "undismissed_count": undismissed,
        },
    )


@router.post("/alerts/{notif_id}/dismiss", response_class=HTMLResponse)
async def dismiss_alert(
    notif_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute(
        "UPDATE notification_events SET dismissed=1, dismissed_at=? WHERE id=?",
        (_now(), notif_id),
    )
    count = db.execute(
        "SELECT COUNT(*) FROM notification_events WHERE dismissed=0"
    ).fetchone()[0]
    return HTMLResponse(
        f'<span id="undismissed-count">{count}</span>'
    )


@router.post("/api/alerts/dismiss-all", response_class=HTMLResponse)
async def dismiss_all(db: sqlite3.Connection = Depends(get_db)):
    db.execute(
        "UPDATE notification_events SET dismissed=1, dismissed_at=? WHERE dismissed=0",
        (_now(),),
    )
    return HTMLResponse('<span id="undismissed-count">0</span>')


@router.post("/api/retry/{retry_id}/resolve", response_class=HTMLResponse)
async def resolve_retry(
    retry_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute(
        "UPDATE retry_queue SET resolved=1, resolved_at=? WHERE id=?",
        (_now(), retry_id),
    )
    return HTMLResponse("")
