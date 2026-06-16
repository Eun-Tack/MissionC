"""
CRUD endpoints for items — FR-CAP-01, FR-CAP-02, FR-LABEL-01, FR-BACKUP-01.

POST   /api/items
PATCH  /api/items/{id}
DELETE /api/items/{id}
POST   /api/items/{id}/tags
DELETE /api/items/{id}/tags/{tag_id}
POST   /api/items/{id}/files
DELETE /api/items/{id}/files
GET    /api/labels
POST   /api/items/{id}/labels
DELETE /api/items/{id}/labels/{label_id}
POST   /api/carry-over
GET    /api/export
"""

from __future__ import annotations
import calendar as _calendar
import json
import sqlite3
from datetime import datetime, date, timedelta, timezone
from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from ..db import get_db

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


_VALID_RECURRENCE = {"DAILY", "WEEKDAYS", "WEEKLY", "MONTHLY"}
_TITLE_MAX = 10000


def _normalize_due_at(value: str | None) -> str | None:
    if value is None:
        return None
    val = value.strip()
    if not val:
        return None
    if "T" not in val and len(val) == 10:
        return f"{val}T23:59:00Z"
    if "T" in val and not val.endswith("Z"):
        return val + ":00Z" if len(val) == 16 else val
    return val


def _normalize_datetime(value: str | None, *, default_time: str = "00:00:00Z") -> str | None:
    if value is None:
        return None
    val = value.strip()
    if not val:
        return None
    if "T" not in val and len(val) == 10:
        return f"{val}T{default_time}"
    if "T" in val and not val.endswith("Z"):
        return val + ":00Z" if len(val) == 16 else val
    return val


def _sync_schedule_row(
    db: sqlite3.Connection,
    item_id: int,
    item_type: str,
    scheduled_at: str | None,
    end_at: str | None = None,
    *,
    end_at_provided: bool = False,
) -> None:
    """Keep schedules.start_at/end_at aligned with item schedule fields."""
    if not scheduled_at:
        db.execute("DELETE FROM schedules WHERE item_id=?", (item_id,))
        return
    if item_type != "schedule":
        return
    existing = db.execute(
        "SELECT id, end_at FROM schedules WHERE item_id=? ORDER BY start_at ASC LIMIT 1",
        (item_id,),
    ).fetchone()
    if existing:
        next_end = end_at if end_at_provided else existing["end_at"]
        db.execute("UPDATE schedules SET start_at=?, end_at=? WHERE id=?", (scheduled_at, next_end, existing["id"]))
    else:
        db.execute(
            "INSERT INTO schedules (item_id, start_at, end_at) VALUES (?, ?, ?)",
            (item_id, scheduled_at, end_at if end_at_provided else None),
        )


def _check_title(title: str) -> str:
    """Validate and trim title — raises 422 if too long. (B-003)"""
    t = (title or "").strip()
    if not t:
        raise HTTPException(422, "Title required")
    if len(t) > _TITLE_MAX:
        raise HTTPException(422, f"Title too long (max {_TITLE_MAX} chars, got {len(t)})")
    return t


def _schedule_item_gcal_sync(item_id: int) -> None:
    try:
        from ..integrations import _record_integration_state, schedule_integration_sync, sync_item_to_gcal

        async def _run():
            try:
                await sync_item_to_gcal(item_id)
            except Exception as e:
                _record_integration_state("gcal", "error", error=f"item {item_id}: {e}")
                raise

        schedule_integration_sync(f"gcal:item:{item_id}", _run())
    except Exception:
        return


def _new_item_snippet(item_id: int, title: str, status: str = "todo") -> str:
    return f"""
<div id="anytime-list" hx-swap-oob="afterbegin">
  <div class="row" id="item-{item_id}"
       hx-get="/partial/context/{item_id}"
       hx-target="#context-panel"
       hx-swap="innerHTML">
    <span class="time">·</span>
    <span class="dot-wrap"><span id="dot-{item_id}"><span class="mc-dot" data-status="{escape(status)}"></span></span></span>
    <span class="icon">□</span>
    <div class="body">
      <div class="title">{escape(title)}</div>
    </div>
  </div>
</div>
"""


def _next_recurrence_date(current: str | None, rule: str) -> str | None:
    """Compute next occurrence date string (YYYY-MM-DD) given a date ref and rule."""
    if not current:
        current = date.today().isoformat()
    try:
        d = date.fromisoformat(current[:10])
    except (ValueError, TypeError):
        d = date.today()
    rule = rule.upper().strip()
    if rule == "DAILY":
        return (d + timedelta(days=1)).isoformat()
    if rule == "WEEKDAYS":
        nxt = d + timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
        return nxt.isoformat()
    if rule == "WEEKLY":
        return (d + timedelta(weeks=1)).isoformat()
    if rule == "MONTHLY":
        m = d.month + 1
        y = d.year
        if m > 12:
            m, y = 1, y + 1
        max_day = _calendar.monthrange(y, m)[1]
        return date(y, m, min(d.day, max_day)).isoformat()
    return None


