"""
SC-14 Org Hierarchy — GET /hierarchy (FR-ORG-01~03, FR-PROJ-01~04).
Business/Project CRUD + /project/{id} detail.
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..db import get_db

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

_STATUS_LABELS = {
    "active": "진행중", "planning": "기획", "review": "검토",
    "done": "완료", "paused": "중단", "archived": "보관",
}
_VALID_PROJ_STATUSES = {"planning", "active", "review", "paused", "done"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_biz_projects(db: sqlite3.Connection, biz_id: int) -> list[dict]:
    projects = db.execute(
        """
        SELECT p.id, p.title, p.status, p.start_date, p.end_date, p.github_repo,
            (SELECT COUNT(*) FROM project_stages ps WHERE ps.project_id=p.id) AS stage_count,
            (SELECT COUNT(*) FROM project_stages ps WHERE ps.project_id=p.id AND ps.status='active') AS active_stages,
            (SELECT COUNT(*) FROM item_projects ip
             JOIN items i ON i.id=ip.item_id
             WHERE ip.project_id=p.id AND i.status NOT IN ('cancelled')) AS item_count,
            (SELECT COUNT(*) FROM item_projects ip
             JOIN items i ON i.id=ip.item_id
             WHERE ip.project_id=p.id AND i.status='done') AS done_count
        FROM projects p
        WHERE p.business_id=? AND p.status != 'archived'
        ORDER BY p.status='active' DESC, p.title
        """,
        (biz_id,),
    ).fetchall()
    result = []
    for p in projects:
        p_d = dict(p)
        p_d["progress_pct"] = (
            round(p_d["done_count"] * 100 / p_d["item_count"])
            if p_d["item_count"] else 0
        )
        stages = db.execute(
            "SELECT name, status, order_idx FROM project_stages WHERE project_id=? ORDER BY order_idx",
            (p_d["id"],),
        ).fetchall()
        p_d["stages"] = [dict(s) for s in stages]
        result.append(p_d)
    return result


def _load_single_biz(db: sqlite3.Connection, biz_id: int) -> dict | None:
    row = db.execute(
        "SELECT id, name, description, org_id FROM businesses WHERE id=?", (biz_id,)
    ).fetchone()
    if not row:
        return None
    biz_d = dict(row)
    biz_d["projects"] = _load_biz_projects(db, biz_id)
    return biz_d


def _load_single_org(db: sqlite3.Connection, org_id: int) -> dict | None:
    org = db.execute(
        "SELECT id, name, color FROM organizations WHERE id=?", (org_id,)
    ).fetchone()
    if not org:
        return None
    org_d = dict(org)
    businesses = db.execute(
        "SELECT id, name, description FROM businesses WHERE org_id=? ORDER BY name",
        (org_id,),
    ).fetchall()
    biz_list = []
    for biz in businesses:
        biz_d = dict(biz)
        biz_d["projects"] = _load_biz_projects(db, biz_d["id"])
        biz_list.append(biz_d)
    org_d["businesses"] = biz_list
    return org_d


def _load_hierarchy(db: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    orgs = db.execute(
        "SELECT id, name, color FROM organizations ORDER BY name"
    ).fetchall()

    result = []
    for org in orgs:
        org_d = dict(org)
        businesses = db.execute(
            "SELECT id, name, description FROM businesses WHERE org_id=? ORDER BY name",
            (org_d["id"],),
        ).fetchall()
        biz_list = []
        for biz in businesses:
            biz_d = dict(biz)
            biz_d["projects"] = _load_biz_projects(db, biz_d["id"])
            biz_list.append(biz_d)
        org_d["businesses"] = biz_list
        result.append(org_d)

    unaffiliated = db.execute(
        """
        SELECT p.id, p.title, p.status, p.start_date, p.end_date,
               (SELECT COUNT(*) FROM item_projects ip
                JOIN items i ON i.id=ip.item_id
                WHERE ip.project_id=p.id AND i.status NOT IN ('cancelled')) AS item_count,
               (SELECT COUNT(*) FROM item_projects ip
                JOIN items i ON i.id=ip.item_id
                WHERE ip.project_id=p.id AND i.status='done') AS done_count
        FROM projects p
        WHERE p.business_id IS NULL AND p.status != 'archived'
        ORDER BY p.title
        """
    ).fetchall()

    unaffiliated_list = []
    for p in unaffiliated:
        p_d = dict(p)
        p_d["progress_pct"] = (
            round(p_d["done_count"] * 100 / p_d["item_count"])
            if p_d["item_count"] else 0
        )
        p_d["active_stage"] = None
        p_d["stages"] = []
        unaffiliated_list.append(p_d)

    return result, unaffiliated_list


# ── Main hierarchy page ───────────────────────────────────────────────────────

@router.get("/hierarchy", response_class=HTMLResponse)
async def hierarchy(request: Request, db: sqlite3.Connection = Depends(get_db)):
    orgs, unaffiliated = _load_hierarchy(db)
    total_projects = sum(
        len(biz["projects"]) for org in orgs for biz in org["businesses"]
    ) + len(unaffiliated)

    return templates.TemplateResponse(
        request,
        "hierarchy.html",
        {"orgs": orgs, "unaffiliated": unaffiliated, "total_projects": total_projects},
    )


# ── Business CRUD ─────────────────────────────────────────────────────────────

@router.post("/api/businesses", response_class=HTMLResponse)
async def add_business(
    request: Request,
    name: Annotated[str, Form()],
    org_id: Annotated[int, Form()],
    description: Annotated[str, Form()] = "",
    db: sqlite3.Connection = Depends(get_db),
):
    name = name.strip()
    if not name:
        return HTMLResponse('<span style="color:oklch(60% 0.21 25)">이름을 입력하세요</span>', status_code=422)
    cur = db.execute(
        "INSERT INTO businesses(name, description, org_id) VALUES(?,?,?)",
        (name, description.strip(), org_id),
    )
    biz_id = cur.lastrowid

    # FR-FILES-01: auto-create business folder
    org_row = db.execute("SELECT name FROM organizations WHERE id=?", (org_id,)).fetchone()
    if org_row:
        from ..config import get_config
        from ..integrations import ensure_business_folder
        cfg = get_config()
        folder = ensure_business_folder(str(cfg.notes_root), org_row["name"], name)
        if folder:
            db.execute("UPDATE businesses SET folder_path=? WHERE id=?", (folder, biz_id))

    org = _load_single_org(db, org_id)
    return templates.TemplateResponse(request, "partials/org_section.html", {"org": org})


@router.delete("/api/businesses/{biz_id}", response_class=HTMLResponse)
async def delete_business(
    request: Request,
    biz_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute("SELECT org_id FROM businesses WHERE id=?", (biz_id,)).fetchone()
    if not row:
        return HTMLResponse("", status_code=404)
    org_id = row[0]
    proj_count = db.execute(
        "SELECT COUNT(*) FROM projects WHERE business_id=? AND status != 'archived'", (biz_id,)
    ).fetchone()[0]
    if proj_count > 0:
        return HTMLResponse(
            '<span style="color:oklch(60% 0.21 25); font-size:12px;">⚠ 프로젝트가 있어 삭제 불가</span>',
            status_code=409,
        )
    db.execute("DELETE FROM businesses WHERE id=?", (biz_id,))
    org = _load_single_org(db, org_id)
    return templates.TemplateResponse(request, "partials/org_section.html", {"org": org})


# ── Project CRUD ──────────────────────────────────────────────────────────────

@router.post("/api/projects", response_class=HTMLResponse)
async def add_project(
    request: Request,
    title: Annotated[str, Form()],
    business_id: Annotated[int, Form()],
    status: Annotated[str, Form()] = "planning",
    start_date: Annotated[str, Form()] = "",
    end_date: Annotated[str, Form()] = "",
    github_repo: Annotated[str, Form()] = "",
    db: sqlite3.Connection = Depends(get_db),
):
    title = title.strip()
    if not title:
        return HTMLResponse('<span style="color:oklch(60% 0.21 25)">제목을 입력하세요</span>', status_code=422)
    cur = db.execute(
        "INSERT INTO projects(business_id, title, status, start_date, end_date, github_repo) VALUES(?,?,?,?,?,?)",
        (
            business_id, title, status,
            start_date.strip() or None,
            end_date.strip() or None,
            github_repo.strip() or None,
        ),
    )
    proj_id = cur.lastrowid

    # FR-FILES-01: auto-create folder structure
    biz_row = db.execute(
        "SELECT b.name AS biz_name, o.name AS org_name FROM businesses b "
        "LEFT JOIN organizations o ON o.id=b.org_id WHERE b.id=?",
        (business_id,),
    ).fetchone()
    if biz_row:
        from ..config import get_config
        from ..integrations import ensure_project_folder
        cfg = get_config()
        folder = ensure_project_folder(
            str(cfg.notes_root),
            biz_row["org_name"] or "misc",
            biz_row["biz_name"] or "misc",
            title,
        )
        if folder:
            db.execute("UPDATE projects SET folder_path=? WHERE id=?", (folder, proj_id))

    biz = _load_single_biz(db, business_id)
    return templates.TemplateResponse(request, "partials/biz_block.html", {"biz": biz})


@router.delete("/api/projects/{proj_id}", response_class=HTMLResponse)
async def archive_project(
    request: Request,
    proj_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute("SELECT business_id FROM projects WHERE id=?", (proj_id,)).fetchone()
    if not row:
        return HTMLResponse("", status_code=404)
    biz_id = row[0]
    db.execute("UPDATE projects SET status='archived' WHERE id=?", (proj_id,))
    # B-006: clean up item_projects so archived projects don't appear
    # in flow / export queries that expect active links (BR-PROJ-03).
    db.execute("DELETE FROM item_projects WHERE project_id=?", (proj_id,))
    biz = _load_single_biz(db, biz_id)
    return templates.TemplateResponse(request, "partials/biz_block.html", {"biz": biz})


@router.patch("/api/projects/{proj_id}/status", response_class=HTMLResponse)
async def update_project_status(
    proj_id: int,
    status: Annotated[str, Form()],
    db: sqlite3.Connection = Depends(get_db),
):
    if status not in _VALID_PROJ_STATUSES:
        return HTMLResponse("잘못된 상태값", status_code=422)
    db.execute("UPDATE projects SET status=? WHERE id=?", (status, proj_id))
    label = _STATUS_LABELS.get(status, status)
    return HTMLResponse(
        f'<span class="status-badge" data-s="{status}" id="proj-status-{proj_id}">{label}</span>'
    )


@router.patch("/api/stages/{stage_id}/status", response_class=HTMLResponse)
async def update_stage_status(
    stage_id: int,
    status: Annotated[str, Form()],
    db: sqlite3.Connection = Depends(get_db),
):
    if status not in ("pending", "active", "done"):
        return HTMLResponse("잘못된 상태값", status_code=422)
    db.execute("UPDATE project_stages SET status=? WHERE id=?", (status, stage_id))
    row = db.execute(
        "SELECT name FROM project_stages WHERE id=?", (stage_id,)
    ).fetchone()
    name = row[0] if row else ""
    next_s = {"pending": "active", "active": "done", "done": "pending"}[status]
    icon = {"done": "✓ ", "active": "● ", "pending": ""}[status]
    return HTMLResponse(
        f'<button class="stage-chip" data-s="{status}" id="stage-{stage_id}" '
        f'hx-patch="/api/stages/{stage_id}/status" '
        f'hx-vals=\'{{"status":"{next_s}"}}\' '
        f'hx-target="#stage-{stage_id}" hx-swap="outerHTML" '
        f'title="클릭하여 상태 변경">{icon}{name}</button>'
    )


# ── Project detail ────────────────────────────────────────────────────────────

@router.get("/project/{project_id}", response_class=HTMLResponse)
async def project_detail(
    project_id: int,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
):
    from ..integrations import sync_github
    await sync_github()
    proj = db.execute(
        """
        SELECT p.id, p.title, p.status, p.start_date, p.end_date,
               p.github_repo, p.vision, p.folder_path,
               b.id AS biz_id, b.name AS biz_name,
               o.id AS org_id, o.name AS org_name, o.color AS org_color
        FROM projects p
        LEFT JOIN businesses b ON b.id = p.business_id
        LEFT JOIN organizations o ON o.id = b.org_id
        WHERE p.id = ?
        """,
        (project_id,),
    ).fetchone()
    if not proj:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")
    proj_d = dict(proj)

    stages = db.execute(
        "SELECT id, name, status, order_idx, start_date, end_date FROM project_stages WHERE project_id=? ORDER BY order_idx",
        (project_id,),
    ).fetchall()

    # Top-level items only (parent_id IS NULL); subtasks are loaded per-item
    items = db.execute(
        """
        SELECT i.id, i.title, i.status, i.scheduled_at, i.due_date, i.start_date,
               (SELECT COUNT(*) FROM items c WHERE c.parent_id = i.id AND c.status != 'cancelled') AS sub_total,
               (SELECT COUNT(*) FROM items c WHERE c.parent_id = i.id AND c.status = 'done')        AS sub_done
        FROM items i
        JOIN item_projects ip ON ip.item_id = i.id
        WHERE ip.project_id = ? AND i.status NOT IN ('cancelled')
          AND i.parent_id IS NULL
        ORDER BY i.status='done' ASC,
                 CASE i.status WHEN 'in_progress' THEN 0 WHEN 'doing' THEN 0
                               WHEN 'todo' THEN 1 WHEN 'waiting' THEN 2 ELSE 3 END,
                 COALESCE(i.due_date, i.scheduled_at, '9999') ASC
        """,
        (project_id,),
    ).fetchall()

    items_list = []
    for r in items:
        d = dict(r)
        d["sub_pct"] = round(d["sub_done"] * 100 / d["sub_total"]) if d["sub_total"] else 0
        items_list.append(d)
    item_count = len(items_list)
    done_count = sum(1 for i in items_list if i["status"] == "done")
    progress_pct = round(done_count * 100 / item_count) if item_count else 0

    github_issues = []
    if proj_d.get("github_repo"):
        github_issues = [
            dict(r) for r in db.execute(
                """SELECT number, title, state, html_url FROM github_cache
                   WHERE repo=? AND state='open' ORDER BY number DESC LIMIT 10""",
                (proj_d["github_repo"],),
            ).fetchall()
        ]

    from datetime import date
    return templates.TemplateResponse(
        request,
        "project.html",
        {
            "proj": proj_d,
            "stages": [dict(s) for s in stages],
            "items": items_list,
            "item_count": item_count,
            "today": date.today().isoformat(),
            "done_count": done_count,
            "progress_pct": progress_pct,
            "status_labels": _STATUS_LABELS,
            "valid_statuses": sorted(_VALID_PROJ_STATUSES),
            "github_issues": github_issues,
        },
    )


# ── Folder open ───────────────────────────────────────────────────────────────

@router.get("/api/folder-open")
async def folder_open(path: str):
    """Open a local folder path in Windows Explorer."""
    import subprocess
    from fastapi.responses import JSONResponse
    try:
        p = Path(path)
        if not p.exists():
            return JSONResponse({"error": "경로가 존재하지 않습니다"}, status_code=404)
        subprocess.Popen(["explorer", str(p)])
        return {"ok": True}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


# ── Project items partial ─────────────────────────────────────────────────────

@router.get("/partial/project/{project_id}/items", response_class=HTMLResponse)
async def project_items_partial(
    project_id: int,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
):
    """Return items list HTML partial for a project page (reloaded after add/toggle)."""
    from datetime import date
    items = db.execute(
        """
        SELECT i.id, i.title, i.status, i.scheduled_at, i.due_date, i.start_date,
               (SELECT COUNT(*) FROM items c WHERE c.parent_id = i.id AND c.status != 'cancelled') AS sub_total,
               (SELECT COUNT(*) FROM items c WHERE c.parent_id = i.id AND c.status = 'done')        AS sub_done
        FROM items i
        JOIN item_projects ip ON ip.item_id = i.id
        WHERE ip.project_id = ? AND i.status NOT IN ('cancelled')
          AND i.parent_id IS NULL
        ORDER BY i.status='done' ASC,
                 CASE i.status WHEN 'in_progress' THEN 0 WHEN 'doing' THEN 0
                               WHEN 'todo' THEN 1 WHEN 'waiting' THEN 2 ELSE 3 END,
                 COALESCE(i.due_date, i.scheduled_at, '9999') ASC
        """,
        (project_id,),
    ).fetchall()

    items_list = []
    for r in items:
        d = dict(r)
        d["sub_pct"] = round(d["sub_done"] * 100 / d["sub_total"]) if d["sub_total"] else 0
        items_list.append(d)

    return templates.TemplateResponse(
        request,
        "partials/project_items.html",
        {
            "items": items_list,
            "project_id": project_id,
            "today": date.today().isoformat(),
        },
    )
