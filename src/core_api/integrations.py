"""
Background integration tasks (FR-GIT-04, FR-INT-TG-01).
Started via APScheduler in main.py lifespan.
"""

from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("mc.integrations")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _get_secret(key: str) -> str | None:
    import os
    env_key = key.upper().replace("-", "_").replace("/", "_")
    val = os.environ.get(env_key)
    if val and val.strip():
        return val.strip()
    try:
        import keyring
        val = keyring.get_password(key, "iet03")
        if not val and key == "MC_GCAL_TOKEN":
            val = keyring.get_password("MC_GOOGLE_OAUTH", "iet03")
            if val:
                keyring.set_password("MC_GCAL_TOKEN", "iet03", val)
        return val if val and val.strip() else None
    except Exception:
        return None


def _db_path() -> Path:
    from .db import DB_PATH
    return DB_PATH


# ── B-004 inbox expiry ───────────────────────────────────────────────────────

def expire_stale_inbox(days: int = 14) -> int:
    """Mark pending capture_inbox rows older than `days` as expired.
    Returns the number of rows updated. (B-004, BR-INBOX-02)"""
    import sqlite3
    try:
        path = _db_path()
        if not path.exists():
            return 0
        with sqlite3.connect(path) as conn:
            cur = conn.execute(
                """UPDATE capture_inbox
                   SET status='expired', processed_at=?
                   WHERE status='pending'
                     AND received_at < datetime('now', ?)""",
                (_now(), f"-{int(days)} days"),
            )
            conn.commit()
            n = cur.rowcount or 0
            if n:
                log.info("Expired %d stale inbox rows (>%dd)", n, days)
            return n
    except Exception as e:
        log.warning("inbox expiry failed: %s", e)
        return 0


# ── GitHub sync (FR-GIT-04) ──────────────────────────────────────────────────

async def sync_github() -> None:
    """Fetch open GitHub issues for all projects that have a repo set."""
    token = _get_secret("MC_GH_PAT")
    if not token:
        return

    try:
        import httpx
        import sqlite3
        from .db import get_connection

        with get_connection() as db:
            repos = db.execute(
                "SELECT DISTINCT github_repo FROM projects "
                "WHERE github_repo IS NOT NULL AND status != 'archived'"
            ).fetchall()

        if not repos:
            return

        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        ) as client:
            for (repo,) in repos:
                try:
                    r = await client.get(
                        f"https://api.github.com/repos/{repo}/issues",
                        params={"state": "open", "per_page": 30},
                    )
                    if r.status_code != 200:
                        continue

                    now = _now()
                    with get_connection() as db:
                        for issue in r.json():
                            db.execute(
                                """INSERT INTO github_cache
                                   (repo, number, title, state, html_url, fetched_at)
                                   VALUES (?,?,?,?,?,?)
                                   ON CONFLICT(repo, number) DO UPDATE SET
                                     title=excluded.title, state=excluded.state,
                                     html_url=excluded.html_url,
                                     fetched_at=excluded.fetched_at""",
                                (
                                    repo,
                                    issue["number"],
                                    issue["title"],
                                    issue["state"],
                                    issue["html_url"],
                                    now,
                                ),
                            )
                    log.info("GitHub sync OK: %s (%d issues)", repo, len(r.json()))

                except Exception as e:
                    log.warning("GitHub sync error for %s: %s", repo, e)

    except Exception as e:
        log.error("GitHub sync failed: %s", e)


# ── Telegram polling (FR-INT-TG-01) ─────────────────────────────────────────

_tg_offset: int = 0


async def poll_telegram() -> None:
    """Poll Telegram bot for new messages → capture_inbox."""
    global _tg_offset
    token = _get_secret("MC_TG_BOT_TOKEN")
    if not token:
        return

    try:
        import httpx
        from .db import get_connection

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"offset": _tg_offset, "timeout": 5, "limit": 20},
            )
            if r.status_code != 200 or not r.json().get("ok"):
                return

            updates = r.json().get("result", [])
            if not updates:
                return

            now = _now()
            with get_connection() as db:
                for upd in updates:
                    msg = upd.get("message") or upd.get("channel_post", {})
                    text = msg.get("text", "").strip()
                    if text:
                        db.execute(
                            """INSERT INTO capture_inbox
                               (source, raw_text, raw_payload, suggested_type, status, received_at)
                               VALUES ('telegram', ?, ?, 'task', 'pending', ?)""",
                            (text, str(upd), now),
                        )
                    _tg_offset = upd["update_id"] + 1

            log.info("Telegram polled: %d updates", len(updates))

    except Exception as e:
        log.warning("Telegram poll error: %s", e)


