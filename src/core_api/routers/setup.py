"""
Setup Wizard + Settings (SC-08).

GET  /setup                  — 초기 설정 마법사
POST /setup/step/folder      — Step 1: MC-Notes 폴더 저장
POST /setup/step/orgs        — Step 2: 소속 등록
POST /setup/step/integrations — Step 3: 연동 설정 저장
POST /setup/complete         — 완료 → setup_completed=true

GET  /settings               — SC-08 설정 화면 (언제든 재접근)
POST /settings/folder        — 폴더 경로 변경
POST /settings/org           — 소속 추가/수정
DELETE /settings/org/{id}    — 소속 삭제
PATCH /settings/business/{id}/folder  — 사업 기본 폴더 설정
POST  /settings/tags         — 태그 생성
DELETE /settings/tags/{id}   — 태그 삭제
POST  /settings/labels       — 라벨 생성
DELETE /settings/labels/{id} — 라벨 삭제
POST /settings/credential    — 토큰 저장 (ADR-005)
GET  /settings/test/{service} — 연동 테스트

GET  /api/pick-folder        — 네이티브 폴더 다이얼로그 (Windows)
"""

from __future__ import annotations
import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..db import get_db
from ..config import reload_config
from .auth import has_gcal_token

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

_KEYRING_USER = "iet03"
_GCAL_SECRET_KEY = "MC_GCAL_TOKEN"
_LEGACY_GCAL_SECRET_KEY = "MC_GOOGLE_OAUTH"
_ORG_COLORS = [
    ("oklch(58% 0.18 280)", "보라"),
    ("oklch(55% 0.20 145)", "초록"),
    ("oklch(60% 0.20 250)", "파랑"),
    ("oklch(60% 0.18 25)",  "주황"),
    ("oklch(58% 0.18 320)", "분홍"),
    ("oklch(55% 0.15 200)", "청록"),
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _save_setting(db: sqlite3.Connection, key: str, value: str) -> None:
    db.execute(
        "INSERT INTO settings(key, value, updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, value, _now()),
    )


def _get_setting(db: sqlite3.Connection, key: str, default: str = "") -> str:
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def _is_setup_complete(db: sqlite3.Connection) -> bool:
    return _get_setting(db, "setup_completed") == "true"


def _try_save_secret(key: str, value: str) -> tuple[bool, str]:
    # On cloud/Railway: secrets come from env vars — no-op write, just validate
    import os
    env_key = key.upper().replace("-", "_").replace("/", "_")
    if os.environ.get(env_key):
        return True, "(env var 사용 중)"
    try:
        import keyring
        keyring.set_password(key, _KEYRING_USER, value)
        return True, ""
    except Exception as e:
        return False, str(e)


def _try_get_secret(key: str) -> str | None:
    import os
    # 1. Env var (Railway / Docker / cloud deployment)
    env_key = key.upper().replace("-", "_").replace("/", "_")
    val = os.environ.get(env_key)
    if val:
        return val
    # 2. Local Windows Credential Manager
    try:
        import keyring
        val = keyring.get_password(key, _KEYRING_USER)
        if val:
            return val
        if key == _GCAL_SECRET_KEY:
            legacy = keyring.get_password(_LEGACY_GCAL_SECRET_KEY, _KEYRING_USER)
            if legacy:
                keyring.set_password(_GCAL_SECRET_KEY, _KEYRING_USER, legacy)
                return legacy
        return None
    except Exception:
        return None


def _secret_is_set(key: str) -> bool:
    val = _try_get_secret(key)
    return bool(val and val.strip())


# ── Native folder picker (Windows tkinter) ────────────────────────────────────

def _open_folder_dialog_sync(initial: str = "") -> str:
    import sys
    if sys.platform != "win32":
        return ""   # 폴더 다이얼로그는 Windows 전용 — 클라우드에서는 수동 입력
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        path = filedialog.askdirectory(
            title="MC-Notes 폴더 선택",
            initialdir=initial or str(Path.home() / "Documents"),
        )
        root.destroy()
        return path or ""
    except Exception:
        return ""


@router.get("/api/pick-folder")
async def pick_folder(current: str = ""):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        path = await loop.run_in_executor(pool, _open_folder_dialog_sync, current)
    return JSONResponse({"path": path})


# ── Integration test helpers ──────────────────────────────────────────────────

async def _test_github(token: str) -> tuple[bool, str]:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            )
            if r.status_code == 200:
                login = r.json().get("login", "?")
                return True, f"연결됨 — @{login}"
            return False, f"인증 실패 ({r.status_code})"
    except Exception as e:
        return False, f"오류: {e}"


