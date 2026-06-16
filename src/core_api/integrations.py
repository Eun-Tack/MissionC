"""
Background integration tasks (FR-GIT-04, FR-INT-TG-01).
Started via APScheduler in main.py lifespan.
"""

from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone
from datetime import timedelta
from pathlib import Path

log = logging.getLogger("mc.integrations")
_sync_tasks: dict[str, asyncio.Task] = {}


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


def _record_integration_state(
    provider: str,
    status: str,
    *,
    error: str | None = None,
    success_at: str | None = None,
) -> None:
    try:
        from .db import get_connection

        now = _now()
        with get_connection() as db:
            db.execute(
                """
                INSERT INTO integration_state
                  (provider, status, last_success_at, last_error_at, last_error, last_run_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider) DO UPDATE SET
                  status=excluded.status,
                  last_success_at=COALESCE(excluded.last_success_at, integration_state.last_success_at),
                  last_error_at=COALESCE(excluded.last_error_at, integration_state.last_error_at),
                  last_error=CASE
                    WHEN excluded.status='ok' THEN NULL
                    WHEN excluded.last_error IS NOT NULL THEN excluded.last_error
                    ELSE integration_state.last_error
                  END,
                  last_run_at=excluded.last_run_at,
                  updated_at=excluded.updated_at
                """,
                (
                    provider,
                    status,
                    success_at,
                    now if error else None,
                    error[:500] if error else None,
                    now,
                    now,
                ),
            )
    except Exception as e:
        log.debug("integration state update failed for %s: %s", provider, e)


def schedule_integration_sync(provider: str, coro) -> bool:
    """Run an integration refresh without blocking the page request.

    Returns True when a new task was scheduled. If the same provider already
    has a live task, this call is skipped so repeated page visits do not stack
    network work.
    """
    existing = _sync_tasks.get(provider)
    if existing and not existing.done():
        coro.close()
        return False

    async def _runner():
        try:
            await coro
        except Exception as e:
            log.warning("%s background sync failed: %s", provider, e)
            _record_integration_state(provider, "error", error=str(e))
        finally:
            task = _sync_tasks.get(provider)
            if task is asyncio.current_task():
                _sync_tasks.pop(provider, None)

    try:
        _sync_tasks[provider] = asyncio.create_task(_runner())
        return True
    except RuntimeError:
        coro.close()
        log.warning("No running event loop for %s sync; skipping background refresh", provider)
        return False


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
        _record_integration_state("github", "not_configured")
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
            _record_integration_state("github", "ok", success_at=_now())
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
                        _record_integration_state("github", "error", error=f"{repo}: HTTP {r.status_code}")
                        continue

                    now = _now()
                    with get_connection() as db:
                        for issue in r.json():
                            item_type = "pr" if issue.get("pull_request") else "issue"
                            labels = [lbl.get("name", "") for lbl in issue.get("labels", []) if isinstance(lbl, dict)]
                            db.execute(
                                """INSERT INTO github_cache
                                   (repo, number, type, title, state, labels, html_url, fetched_at)
                                   VALUES (?,?,?,?,?,?,?,?)
                                   ON CONFLICT(repo, number, type) DO UPDATE SET
                                     title=excluded.title, state=excluded.state,
                                     labels=excluded.labels,
                                     html_url=excluded.html_url,
                                     fetched_at=excluded.fetched_at""",
                                (
                                    repo,
                                    issue["number"],
                                    item_type,
                                    issue["title"],
                                    issue["state"],
                                    ",".join(labels),
                                    issue["html_url"],
                                    now,
                                ),
                            )
                    log.info("GitHub sync OK: %s (%d issues)", repo, len(r.json()))
                    _record_integration_state("github", "ok", success_at=now)

                except Exception as e:
                    log.warning("GitHub sync error for %s: %s", repo, e)
                    _record_integration_state("github", "error", error=f"{repo}: {e}")

    except Exception as e:
        log.error("GitHub sync failed: %s", e)
        _record_integration_state("github", "error", error=str(e))


# ── Telegram polling (FR-INT-TG-01) ─────────────────────────────────────────

_tg_offset: int = 0


async def poll_telegram() -> None:
    """Poll Telegram bot for new messages → capture_inbox."""
    global _tg_offset
    token = _get_secret("MC_TG_BOT_TOKEN")
    if not token:
        _record_integration_state("telegram", "not_configured")
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
                _record_integration_state("telegram", "error", error=f"HTTP {r.status_code}: {r.text[:180]}")
                return

            updates = r.json().get("result", [])
            if not updates:
                _record_integration_state("telegram", "ok", success_at=_now())
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
            _record_integration_state("telegram", "ok", success_at=_now())

    except Exception as e:
        log.warning("Telegram poll error: %s", e)
        _record_integration_state("telegram", "error", error=str(e))