# ── Google Calendar sync (FR-CAL-02) ────────────────────────────────────────

async def sync_gcal() -> None:
    """Fetch GCal events (±7d / +30d window) → gcal_cache."""
    import json, os
    token_json = _get_secret("MC_GCAL_TOKEN")
    if not token_json:
        return

    try:
        token_data = json.loads(token_json)
    except Exception:
        return

    access_token  = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    client_id     = os.environ.get("MC_GOOGLE_CLIENT_ID") or os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("MC_GOOGLE_CLIENT_SECRET") or os.environ.get("GOOGLE_CLIENT_SECRET", "")

    from datetime import timezone, timedelta
    import httpx

    now_dt   = datetime.now(timezone.utc)
    time_min = (now_dt - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = (now_dt + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    _EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    _REFRESH_URL = "https://oauth2.googleapis.com/token"

    async def _fetch(token: str):
        async with httpx.AsyncClient(timeout=10) as c:
            return await c.get(
                _EVENTS_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={"timeMin": time_min, "timeMax": time_max,
                        "singleEvents": "true", "orderBy": "startTime", "maxResults": 100},
            )

    try:
        r = await _fetch(access_token)

        if r.status_code == 401 and refresh_token and client_id:
            async with httpx.AsyncClient(timeout=10) as c:
                ref = await c.post(_REFRESH_URL, data={
                    "refresh_token": refresh_token,
                    "client_id":     client_id,
                    "client_secret": client_secret,
                    "grant_type":    "refresh_token",
                })
            if ref.status_code == 200:
                access_token = ref.json()["access_token"]
                token_data["access_token"] = access_token
                try:
                    import keyring as kr
                    kr.set_password("MC_GCAL_TOKEN", "iet03", json.dumps(token_data))
                except Exception:
                    pass
                r = await _fetch(access_token)
            else:
                log.warning("GCal token refresh failed (%s)", ref.status_code)
                return

        if r.status_code != 200:
            log.warning("GCal sync failed: %s", r.status_code)
            return

        events = r.json().get("items", [])
        now_str = _now()

        from .db import get_connection
        with get_connection() as db:
            for ev in events:
                start = ev.get("start", {})
                end   = ev.get("end", {})
                start_at = start.get("dateTime") or (start.get("date", "") + "T00:00:00Z")
                end_at   = end.get("dateTime")   or (end.get("date", "")   + "T00:00:00Z")
                db.execute(
                    """INSERT INTO gcal_cache
                       (gcal_event_id, calendar_id, title, start_at, end_at,
                        description, location, fetched_at)
                       VALUES (?, 'primary', ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(gcal_event_id) DO UPDATE SET
                         title=excluded.title, start_at=excluded.start_at,
                         end_at=excluded.end_at, description=excluded.description,
                         location=excluded.location, fetched_at=excluded.fetched_at""",
                    (ev["id"], ev.get("summary", "(제목 없음)"),
                     start_at, end_at,
                     ev.get("description"), ev.get("location"), now_str),
                )
        log.info("GCal sync OK: %d events", len(events))

    except Exception as e:
        log.error("GCal sync error: %s", e)


# ── Folder auto-creation (FR-FILES-01) ──────────────────────────────────────

def _safe_seg(s: str) -> str:
    return "".join(c if c.isalnum() or c in " .-_" else "_" for c in (s or "")).strip() or "misc"


def ensure_org_folder(notes_root: str, org_name: str) -> str | None:
    """Create MC-Notes/{org}/ folder. Returns path or None. (B-005)"""
    if not notes_root:
        return None
    try:
        path = Path(notes_root) / _safe_seg(org_name)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    except Exception as e:
        log.warning("Org folder creation failed: %s", e)
        return None


def ensure_business_folder(notes_root: str, org_name: str, biz_name: str) -> str | None:
    """Create MC-Notes/{org}/{biz}/ folder. Returns path or None."""
    if not notes_root:
        return None
    try:
        path = Path(notes_root) / _safe_seg(org_name) / _safe_seg(biz_name)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    except Exception as e:
        log.warning("Business folder creation failed: %s", e)
        return None


def ensure_project_folder(notes_root: str, org_name: str, biz_name: str, proj_title: str) -> str | None:
    """Create MC-Notes/{org}/{biz}/{project}/ folder structure. Returns path or None."""
    if not notes_root:
        return None
    try:
        path = Path(notes_root) / _safe_seg(org_name) / _safe_seg(biz_name) / _safe_seg(proj_title)
        path.mkdir(parents=True, exist_ok=True)
        (path / "inbox").mkdir(exist_ok=True)
        return str(path)
    except Exception as e:
        log.warning("Folder creation failed: %s", e)
        return None