def _sync_parent_date_bounds(db: sqlite3.Connection, item_id: int) -> str:
    """Expand a parent item date range when a child lies outside it."""
    child = db.execute(
        "SELECT parent_id, start_date, due_date, scheduled_at, due_at FROM items WHERE id=?",
        (item_id,),
    ).fetchone()
    if not child or not child["parent_id"]:
        return ""

    parent_id = child["parent_id"]
    bounds = db.execute(
        """
        SELECT
          MIN(COALESCE(start_date, due_date, scheduled_at, due_at)) AS min_start,
          MAX(COALESCE(due_at, due_date, start_date, scheduled_at)) AS max_end
        FROM items
        WHERE parent_id=? AND status != 'cancelled'
        """,
        (parent_id,),
    ).fetchone()
    if not bounds or (not bounds["min_start"] and not bounds["max_end"]):
        return ""

    parent = db.execute(
        "SELECT start_date, due_date FROM items WHERE id=?",
        (parent_id,),
    ).fetchone()
    if not parent:
        return ""

    min_start = bounds["min_start"][:10] if bounds["min_start"] else None
    max_end = bounds["max_end"][:10] if bounds["max_end"] else None
    next_start = parent["start_date"]
    next_due = parent["due_date"]
    changed = []

    if min_start and (not next_start or min_start < next_start):
        next_start = min_start
        changed.append(f"시작 {min_start}")
    if max_end and (not next_due or max_end > next_due):
        next_due = max_end
        changed.append(f"마감 {max_end}")

    if not changed:
        return ""

    db.execute(
        "UPDATE items SET start_date=?, due_date=?, updated_at=? WHERE id=?",
        (next_start, next_due, _now_iso(), parent_id),
    )
    return "상위 할 일 일정 자동 조정: " + ", ".join(changed)


# ── Items CRUD ────────────────────────────────────────────────────────────────