# ── Google Calendar sync (FR-CAL-02) ────────────────────────────────────────

async def _gcal_access_token() -> str | None:
    import os
    import httpx
    token_json = _get_secret("MC_GCAL_TOKEN")
    if not token_json:
        _record_integration_state("gcal", "not_configured")
        return None
    try:
        token_data = json.loads(token_json)
    except Exception:
        _record_integration_state("gcal", "error", error="Invalid token JSON")
        return None
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    client_id = os.environ.get("MC_GOOGLE_CLIENT_ID") or os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("MC_GOOGLE_CLIENT_SECRET") or os.environ.get("GOOGLE_CLIENT_SECRET", "")
    if not access_token and refresh_token and client_id:
        async with httpx.AsyncClient(timeout=10) as c:
            ref = await c.post("https://oauth2.googleapis.com/token", data={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
            })
        if ref.status_code != 200:
            _record_integration_state("gcal", "error", error=f"Token refresh failed HTTP {ref.status_code}")
            return None
        access_token = ref.json().get("access_token")
        token_data["access_token"] = access_token
        try:
            import keyring as kr
            kr.set_password("MC_GCAL_TOKEN", "iet03", json.dumps(token_data))
        except Exception:
            pass
    return access_token


def _clean_mobile_title(title: str) -> tuple[str, str | None]:
    raw = (title or "").strip()
    for marker, action in (
        ("[완료]", "mark_done"), ("[보류]", "mark_waiting"), ("[취소]", "cancel"),
        ("[DONE]", "mark_done"), ("[WAIT]", "mark_waiting"), ("[CANCEL]", "cancel"),
    ):
        if raw.upper().startswith(marker.upper()):
            return raw[len(marker):].strip() or raw, action
    return raw, None


def _queue_mobile_action(db, *, external_id: str, item_id: int | None, action: str,
                         title: str, old_value: str | None, new_value: str | None,
                         payload: dict) -> None:
    db.execute(
        """INSERT OR IGNORE INTO mobile_sync_actions
           (provider, external_id, item_id, action, title, old_value, new_value, payload)
           VALUES ('gcal', ?, ?, ?, ?, ?, ?, ?)""",
        (external_id, item_id, action, title, old_value, new_value, json.dumps(payload, ensure_ascii=False)),
    )


def _detect_gcal_mobile_changes(db, ev: dict, item_id: int | None, start_at: str, title: str) -> None:
    if not item_id:
        return
    item = db.execute(
        "SELECT id, title, status, scheduled_at, due_at, start_date, due_date FROM items WHERE id=?",
        (item_id,),
    ).fetchone()
    if not item:
        return
    clean_title, action = _clean_mobile_title(title)
    payload = {"event_id": ev.get("id"), "title": title, "start_at": start_at}
    if action == "mark_done" and item["status"] != "done":
        _queue_mobile_action(db, external_id=ev["id"], item_id=item_id, action="mark_done",
                             title=f"{clean_title} 완료", old_value=item["status"], new_value="done", payload=payload)
    elif action == "mark_waiting" and item["status"] != "waiting":
        _queue_mobile_action(db, external_id=ev["id"], item_id=item_id, action="mark_waiting",
                             title=f"{clean_title} 보류", old_value=item["status"], new_value="waiting", payload=payload)
    elif action == "cancel" and item["status"] != "cancelled":
        _queue_mobile_action(db, external_id=ev["id"], item_id=item_id, action="cancel",
                             title=f"{clean_title} 취소", old_value=item["status"], new_value="cancelled", payload=payload)
    current_date = (item["scheduled_at"] or item["due_at"] or item["start_date"] or item["due_date"] or "")[:10]
    next_date = (start_at or "")[:10]
    if current_date and next_date and current_date != next_date:
        _queue_mobile_action(db, external_id=ev["id"], item_id=item_id, action="reschedule",
                             title=f"{item['title']} 날짜 변경", old_value=current_date, new_value=next_date, payload=payload)