async def _test_gcal() -> tuple[bool, str]:
    try:
        import json, os, httpx
        token_json = _try_get_secret(_GCAL_SECRET_KEY)
        if not token_json:
            return False, "토큰 없음"
        token_data = json.loads(token_json)
        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")
        client_id = os.environ.get("MC_GOOGLE_CLIENT_ID") or os.environ.get("GOOGLE_CLIENT_ID", "")
        client_secret = os.environ.get("MC_GOOGLE_CLIENT_SECRET") or os.environ.get("GOOGLE_CLIENT_SECRET", "")

        async def _refresh() -> str | None:
            if not refresh_token or not client_id:
                return None
            async with httpx.AsyncClient(timeout=8) as client:
                ref = await client.post("https://oauth2.googleapis.com/token", data={
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                })
            if ref.status_code == 200:
                refreshed = ref.json().get("access_token", "")
                token_data["access_token"] = refreshed
                try:
                    import keyring
                    keyring.set_password(_GCAL_SECRET_KEY, _KEYRING_USER, json.dumps(token_data))
                except Exception:
                    pass
                return refreshed
            raise RuntimeError(f"토큰 갱신 실패 ({ref.status_code})")

        if not access_token:
            access_token = await _refresh()
            if not access_token:
                return False, "access_token 없음"

        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if r.status_code == 401 and refresh_token:
                access_token = await _refresh()
                if access_token:
                    r = await client.get(
                        "https://www.googleapis.com/calendar/v3/calendars/primary",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
            if r.status_code == 200:
                summary = r.json().get("summary", "primary")
                return True, f"연결됨 — {summary}"
            return False, f"인증 실패 ({r.status_code})"
    except Exception as e:
        return False, f"오류: {e}"


async def _test_telegram(token: str) -> tuple[bool, str]:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            if r.status_code == 200 and r.json().get("ok"):
                name = r.json()["result"].get("username", "?")
                return True, f"연결됨 — @{name}"
            return False, "토큰 오류"
    except Exception as e:
        return False, f"오류: {e}"


@router.get("/settings/test/{service}", response_class=HTMLResponse)
async def test_integration(service: str):
    token = _try_get_secret(f"MC_{service.upper()}_PAT" if service == "gh" else f"MC_{service.upper()}_BOT_TOKEN")
    if service == "gcal":
        ok, msg = await _test_gcal()
        color = "var(--st-done)" if ok else "oklch(60% 0.21 25)"
        icon  = "✓" if ok else "✕"
        return HTMLResponse(f'<span style="color:{color}; font-size:12px;">{icon} {msg}</span>')

    if service == "gh":
        token = _try_get_secret("MC_GH_PAT")
    elif service == "tg":
        token = _try_get_secret("MC_TG_BOT_TOKEN")
    else:
        return HTMLResponse('<span style="color:var(--muted)">알 수 없는 서비스</span>')

    if not token:
        return HTMLResponse('<span style="color:var(--st-waiting)">⚠ 토큰 미설정</span>')

    if service == "gh":
        ok, msg = await _test_github(token)
    else:
        ok, msg = await _test_telegram(token)

    color = "var(--st-done)" if ok else "oklch(60% 0.21 25)"
    icon  = "✓" if ok else "✕"
    return HTMLResponse(f'<span style="color:{color}; font-size:12px;">{icon} {msg}</span>')


# ── Setup Wizard ──────────────────────────────────────────────────────────────

@router.get("/setup", response_class=HTMLResponse)
async def setup_get(request: Request, step: int = 1, db: sqlite3.Connection = Depends(get_db)):
    if _is_setup_complete(db):
        return RedirectResponse("/", status_code=302)

    notes_root = _get_setting(db, "mc_notes_root")
    orgs = db.execute("SELECT id, name, color FROM organizations ORDER BY name").fetchall()

    return templates.TemplateResponse(
        request,
        "setup.html",
        {
            "step": step,
            "notes_root": notes_root,
            "orgs": [dict(o) for o in orgs],
            "org_colors": _ORG_COLORS,
            "gh_set":  _secret_is_set("MC_GH_PAT"),
            "tg_set":  _secret_is_set("MC_TG_BOT_TOKEN"),
            "gcal_set": has_gcal_token() or _secret_is_set(_GCAL_SECRET_KEY),
        },
    )


@router.post("/setup/step/folder")
async def setup_folder(
    notes_root: Annotated[str, Form()] = "",
    db: sqlite3.Connection = Depends(get_db),
):
    path = notes_root.strip()
    if path:
        Path(path).mkdir(parents=True, exist_ok=True)
        _save_setting(db, "mc_notes_root", path)
        (Path(path) / "inbox").mkdir(exist_ok=True)
    reload_config()
    from fastapi.responses import Response
    r = Response(status_code=200)
    r.headers["HX-Redirect"] = "/setup?step=2"
    return r


@router.post("/setup/step/orgs")
async def setup_orgs():
    from fastapi.responses import Response
    r = Response(status_code=200)
    r.headers["HX-Redirect"] = "/setup?step=3"
    return r


@router.post("/setup/step/integrations")
async def setup_integrations(
    gh_token: Annotated[str, Form()] = "",
    tg_token: Annotated[str, Form()] = "",
):
    if gh_token.strip():
        _try_save_secret("MC_GH_PAT", gh_token.strip())
    if tg_token.strip():
        _try_save_secret("MC_TG_BOT_TOKEN", tg_token.strip())
    from fastapi.responses import Response
    r = Response(status_code=200)
    r.headers["HX-Redirect"] = "/setup?step=4"
    return r


@router.post("/setup/complete")
async def setup_complete(db: sqlite3.Connection = Depends(get_db)):
    _save_setting(db, "setup_completed", "true")
    reload_config()
    return RedirectResponse("/", status_code=302)


# ── Settings page (SC-08) ─────────────────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
async def settings_get(request: Request, db: sqlite3.Connection = Depends(get_db)):
    notes_root = _get_setting(db, "mc_notes_root")
    orgs = db.execute(
        """SELECT o.id, o.name, o.color,
                  COUNT(DISTINCT b.id) AS biz_count,
                  COUNT(DISTINCT p.id) AS proj_count
           FROM organizations o
           LEFT JOIN businesses b ON b.org_id = o.id
           LEFT JOIN projects   p ON p.business_id = b.id
           GROUP BY o.id ORDER BY o.name"""
    ).fetchall()

    # Businesses grouped by org (for folder settings)
    businesses = db.execute(
        """SELECT b.id, b.name, b.folder_path,
                  o.name AS org_name, o.color AS org_color
           FROM businesses b
           LEFT JOIN organizations o ON o.id = b.org_id
           ORDER BY o.name, b.name"""
    ).fetchall()

    tags = db.execute(
        """SELECT t.id, t.name, t.color_hue,
                  COUNT(it.item_id) AS usage_count
           FROM tags t
           LEFT JOIN item_tags it ON it.tag_id = t.id
           GROUP BY t.id ORDER BY t.name"""
    ).fetchall()

    labels = db.execute(
        """SELECT l.id, l.name, l.color, l.type,
                  COUNT(il.item_id) AS usage_count
           FROM labels l
           LEFT JOIN item_labels il ON il.label_id = l.id
           GROUP BY l.id ORDER BY l.type DESC, l.name"""
    ).fetchall()

    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "notes_root":   notes_root,
            "orgs":         [dict(o) for o in orgs],
            "org_colors":   _ORG_COLORS,
            "businesses":   [dict(b) for b in businesses],
            "tags":         [dict(t) for t in tags],
            "labels":       [dict(l) for l in labels],
            "gh_set":       _secret_is_set("MC_GH_PAT"),
            "tg_set":       _secret_is_set("MC_TG_BOT_TOKEN"),
            "gcal_set":     has_gcal_token() or _secret_is_set(_GCAL_SECRET_KEY),
        },
    )