@router.post("/api/items", response_class=HTMLResponse)
async def create_item(
    title: Annotated[str, Form()],
    type_: Annotated[str, Form(alias="type")] = "task",
    scheduled_at: Annotated[str | None, Form()] = None,
    end_at: Annotated[str | None, Form()] = None,
    body: Annotated[str | None, Form()] = None,
    project_id: Annotated[int | None, Form()] = None,
    parent_id: Annotated[int | None, Form()] = None,
    start_date: Annotated[str | None, Form()] = None,
    due_date: Annotated[str | None, Form()] = None,
    due_at: Annotated[str | None, Form()] = None,
    recurrence_rule: Annotated[str | None, Form()] = None,
    recurrence_parent_id: Annotated[int | None, Form()] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Create an item from Quick Capture or project page (FR-CAP-01)."""
    if type_ not in ("schedule", "task", "memo", "project_ref"):
        raise HTTPException(422, "Invalid item type")
    rule = (recurrence_rule or "").upper().strip() or None
    if rule and rule not in _VALID_RECURRENCE:
        raise HTTPException(422, "Invalid recurrence_rule")

    title_clean = _check_title(title)
    scheduled_at_norm = _normalize_datetime(scheduled_at)
    end_at_norm = _normalize_datetime(end_at)
    due_at_norm = _normalize_due_at(due_at)
    duplicate = db.execute(
        """SELECT i.id, i.status
           FROM items i
           LEFT JOIN schedules s ON s.item_id=i.id
           WHERE i.status != 'cancelled'
             AND i.type = ?
             AND i.title = ?
             AND COALESCE(i.parent_id, -1) = COALESCE(?, -1)
             AND COALESCE(i.scheduled_at, '') = COALESCE(?, '')
             AND COALESCE(i.due_at, '') = COALESCE(?, '')
             AND COALESCE(i.start_date, '') = COALESCE(?, '')
             AND COALESCE(i.due_date, '') = COALESCE(?, '')
           ORDER BY i.id ASC
           LIMIT 1""",
        (type_, title_clean, parent_id, scheduled_at_norm, due_at_norm, start_date or None, due_date or None),
    ).fetchone()
    if duplicate:
        if project_id:
            db.execute(
                "INSERT OR IGNORE INTO item_projects(item_id, project_id) VALUES(?,?)",
                (duplicate["id"], project_id),
            )
        if scheduled_at_norm and (type_ == "schedule" or end_at_norm):
            _sync_schedule_row(
                db,
                duplicate["id"],
                type_,
                scheduled_at_norm,
                end_at_norm,
                end_at_provided=end_at is not None,
            )
        return HTMLResponse(_new_item_snippet(duplicate["id"], title_clean, duplicate["status"]))

    now = _now_iso()
    cur = db.execute(
        """INSERT INTO items (type, title, body, body_inline, status, location,
                              scheduled_at, due_at, parent_id, start_date, due_date,
                              recurrence_rule, recurrence_parent_id,
                              created_at, updated_at, source)
           VALUES (?, ?, ?, 0, 'todo', 'hot', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual')""",
        (type_, title_clean, body, scheduled_at_norm, due_at_norm, parent_id,
         start_date or None, due_date or None,
         rule, recurrence_parent_id,
         now, now),
    )
    item_id = cur.lastrowid

    # If subtask of a parent that's linked to a project, inherit the link
    if parent_id and not project_id:
        parent_proj = db.execute(
            "SELECT project_id FROM item_projects WHERE item_id=? LIMIT 1",
            (parent_id,),
        ).fetchone()
        if parent_proj:
            project_id = parent_proj[0]

    if project_id:
        db.execute(
            "INSERT OR IGNORE INTO item_projects(item_id, project_id) VALUES(?,?)",
            (item_id, project_id),
        )

    # Create schedules row so end_at is available in calendar JOIN
    if scheduled_at_norm and (type_ == "schedule" or end_at_norm):
        db.execute(
            "INSERT INTO schedules (item_id, start_at, end_at) VALUES (?, ?, ?)",
            (item_id, scheduled_at_norm, end_at_norm),
        )
    if scheduled_at_norm or due_at_norm or start_date or due_date:
        db.commit()
        _schedule_item_gcal_sync(item_id)

    snippet = f"""
<div id="anytime-list" hx-swap-oob="afterbegin">
  <div class="row" id="item-{item_id}"
       hx-get="/partial/context/{item_id}"
       hx-target="#context-panel"
       hx-swap="innerHTML">
    <span class="time">—</span>
    <span class="dot-wrap"><span id="dot-{item_id}"><span class="mc-dot" data-status="todo"></span></span></span>
    <span class="icon">☐</span>
    <div class="body">
      <div class="title">{escape(title_clean)}</div>
    </div>
  </div>
</div>
"""
    return HTMLResponse(_new_item_snippet(item_id, title_clean))


@router.patch("/api/items/{item_id}", response_class=HTMLResponse)
async def update_item(
    request: Request,
    item_id: int,
    status: Annotated[str | None, Form()] = None,
    title: Annotated[str | None, Form()] = None,
    body: Annotated[str | None, Form()] = None,
    scheduled_at: Annotated[str | None, Form()] = None,
    end_at: Annotated[str | None, Form()] = None,
    start_date: Annotated[str | None, Form()] = None,
    due_date: Annotated[str | None, Form()] = None,
    due_at: Annotated[str | None, Form()] = None,
    recurrence_rule: Annotated[str | None, Form()] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Inline edit — title/status/body/dates/recurrence (FR-CAP-01 AC-3)."""
    row = db.execute(
        """SELECT i.id, i.status, i.title, i.type, i.scheduled_at, i.due_at,
                  i.due_date, i.start_date, i.parent_id, i.recurrence_rule, i.body,
                  s.end_at
           FROM items i
           LEFT JOIN schedules s ON s.item_id=i.id
           WHERE i.id = ?""",
        (item_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Item not found")
    row_d = dict(row)

    updates, params = [], []
    if status is not None:
        if status not in ("todo", "doing", "in_progress", "done", "waiting", "cancelled"):
            raise HTTPException(422, "Invalid status")
        # Normalize in_progress → doing (in_progress is legacy alias)
        updates.append("status = ?")
        params.append("doing" if status == "in_progress" else status)
    if title is not None and title.strip():
        title_clean = _check_title(title)
        updates.append("title = ?")
        params.append(title_clean)
    if body is not None:
        updates.append("body = ?")
        params.append(body.strip() or None)
    if scheduled_at is not None:
        val = _normalize_datetime(scheduled_at)
        updates.append("scheduled_at = ?")
        params.append(val or None)
        row_d["scheduled_at"] = val
    if end_at is not None:
        row_d["end_at"] = _normalize_datetime(end_at)
    if due_at is not None:
        val = _normalize_due_at(due_at)
        updates.append("due_at = ?")
        params.append(val or None)
    if start_date is not None:
        updates.append("start_date = ?")
        params.append(start_date.strip() or None)
    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date.strip() or None)
    if recurrence_rule is not None:
        rule = recurrence_rule.upper().strip() or None
        if rule and rule not in _VALID_RECURRENCE:
            raise HTTPException(422, "Invalid recurrence_rule")
        updates.append("recurrence_rule = ?")
        params.append(rule)
        row_d["recurrence_rule"] = rule  # reflect immediately

    if updates:
        updates.append("updated_at = ?")
        params.extend([_now_iso(), item_id])
        db.execute(f"UPDATE items SET {', '.join(updates)} WHERE id = ?", params)
        if scheduled_at is not None or end_at is not None:
            _sync_schedule_row(
                db,
                item_id,
                row_d["type"],
                row_d.get("scheduled_at"),
                row_d.get("end_at"),
                end_at_provided=end_at is not None,
            )
        parent_date_msg = _sync_parent_date_bounds(db, item_id)
        if any(v is not None for v in (status, title, scheduled_at, end_at, start_date, due_date, due_at)):
            db.commit()
            _schedule_item_gcal_sync(item_id)
    elif end_at is not None:
        _sync_schedule_row(
            db,
            item_id,
            row_d["type"],
            row_d.get("scheduled_at"),
            row_d.get("end_at"),
            end_at_provided=True,
        )
        parent_date_msg = ""
        db.commit()
        _schedule_item_gcal_sync(item_id)
    else:
        parent_date_msg = ""

    new_status = status or row_d["status"]
    extra_oob = ""

    # Only include flow-page OOB swaps when the request comes from the flow page
    hx_url = request.headers.get("hx-current-url", "")
    on_flow_page = hx_url.rstrip("/").split("?")[0].endswith(":8000") or hx_url.split("?")[0].endswith("/")

    # Auto-spawn next occurrence when completing a recurring item
    effective_rule = row_d.get("recurrence_rule")
    if new_status == "done" and effective_rule:
        ref_date = (
            row_d.get("scheduled_at") or row_d.get("due_date") or row_d.get("start_date")
        )
        next_date = _next_recurrence_date(ref_date, effective_rule)
        if next_date:
            now = _now_iso()
            new_sched = f"{next_date}T09:00:00Z" if row_d.get("scheduled_at") else None
            new_due = next_date if row_d.get("due_date") else None
            new_start = next_date if row_d.get("start_date") else None
            cur2 = db.execute(
                """INSERT INTO items (type, title, body, body_inline, status, location,
                                     scheduled_at, start_date, due_date,
                                     recurrence_rule, recurrence_parent_id,
                                     created_at, updated_at, source)
                   VALUES (?, ?, ?, 0, 'todo', 'hot', ?, ?, ?, ?, ?, ?, ?, 'recurrence')""",
                (row_d["type"], row_d["title"], row_d["body"],
                 new_sched, new_start, new_due,
                 effective_rule, item_id, now, now),
            )
            new_id = cur2.lastrowid
            # Copy project link
            proj = db.execute(
                "SELECT project_id FROM item_projects WHERE item_id=? LIMIT 1", (item_id,)
            ).fetchone()
            if proj:
                db.execute(
                    "INSERT OR IGNORE INTO item_projects(item_id, project_id) VALUES(?,?)",
                    (new_id, proj[0]),
                )
            rule_label = {"DAILY": "매일", "WEEKDAYS": "평일", "WEEKLY": "매주", "MONTHLY": "매월"}.get(
                effective_rule, effective_rule
            )
            month, day = next_date[5:7], next_date[8:10]
            toast_msg = f"✓ 완료 · 다음 반복 {month}/{day}"
            extra_oob = f'<span id="ctx-toast-{item_id}" hx-swap-oob="true" class="ctx-toast show">{toast_msg}</span>'
            if on_flow_page:
                extra_oob = f"""
<div id="anytime-list" hx-swap-oob="afterbegin">
  <div class="row recurrence-new" id="item-{new_id}"
       hx-get="/partial/context/{new_id}"
       hx-target="#context-panel" hx-swap="innerHTML">
    <span class="time">—</span>
    <span class="dot-wrap"><span id="dot-{new_id}"><span class="mc-dot" data-status="todo"></span></span></span>
    <span class="icon">🔄</span>
    <div class="body">
      <div class="title">{escape(row_d['title'])}</div>
      <div class="meta-row" style="font-size:10px; color:var(--muted);">{rule_label} · 다음 {month}/{day}</div>
    </div>
  </div>
</div>
<span id="ctx-toast-{item_id}" hx-swap-oob="true" class="ctx-toast show">{toast_msg}</span>
"""

    # dot OOB: only include when on flow page (avoids insertBefore null on other pages)
    dot_oob = ""
    if on_flow_page:
        dot_oob = f'<span id="dot-{item_id}" hx-swap-oob="true"><span class="mc-dot" data-status="{new_status}"></span></span>'

    status_marker = f'<span hidden data-status="{escape(new_status)}">{escape(new_status)}</span>'
    parent_msg_html = (
        f'<span id="ctx-toast-{item_id}" hx-swap-oob="true" class="ctx-toast show">{escape(parent_date_msg)}</span>'
        if parent_date_msg else ""
    )
    return HTMLResponse(f"{dot_oob}\n{extra_oob}\n{parent_msg_html}\n{status_marker}")


# ── Project linking (FR-CAP-01 AC-5) ─────────────────────────────────────────

@router.post("/api/items/{item_id}/project", response_class=HTMLResponse)
async def link_project(
    item_id: int,
    project_id: Annotated[int, Form()],
    db: sqlite3.Connection = Depends(get_db),
):
    """Link an item to a project (replaces existing link)."""
    if not db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
        raise HTTPException(404, "Project not found")
    db.execute("DELETE FROM item_projects WHERE item_id=?", (item_id,))
    db.execute(
        "INSERT OR IGNORE INTO item_projects(item_id, project_id) VALUES(?,?)",
        (item_id, project_id),
    )
    proj = db.execute(
        "SELECT title FROM projects WHERE id=?", (project_id,)
    ).fetchone()
    return HTMLResponse(
        f'<span style="font-size:12px; color:var(--st-done);">✓ "{proj["title"]}"에 연결됨</span>'
    )


@router.delete("/api/items/{item_id}/project", response_class=HTMLResponse)
async def unlink_project(item_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Remove all project links for this item."""
    db.execute("DELETE FROM item_projects WHERE item_id=?", (item_id,))
    return HTMLResponse('<span style="font-size:12px; color:var(--muted);">연결 해제됨</span>')


# ── Hierarchical sub-tasks (v1.6) ────────────────────────────────────────────

def _render_subtasks(parent_id: int, db: sqlite3.Connection) -> HTMLResponse:
    rows = db.execute(
        """SELECT id, title, status, scheduled_at, due_at, due_date, start_date
           FROM items
           WHERE parent_id = ? AND status != 'cancelled'
           ORDER BY status='done' ASC,
                    COALESCE(due_at, due_date, '9999') ASC,
                    created_at ASC""",
        (parent_id,),
    ).fetchall()

    total = len(rows)
    done = sum(1 for r in rows if r["status"] == "done")
    pct = round(done * 100 / total) if total else 0
    reload_attr = (
        f"htmx.ajax('GET','/api/items/{parent_id}/subtasks',"
        f"{{target:'#subtasks-{parent_id}',swap:'innerHTML'}})"
    )
    reload_html = escape(reload_attr, quote=True)

    parts = [
        f'<div data-pct="{pct}" data-total="{total}" data-done="{done}">',
        '<div class="sub-progress-row">'
        f'<span class="sub-progress-label">{done}/{total} 완료</span>'
        f'<span class="sub-progress-pct">{pct}%</span>'
        '</div>',
        f'<div class="sub-progress-bar"><div class="sub-progress-fill" style="width:{pct}%"></div></div>',
    ]
    if rows:
        parts.append('<div class="sub-list">')
        for r in rows:
            d = dict(r)
            done_cls = " sub-done" if d["status"] == "done" else ""
            next_status = "todo" if d["status"] == "done" else "done"
            start_value = escape(d.get("start_date") or "", quote=True)
            due_value = escape(d.get("due_date") or "", quote=True)
            due_at_value = escape((d.get("due_at") or "")[:16], quote=True)
            due = f' · 마감 {escape(d["due_date"])}' if d.get("due_date") else ""
            due_time = f' {escape(d["due_at"][11:16])}' if d.get("due_at") else ""
            is_overdue = (
                d["status"] not in ("done", "cancelled")
                and (
                    (d.get("due_at") and d["due_at"][:10] < date.today().isoformat())
                    or (d.get("due_date") and d["due_date"] < date.today().isoformat())
                )
            )
            status_label = "지연" if is_overdue else {"todo": "대기", "doing": "진행", "waiting": "보류", "done": "완료"}.get(d["status"], d["status"])
            parts.append(
                f'<div class="sub-item sub-item-detail{done_cls}" id="sub-{d["id"]}">'
                f'<button class="sub-check" hx-patch="/api/items/{d["id"]}" '
                f'hx-vals=\'{{"status":"{next_status}"}}\' hx-swap="none" hx-on::after-request="{reload_html}">'
                f'{"✓" if d["status"] == "done" else "○"}</button>'
                '<div class="sub-main">'
                f'<input class="sub-title-input" name="title" value="{escape(d["title"], quote=True)}" '
                f'hx-patch="/api/items/{d["id"]}" hx-trigger="change" hx-include="this" hx-swap="none" hx-on::after-request="{reload_html}">'
                '<div class="sub-controls">'
                f'<select name="status" class="sub-status-select" hx-patch="/api/items/{d["id"]}" hx-trigger="change" hx-include="this" hx-swap="none" hx-on::after-request="{reload_html}">'
                f'<option value="todo" {"selected" if d["status"] == "todo" else ""}>대기</option>'
                f'<option value="doing" {"selected" if d["status"] == "doing" else ""}>진행</option>'
                f'<option value="waiting" {"selected" if d["status"] == "waiting" else ""}>보류</option>'
                f'<option value="done" {"selected" if d["status"] == "done" else ""}>완료</option>'
                '<option value="cancelled">취소</option>'
                '</select>'
                f'<input type="date" name="start_date" value="{start_value}" title="시작" '
                f'hx-patch="/api/items/{d["id"]}" hx-trigger="change" hx-include="this" hx-swap="none" hx-on::after-request="{reload_html}">'
                f'<input type="date" name="due_date" value="{due_value}" title="마감일" '
                f'hx-patch="/api/items/{d["id"]}" hx-trigger="change" hx-include="this" hx-swap="none" hx-on::after-request="{reload_html}">'
                f'<input type="datetime-local" name="due_at" value="{due_at_value}" title="마감 시간" '
                f'hx-patch="/api/items/{d["id"]}" hx-trigger="change" hx-include="this" hx-swap="none" hx-on::after-request="{reload_html}">'
                '</div>'
                f'<span class="sub-meta">{escape(status_label)}{due}{due_time}</span>'
                '</div>'
                f'<button class="sub-x" hx-delete="/api/items/{d["id"]}" hx-confirm="삭제?" '
                f'hx-swap="none" hx-on::after-request="{reload_html}">×</button>'
                '</div>'
            )
        parts.append('</div>')
    else:
        parts.append('<div style="font-size:12px; color:var(--muted); padding:8px 0;">하위 작업이 없습니다</div>')

    parts.append('</div>')
    return HTMLResponse("\n".join(parts))


@router.get("/api/items/{parent_id}/subtasks", response_class=HTMLResponse)
async def list_subtasks(
    parent_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    """Return HTML partial of sub-tasks for inline rendering in Context Panel."""
    return _render_subtasks(parent_id, db)
    rows = db.execute(
        """SELECT id, title, status, scheduled_at, due_at, due_date, start_date
           FROM items
           WHERE parent_id = ? AND status != 'cancelled'
           ORDER BY status='done' ASC,
                    COALESCE(due_at, due_date, '9999') ASC,
                    created_at ASC""",
        (parent_id,),
    ).fetchall()

    total = len(rows)
    done = sum(1 for r in rows if r["status"] == "done")
    pct = round(done * 100 / total) if total else 0

    parts = [
        f'<div data-pct="{pct}" data-total="{total}" data-done="{done}">',
        f'<div class="sub-progress-row">'
        f'<span class="sub-progress-label">{done}/{total} 완료</span>'
        f'<span class="sub-progress-pct">{pct}%</span>'
        f'</div>',
        f'<div class="sub-progress-bar"><div class="sub-progress-fill" style="width:{pct}%"></div></div>',
    ]
    if rows:
        parts.append('<div class="sub-list">')
        for r in rows:
            d = dict(r)
            done_cls = " sub-done" if d["status"] == "done" else ""
            next_status = "todo" if d["status"] == "done" else "done"
            due = f' · 📅 {d["due_date"]}' if d.get("due_date") else ""
            parts.append(
                f'<div class="sub-item{done_cls}" id="sub-{d["id"]}">'
                f'<button class="sub-check" '
                f'hx-patch="/api/items/{d["id"]}" '
                f'hx-vals=\'{{"status":"{next_status}"}}\' '
                f'hx-swap="none" '
                f'hx-on::after-request="htmx.ajax(\'GET\',\'/api/items/{parent_id}/subtasks\',{{target:\'#subtasks-{parent_id}\',swap:\'innerHTML\'}})">'
                f'{"✓" if d["status"] == "done" else "○"}</button>'
                f'<span class="sub-title">{d["title"]}</span>'
                f'<span class="sub-meta">{due}</span>'
                f'<button class="sub-x" '
                f'hx-delete="/api/items/{d["id"]}" '
                f'hx-confirm="삭제?" '
                f'hx-swap="none" '
                f'hx-on::after-request="htmx.ajax(\'GET\',\'/api/items/{parent_id}/subtasks\',{{target:\'#subtasks-{parent_id}\',swap:\'innerHTML\'}})">×</button>'
                f'</div>'
            )
        parts.append('</div>')
    else:
        parts.append('<div style="font-size:12px; color:var(--muted); padding:8px 0;">하위 항목이 없습니다</div>')

    parts.append('</div>')
    return HTMLResponse("\n".join(parts))


@router.post("/api/items/{parent_id}/subtasks", response_class=HTMLResponse)
async def create_subtask(
    parent_id: int,
    title: Annotated[str, Form()],
    start_date: Annotated[str | None, Form()] = None,
    due_date: Annotated[str | None, Form()] = None,
    due_at: Annotated[str | None, Form()] = None,
    body: Annotated[str | None, Form()] = None,
    assignee_name: Annotated[str | None, Form()] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Create a child item under parent_id, inheriting parent's project."""
    if not db.execute("SELECT 1 FROM items WHERE id=?", (parent_id,)).fetchone():
        raise HTTPException(404, "Parent item not found")
    title_clean = _check_title(title)

    now = _now_iso()
    cur = db.execute(
        """INSERT INTO items (type, title, body, body_inline, status, location,
                              parent_id, start_date, due_date, due_at, created_at, updated_at, source)
           VALUES ('task', ?, ?, 0, 'todo', 'hot', ?, ?, ?, ?, ?, ?, 'manual')""",
        (title_clean, body or None, parent_id, start_date or None, due_date or None, _normalize_due_at(due_at), now, now),
    )
    new_id = cur.lastrowid

    if assignee_name and assignee_name.strip():
        assignee = assignee_name.strip()
        existing = db.execute(
            "SELECT id FROM contacts WHERE name=? COLLATE NOCASE LIMIT 1",
            (assignee,),
        ).fetchone()
        contact_id = existing["id"] if existing else db.execute(
            "INSERT INTO contacts(name) VALUES(?)",
            (assignee,),
        ).lastrowid
        db.execute(
            "INSERT OR IGNORE INTO item_contacts(item_id, contact_id, role) VALUES(?,?,?)",
            (new_id, contact_id, "assignee"),
        )

    # Inherit parent's project link
    parent_proj = db.execute(
        "SELECT project_id FROM item_projects WHERE item_id=? LIMIT 1",
        (parent_id,),
    ).fetchone()
    if parent_proj:
        db.execute(
            "INSERT OR IGNORE INTO item_projects(item_id, project_id) VALUES(?,?)",
            (new_id, parent_proj[0]),
        )

    _sync_parent_date_bounds(db, new_id)

    # Re-render the subtasks list
    return await list_subtasks(parent_id, db=db)


# ── File / memo attachment ───────────────────────────────────────────────────

@router.post("/api/items/{item_id}/files", response_class=HTMLResponse)
async def attach_file(
    item_id: int,
    path: Annotated[str, Form()],
    db: sqlite3.Connection = Depends(get_db),
):
    """Attach a local file path to an item (manual file_index entry)."""
    if not db.execute("SELECT 1 FROM items WHERE id=?", (item_id,)).fetchone():
        raise HTTPException(404, "item not found")
    p = path.strip()
    if not p:
        raise HTTPException(422, "path required")
    db.execute(
        "INSERT OR IGNORE INTO file_index (path, item_id, state) VALUES (?, ?, 'present')",
        (p, item_id),
    )
    db.commit()
    return _render_memos_html(item_id, db)


@router.delete("/api/items/{item_id}/files", response_class=HTMLResponse)
async def detach_file(
    item_id: int,
    path: Annotated[str, Form()],
    db: sqlite3.Connection = Depends(get_db),
):
    """Remove a file_index entry from an item."""
    db.execute(
        "UPDATE file_index SET item_id=NULL WHERE path=? AND item_id=?",
        (path.strip(), item_id),
    )
    db.commit()
    return _render_memos_html(item_id, db)


def _render_memos_html(item_id: int, db: sqlite3.Connection) -> HTMLResponse:
    memos = db.execute(
        "SELECT path, evolution_count FROM file_index WHERE item_id=? ORDER BY rowid DESC",
        (item_id,),
    ).fetchall()
    rows = []
    for m in memos:
        fname = m["path"].replace("\\", "/").split("/")[-1]
        evo = ""
        if m["evolution_count"] and m["evolution_count"] >= 3:
            evo = (
                f'<span style="font-size:9px; color:var(--brand); font-weight:700; '
                f'background:var(--brand-soft); padding:1px 5px; border-radius:4px;" '
                f'title="evolution {m["evolution_count"]}">×{m["evolution_count"]}</span>'
            )
        rows.append(
            f'<div style="display:flex; align-items:center; gap:6px; padding:4px 0; font-size:12px;">'
            f'<span style="color:var(--muted);">📄</span>'
            f'<span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" '
            f'title="{escape(m["path"])}">{escape(fname)}</span>'
            f'{evo}'
            f'<button style="font-size:10px; color:var(--muted); background:none; border:none; '
            f'cursor:pointer; padding:0 4px;" '
            f'hx-delete="/api/items/{item_id}/files" '
            f'hx-vals=\'{{"path":"{escape(m["path"])}"}}\'  '
            f'hx-target="#ctx-memos-{item_id}" hx-swap="innerHTML" '
            f'onclick="return confirm(\'연결 해제?\')">✕</button>'
            f'</div>'
        )
    return HTMLResponse("\n".join(rows) if rows else "")


# ── Orphan items (capture without project) ───────────────────────────────────

@router.get("/api/items/orphans")
async def list_orphans(db: sqlite3.Connection = Depends(get_db)):
    """List items that have no project link — captured but not yet triaged."""
    rows = db.execute(
        """
        SELECT i.id, i.type, i.title, i.status, i.scheduled_at, i.created_at,
               GROUP_CONCAT(t.name) AS tag_names
        FROM items i
        LEFT JOIN item_projects ip ON ip.item_id = i.id
        LEFT JOIN item_tags it ON it.item_id = i.id
        LEFT JOIN tags t ON t.id = it.tag_id
        WHERE ip.item_id IS NULL
          AND i.status NOT IN ('cancelled', 'done')
          AND i.location = 'hot'
        GROUP BY i.id
        ORDER BY i.created_at DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/items/orphans/count")
async def count_orphans(db: sqlite3.Connection = Depends(get_db)):
    n = db.execute(
        """SELECT COUNT(*) FROM items i
           LEFT JOIN item_projects ip ON ip.item_id = i.id
           WHERE ip.item_id IS NULL
             AND i.status NOT IN ('cancelled', 'done')
             AND i.location = 'hot'"""
    ).fetchone()[0]
    return {"count": n}


@router.delete("/api/items/{item_id}")
async def delete_item(item_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Soft-delete (FR-CAP-01)."""
    if not db.execute("SELECT id FROM items WHERE id=?", (item_id,)).fetchone():
        raise HTTPException(404)
    db.execute("UPDATE items SET status='cancelled', updated_at=? WHERE id=?",
               (_now_iso(), item_id))
    return Response(status_code=204)


# ── Tags ──────────────────────────────────────────────────────────────────────

@router.post("/api/items/{item_id}/tags", response_class=HTMLResponse)
async def add_tag(
    item_id: int,
    tag_name: Annotated[str, Form()],
    db: sqlite3.Connection = Depends(get_db),
):
    """Attach a tag (FR-CAP-02)."""
    tag_name = tag_name.strip().lstrip("#")
    if not tag_name:
        raise HTTPException(422, "Empty tag")
    db.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (tag_name,))
    tag_id = db.execute("SELECT id FROM tags WHERE name=?", (tag_name,)).fetchone()["id"]
    db.execute("INSERT OR IGNORE INTO item_tags(item_id, tag_id) VALUES (?,?)", (item_id, tag_id))
    return HTMLResponse(
        f'<span class="ctx-pill" id="tag-pill-{item_id}-{tag_id}">'
        f'#{escape(tag_name)}'
        f'<span class="x" hx-delete="/api/items/{item_id}/tags/{tag_id}" '
        f'hx-target="#tag-pill-{item_id}-{tag_id}" hx-swap="outerHTML">×</span>'
        f'</span>'
    )


@router.post("/api/items/{item_id}/tags/by-name", response_class=HTMLResponse)
async def add_tag_by_name(
    item_id: int,
    tag_name: Annotated[str | None, Form()] = None,
    name: Annotated[str | None, Form()] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    return await add_tag(item_id, tag_name or name or "", db)


@router.delete("/api/items/{item_id}/tags/by-name", response_class=HTMLResponse)
async def remove_tag_by_name(
    item_id: int,
    tag_name: Annotated[str | None, Form()] = None,
    name: Annotated[str | None, Form()] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    clean = (tag_name or name or "").strip().lstrip("#")
    if clean:
        db.execute(
            """DELETE FROM item_tags
               WHERE item_id=? AND tag_id IN (SELECT id FROM tags WHERE name=?)""",
            (item_id, clean),
        )
    return HTMLResponse("")


@router.delete("/api/items/{item_id}/tags/{tag_id}", response_class=HTMLResponse)
async def remove_tag(item_id: int, tag_id: int, db: sqlite3.Connection = Depends(get_db)):
    db.execute("DELETE FROM item_tags WHERE item_id=? AND tag_id=?", (item_id, tag_id))
    return HTMLResponse("")


# ── Labels (FR-LABEL-01) ──────────────────────────────────────────────────────

@router.get("/api/labels")
async def list_labels(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT id, name, color, type FROM labels ORDER BY type, name").fetchall()
    return [dict(r) for r in rows]


@router.post("/api/items/{item_id}/labels", response_class=HTMLResponse)
async def add_label(
    item_id: int,
    label_id: Annotated[int, Form()],
    db: sqlite3.Connection = Depends(get_db),
):
    """Attach a label to an item (FR-LABEL-01)."""
    db.execute("INSERT OR IGNORE INTO item_labels(item_id, label_id) VALUES(?,?)",
               (item_id, label_id))
    label = db.execute("SELECT name, color FROM labels WHERE id=?", (label_id,)).fetchone()
    if not label:
        return HTMLResponse("")
    color = label["color"] or "var(--surface-2)"
    return HTMLResponse(
        f'<span class="ctx-pill" data-type="{escape(label["name"])}" '
        f'style="background:{escape(color)}; color:white;">'
        f'{escape(label["name"])}'
        f'<span class="x" hx-delete="/api/items/{item_id}/labels/{label_id}" '
        f'hx-target="closest .ctx-pill" hx-swap="outerHTML">×</span>'
        f'</span>'
    )


@router.post("/api/items/{item_id}/labels/by-name", response_class=HTMLResponse)
async def add_label_by_name(
    item_id: int,
    name: Annotated[str, Form()],
    db: sqlite3.Connection = Depends(get_db),
):
    clean = name.strip()
    if not clean:
        raise HTTPException(422, "Empty label")
    db.execute("INSERT OR IGNORE INTO labels(name, color, type) VALUES(?, '#f59e0b', 'custom')", (clean,))
    label_id = db.execute("SELECT id FROM labels WHERE name=?", (clean,)).fetchone()["id"]
    return await add_label(item_id, label_id, db)


@router.delete("/api/items/{item_id}/labels/by-name", response_class=HTMLResponse)
async def remove_label_by_name(
    item_id: int,
    name: Annotated[str, Form()],
    db: sqlite3.Connection = Depends(get_db),
):
    clean = name.strip()
    if clean:
        db.execute(
            """DELETE FROM item_labels
               WHERE item_id=? AND label_id IN (SELECT id FROM labels WHERE name=?)""",
            (item_id, clean),
        )
    return HTMLResponse("")


@router.delete("/api/items/{item_id}/labels/{label_id}")
async def remove_label(item_id: int, label_id: int, db: sqlite3.Connection = Depends(get_db)):
    db.execute("DELETE FROM item_labels WHERE item_id=? AND label_id=?", (item_id, label_id))
    return Response(status_code=204)


# ── Carry-over ────────────────────────────────────────────────────────────────

@router.post("/api/carry-over", response_class=HTMLResponse)
async def carry_over(
    review_date: Annotated[str | None, Form()] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Move unfinished items to tomorrow (FR-DAY-02)."""
    today = review_date or date.today().isoformat()
    tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
    db.execute(
        """UPDATE items SET scheduled_at=?, updated_at=?
           WHERE status NOT IN ('done','cancelled') AND location='hot'
             AND (scheduled_at IS NULL OR date(scheduled_at) <= ?)""",
        (tomorrow + "T00:00:00Z", _now_iso(), today),
    )
    count = db.execute("SELECT changes()").fetchone()[0]
    return HTMLResponse(f'<span id="carry-over-result">{count}개 이월 완료</span>')


# ── Export (FR-BACKUP-01) ────────────────────────────────────────────────────

@router.get("/api/export")
async def export_all(db: sqlite3.Connection = Depends(get_db)):
    """Full JSON export of all entities (FR-BACKUP-01)."""
    def q(sql: str) -> list[dict]:
        return [dict(r) for r in db.execute(sql).fetchall()]

    payload = {
        "exported_at": _now_iso(),
        "schema_version": 5,
        "items":         q("SELECT * FROM items ORDER BY created_at"),
        "tags":          q("SELECT * FROM tags"),
        "item_tags":     q("SELECT * FROM item_tags"),
        "labels":        q("SELECT * FROM labels"),
        "item_labels":   q("SELECT * FROM item_labels"),
        "organizations": q("SELECT * FROM organizations"),
        "organization_profiles": q("SELECT * FROM organization_profiles"),
        "businesses":    q("SELECT * FROM businesses"),
        "projects":      q("SELECT * FROM projects"),
        "project_stages": q("SELECT * FROM project_stages"),
        "item_projects": q("SELECT * FROM item_projects"),
        "schedules":     q("SELECT * FROM schedules"),
        "capture_inbox": q("SELECT * FROM capture_inbox"),
        "review_memos":  q("SELECT * FROM review_memos"),
        "incomplete_reasons": q("SELECT * FROM incomplete_reasons"),
        "notification_events": q("SELECT * FROM notification_events"),
        "settings":      q("SELECT key, value, updated_at FROM settings"),
    }
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="mc-export-{ts}.json"'},
    )