def _item_event_payload(row) -> dict | None:
    title = row["title"]
    if row["status"] == "done":
        title = f"[완료] {title}"
    elif row["status"] == "waiting":
        title = f"[보류] {title}"
    elif row["status"] == "cancelled":
        title = f"[취소] {title}"
    if row["scheduled_at"]:
        start = {"dateTime": row["scheduled_at"]}
        end_value = row["due_at"] or row["scheduled_at"]
        if end_value == row["scheduled_at"]:
            end_value = (datetime.fromisoformat(row["scheduled_at"].replace("Z", "+00:00")) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        end = {"dateTime": end_value}
    elif row["due_at"]:
        title = f"[마감] {title}"
        start = {"dateTime": row["due_at"]}
        end = {"dateTime": (datetime.fromisoformat(row["due_at"].replace("Z", "+00:00")) + timedelta(minutes=15)).isoformat().replace("+00:00", "Z")}
    elif row["start_date"] or row["due_date"]:
        start_date = row["start_date"] or row["due_date"]
        due_date = row["due_date"] or row["start_date"]
        end = {"date": (datetime.fromisoformat(due_date).date() + timedelta(days=1)).isoformat()}
        start = {"date": start_date}
    else:
        return None
    return {
        "summary": title,
        "start": start,
        "end": end,
        "description": f"MC item #{row['id']}\n모바일에서는 제목 앞에 [완료], [보류], [취소]를 붙이면 PC 정산 큐에 올라옵니다.",
        "extendedProperties": {"private": {
            "mc_item_id": str(row["id"]),
            "mc_kind": row["type"] or "task",
            "mc_status": row["status"],
            "mc_source": "missionc",
        }},
    }


async def sync_item_to_gcal(item_id: int) -> None:
    """Push one MC item to Google Calendar as a mobile-facing event."""
    import httpx
    from .db import get_connection

    token = await _gcal_access_token()
    if not token:
        return
    with get_connection() as db:
        row = db.execute(
            "SELECT id, type, title, status, scheduled_at, due_at, start_date, due_date FROM items WHERE id=?",
            (item_id,),
        ).fetchone()
        if not row:
            return
        payload = _item_event_payload(row)
        existing = db.execute(
            "SELECT gcal_event_id FROM gcal_cache WHERE mc_item_id=? ORDER BY fetched_at DESC LIMIT 1",
            (item_id,),
        ).fetchone()
    if not payload:
        return
    event_id = existing["gcal_event_id"] if existing else None
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    if event_id:
        url += f"/{event_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.request("PATCH" if event_id else "POST", url, headers={"Authorization": f"Bearer {token}"}, json=payload)
    if res.status_code not in (200, 201):
        _record_integration_state("gcal", "error", error=f"item {item_id} write HTTP {res.status_code}: {res.text[:180]}")
        return
    ev = res.json()
    start = ev.get("start", {})
    end = ev.get("end", {})
    start_at = start.get("dateTime") or (start.get("date", "") + "T00:00:00Z")
    end_at = end.get("dateTime") or (end.get("date", "") + "T00:00:00Z")
    with get_connection() as db:
        db.execute(
            """INSERT INTO gcal_cache
               (gcal_event_id, calendar_id, title, start_at, end_at, description, location,
                mc_item_id, mc_kind, mc_last_seen_status, fetched_at)
               VALUES (?, 'primary', ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(gcal_event_id) DO UPDATE SET
                 title=excluded.title, start_at=excluded.start_at, end_at=excluded.end_at,
                 description=excluded.description, location=excluded.location,
                 mc_item_id=excluded.mc_item_id, mc_kind=excluded.mc_kind,
                 mc_last_seen_status=excluded.mc_last_seen_status,
                 fetched_at=excluded.fetched_at""",
            (ev["id"], ev.get("summary", payload["summary"]), start_at, end_at,
             ev.get("description"), ev.get("location"), item_id, row["type"], row["status"], _now()),
        )
    _record_integration_state("gcal", "ok", success_at=_now())


async def sync_gcal() -> None:
    """Fetch GCal events (±7d / +30d window) → gcal_cache."""
    import json, os
    token_json = _get_secret("MC_GCAL_TOKEN")
    if not token_json:
        _record_integration_state("gcal", "not_configured")
        return

    try:
        token_data = json.loads(token_json)
    except Exception:
        _record_integration_state("gcal", "error", error="Invalid token JSON")
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
                _record_integration_state("gcal", "error", error=f"Token refresh failed HTTP {ref.status_code}")
                return

        if r.status_code != 200:
            log.warning("GCal sync failed: %s", r.status_code)
            _record_integration_state("gcal", "error", error=f"HTTP {r.status_code}: {r.text[:200]}")
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
                private_props = (ev.get("extendedProperties") or {}).get("private") or {}
                try:
                    mc_item_id = int(private_props.get("mc_item_id")) if private_props.get("mc_item_id") else None
                except (TypeError, ValueError):
                    mc_item_id = None
                title = ev.get("summary", "(제목 없음)")
                _detect_gcal_mobile_changes(db, ev, mc_item_id, start_at, title)
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
        _record_integration_state("gcal", "ok", success_at=now_str)

    except Exception as e:
        log.error("GCal sync error: %s", e)
        _record_integration_state("gcal", "error", error=str(e))


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
