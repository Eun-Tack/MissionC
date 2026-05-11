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

from fastapi import APIRouter, Depends, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse

from ..db import get_db

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


_VALID_RECURRENCE = {"DAILY", "WEEKDAYS", "WEEKLY", "MONTHLY"}
_TITLE_MAX = 10000


def _check_title(title: str) -> str:
    """Validate and trim title — raises 422 if too long. (B-003)"""
    t = (title or "").strip()
    if not t:
        raise HTTPException(422, "Title required")
    if len(t) > _TITLE_MAX:
        raise HTTPException(422, f"Title too long (max {_TITLE_MAX} chars, got {len(t)})")
    return t


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

    now = _now_iso()
    cur = db.execute(
        """INSERT INTO items (type, title, body, body_inline, status, location,
                              scheduled_at, parent_id, start_date, due_date,
                              recurrence_rule, recurrence_parent_id,
                              created_at, updated_at, source)
           VALUES (?, ?, ?, 0, 'todo', 'hot', ?, ?, ?, ?, ?, ?, ?, ?, 'manual')""",
        (type_, title_clean, body, scheduled_at, parent_id,
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
    if scheduled_at and (type_ == "schedule" or end_at):
        db.execute(
            "INSERT INTO schedules (item_id, start_at, end_at) VALUES (?, ?, ?)",
            (item_id, scheduled_at, end_at or None),
        )

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
    return HTMLResponse(snippet)


@router.patch("/api/items/{item_id}", response_class=HTMLResponse)
async def update_item(
    request: Request,
    item_id: int,
    status: Annotated[str | None, Form()] = None,
    title: Annotated[str | None, Form()] = None,
    body: Annotated[str | None, Form()] = None,
    scheduled_at: Annotated[str | None, Form()] = None,
    start_date: Annotated[str | None, Form()] = None,
    due_date: Annotated[str | None, Form()] = None,
    recurrence_rule: Annotated[str | None, Form()] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Inline edit — title/status/body/dates/recurrence (FR-CAP-01 AC-3)."""
    row = db.execute(
        "SELECT id, status, title, type, scheduled_at, due_date, start_date, "
        "recurrence_rule, body FROM items WHERE id = ?",
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
        val = scheduled_at.strip()
        if val and "T" not in val and len(val) == 10:
            val = f"{val}T00:00:00Z"
        elif val and "T" in val and not val.endswith("Z"):
            val = val + ":00Z" if len(val) == 16 else val
        updates.append("scheduled_at = ?")
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

    return HTMLResponse(f"{dot_oob}\n{extra_oob}")


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

@router.get("/api/items/{parent_id}/subtasks", response_class=HTMLResponse)
async def list_subtasks(
    parent_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    """Return HTML partial of sub-tasks for inline rendering in Context Panel."""
    rows = db.execute(
        """SELECT id, title, status, scheduled_at, due_date, start_date
           FROM items
           WHERE parent_id = ? AND status != 'cancelled'
           ORDER BY status='done' ASC,
                    COALESCE(due_date, '9999') ASC,
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
    due_date: Annotated[str | None, Form()] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Create a child item under parent_id, inheriting parent's project."""
    if not db.execute("SELECT 1 FROM items WHERE id=?", (parent_id,)).fetchone():
        raise HTTPException(404, "Parent item not found")
    title_clean = _check_title(title)

    now = _now_iso()
    cur = db.execute(
        """INSERT INTO items (type, title, body_inline, status, location,
                              parent_id, due_date, created_at, updated_at, source)
           VALUES ('task', ?, 0, 'todo', 'hot', ?, ?, ?, ?, 'manual')""",
        (title_clean, parent_id, due_date or None, now, now),
    )
    new_id = cur.lastrowid

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
    return HTMLResponse(f'<span class="tag-chip">#{tag_name}</span>')


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
        f'<span class="label-chip" style="background:{color};">{label["name"]}</span>'
    )


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