@router.post("/settings/folder", response_class=HTMLResponse)
async def settings_folder(
    notes_root: Annotated[str, Form()] = "",
    db: sqlite3.Connection = Depends(get_db),
):
    path = notes_root.strip()
    if path:
        Path(path).mkdir(parents=True, exist_ok=True)
        _save_setting(db, "mc_notes_root", path)
        (Path(path) / "inbox").mkdir(exist_ok=True)
    reload_config()
    return HTMLResponse(
        f'<span id="folder-saved" style="color:var(--st-done); font-size:12px;">✓ 저장됨 — {path or "기본값"}</span>'
    )


@router.post("/settings/org", response_class=HTMLResponse)
async def settings_add_org(
    request: Request,
    name:  Annotated[str, Form()],
    color: Annotated[str, Form()] = "oklch(58% 0.18 280)",
    db: sqlite3.Connection = Depends(get_db),
):
    name = name.strip()
    if not name:
        return HTMLResponse('<span style="color:oklch(60% 0.21 25)">이름을 입력하세요</span>', status_code=422)
    db.execute(
        "INSERT OR IGNORE INTO organizations(name, color) VALUES(?,?)",
        (name, color),
    )
    # B-005: auto-create MC-Notes/{org}/ folder
    notes_root = _get_setting(db, "mc_notes_root")
    if notes_root:
        from ..integrations import ensure_org_folder
        ensure_org_folder(notes_root, name)

    orgs = db.execute("SELECT id, name, color FROM organizations ORDER BY name").fetchall()
    return templates.TemplateResponse(
        request,
        "partials/org_list.html",
        {"orgs": [dict(o) for o in orgs]},
    )


@router.delete("/settings/org/{org_id}", response_class=HTMLResponse)
async def settings_delete_org(
    request: Request,
    org_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    # BR-ORG-01: only delete if no businesses
    biz_count = db.execute(
        "SELECT COUNT(*) FROM businesses WHERE org_id=?", (org_id,)
    ).fetchone()[0]
    if biz_count > 0:
        return HTMLResponse(
            '<span style="color:oklch(60% 0.21 25); font-size:12px;">⚠ 하위 사업이 있어 삭제 불가</span>',
            status_code=409,
        )
    db.execute("DELETE FROM organizations WHERE id=?", (org_id,))
    orgs = db.execute("SELECT id, name, color FROM organizations ORDER BY name").fetchall()
    return templates.TemplateResponse(
        request,
        "partials/org_list.html",
        {"orgs": [dict(o) for o in orgs]},
    )


@router.patch("/settings/business/{biz_id}/folder", response_class=HTMLResponse)
async def settings_business_folder(
    biz_id: int,
    folder_path: Annotated[str, Form()] = "",
    db: sqlite3.Connection = Depends(get_db),
):
    path = folder_path.strip()
    db.execute(
        "UPDATE businesses SET folder_path=? WHERE id=?",
        (path or None, biz_id),
    )
    icon = "✓" if path else "—"
    color = "var(--st-done)" if path else "var(--muted)"
    return HTMLResponse(
        f'<span style="font-size:11px; color:{color};">{icon} {"저장됨" if path else "비어 있음"}</span>'
    )


# ── Tag management ────────────────────────────────────────────────────────────

def _render_tags(request, db: sqlite3.Connection):
    tags = db.execute(
        """SELECT t.id, t.name, t.color_hue,
                  COUNT(it.item_id) AS usage_count
           FROM tags t LEFT JOIN item_tags it ON it.tag_id = t.id
           GROUP BY t.id ORDER BY t.name"""
    ).fetchall()
    return templates.TemplateResponse(
        request, "partials/settings_tags.html", {"tags": [dict(t) for t in tags]}
    )


@router.post("/settings/tags", response_class=HTMLResponse)
async def settings_add_tag(
    request: Request,
    name:      Annotated[str, Form()],
    color_hue: Annotated[int, Form()] = 265,
    db: sqlite3.Connection = Depends(get_db),
):
    name = name.strip()
    if not name:
        return HTMLResponse('<span style="color:oklch(60% 0.21 25)">이름을 입력하세요</span>', status_code=422)
    db.execute(
        "INSERT OR IGNORE INTO tags(name, color_hue) VALUES(?,?)",
        (name, max(0, min(360, color_hue))),
    )
    return _render_tags(request, db)


@router.delete("/settings/tags/{tag_id}", response_class=HTMLResponse)
async def settings_delete_tag(
    request: Request,
    tag_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute("DELETE FROM tags WHERE id=?", (tag_id,))
    return _render_tags(request, db)


# ── Label management ──────────────────────────────────────────────────────────

def _render_labels(request, db: sqlite3.Connection):
    labels = db.execute(
        """SELECT l.id, l.name, l.color, l.type,
                  COUNT(il.item_id) AS usage_count
           FROM labels l LEFT JOIN item_labels il ON il.label_id = l.id
           GROUP BY l.id ORDER BY l.type DESC, l.name"""
    ).fetchall()
    return templates.TemplateResponse(
        request, "partials/settings_labels.html", {"labels": [dict(l) for l in labels]}
    )


@router.post("/settings/labels", response_class=HTMLResponse)
async def settings_add_label(
    request: Request,
    name:  Annotated[str, Form()],
    color: Annotated[str, Form()] = "#a78bfa",
    db: sqlite3.Connection = Depends(get_db),
):
    name = name.strip()
    if not name:
        return HTMLResponse('<span style="color:oklch(60% 0.21 25)">이름을 입력하세요</span>', status_code=422)
    db.execute(
        "INSERT OR IGNORE INTO labels(name, color, type) VALUES(?,?,'custom')",
        (name, color),
    )
    return _render_labels(request, db)


@router.delete("/settings/labels/{label_id}", response_class=HTMLResponse)
async def settings_delete_label(
    request: Request,
    label_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute("SELECT type FROM labels WHERE id=?", (label_id,)).fetchone()
    if row and row["type"] == "system":
        return HTMLResponse('<span style="color:oklch(60% 0.21 25); font-size:12px;">시스템 라벨은 삭제 불가</span>', status_code=409)
    db.execute("DELETE FROM labels WHERE id=? AND type='custom'", (label_id,))
    return _render_labels(request, db)


@router.post("/settings/credential", response_class=HTMLResponse)
async def settings_credential(
    service: Annotated[str, Form()],
    token:   Annotated[str, Form()],
):
    """Store a secret in Windows Credential Manager (ADR-005)."""
    key_map = {"gh": "MC_GH_PAT", "tg": "MC_TG_BOT_TOKEN", "gcal": _GCAL_SECRET_KEY}
    key = key_map.get(service)
    if not key:
        return HTMLResponse('<span style="color:oklch(60% 0.21 25)">알 수 없는 서비스</span>', status_code=422)

    token = token.strip()
    if not token:
        return HTMLResponse('<span style="color:oklch(60% 0.21 25)">토큰을 입력하세요</span>', status_code=422)

    ok, err = _try_save_secret(key, token)
    if ok:
        return HTMLResponse(
            f'<span id="cred-{service}-result" style="color:var(--st-done); font-size:12px;">✓ 저장됨 (Windows Credential Manager)</span>'
        )
    return HTMLResponse(
        f'<span style="color:oklch(60% 0.21 25); font-size:12px;">✕ 저장 실패: {err}</span>',
        status_code=500,
    )


@router.post("/api/seed-dev")
async def seed_dev(db: sqlite3.Connection = Depends(get_db)):
    """Re-run dev seed data (wipes and recreates sample orgs/projects/items)."""
    import subprocess, sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "src.tools.seed_dev", "--reset"],
        capture_output=True, text=True, cwd=str(project_root),
    )
    if result.returncode != 0:
        return JSONResponse({"ok": False, "error": result.stderr}, status_code=500)
    return JSONResponse({"ok": True})
