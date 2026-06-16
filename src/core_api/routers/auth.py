"""
Google OAuth 로그인 (단일 사용자 — 본인 계정만 허용)

GET  /auth/login      — Google OAuth 시작
GET  /auth/callback   — Google redirect 수신 → 세션 저장
GET  /auth/logout     — 세션 삭제

환경 변수:
  GOOGLE_CLIENT_ID      — GCP OAuth 클라이언트 ID
  GOOGLE_CLIENT_SECRET  — GCP OAuth 클라이언트 시크릿
  ALLOWED_EMAIL         — 허용할 이메일 (예: iet030507@gmail.com)
  APP_URL               — 배포 URL (예: https://mc.railway.app) — callback 생성용

GOOGLE_CLIENT_ID 미설정 시 인증 건너뜀 (로컬 개발 편의).
"""

from __future__ import annotations
import json
import os
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path

from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/auth", tags=["auth"])
_templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

_GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

_SCOPE      = "openid email profile"
_GCAL_SCOPE = "https://www.googleapis.com/auth/calendar.events"
_KEYRING_USER = "iet03"
_GCAL_SECRET_KEY = "MC_GCAL_TOKEN"
_LEGACY_GCAL_SECRET_KEY = "MC_GOOGLE_OAUTH"


def _cfg() -> dict:
    return {
        "client_id":     os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "allowed_email": os.environ.get("ALLOWED_EMAIL", ""),
        "app_url":       os.environ.get("APP_URL", ""),
    }


def _gcal_cfg() -> dict:
    """GCal 전용 credentials — MC_GOOGLE_CLIENT_ID/SECRET 우선, GOOGLE_* fallback."""
    return {
        "client_id":     os.environ.get("MC_GOOGLE_CLIENT_ID") or os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("MC_GOOGLE_CLIENT_SECRET") or os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "app_url":       os.environ.get("APP_URL", ""),
    }


def _callback_base(request: Request, configured_app_url: str) -> str:
    base = (configured_app_url or "").strip().rstrip("/")
    if base:
        return base
    return f"{request.url.scheme}://{request.url.netloc}"


def _load_gcal_token() -> dict:
    try:
        import keyring
        token_json = keyring.get_password(_GCAL_SECRET_KEY, _KEYRING_USER)
        if not token_json:
            token_json = keyring.get_password(_LEGACY_GCAL_SECRET_KEY, _KEYRING_USER)
            if token_json:
                keyring.set_password(_GCAL_SECRET_KEY, _KEYRING_USER, token_json)
        return json.loads(token_json) if token_json else {}
    except Exception:
        return {}


def _save_gcal_token(token_data: dict) -> None:
    import keyring
    keyring.set_password(_GCAL_SECRET_KEY, _KEYRING_USER, json.dumps(token_data))


def has_gcal_token() -> bool:
    data = _load_gcal_token()
    return bool(data.get("refresh_token") or data.get("access_token"))


def _remember_oauth_state(kind: str, state: str) -> None:
    try:
        from ..db import get_connection
        with get_connection() as db:
            db.execute(
                """INSERT INTO settings(key, value, updated_at)
                   VALUES(?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                   ON CONFLICT(key) DO UPDATE SET
                     value=excluded.value,
                     updated_at=excluded.updated_at""",
                (f"oauth_state_{kind}", state),
            )
    except Exception:
        pass


def _consume_oauth_state(kind: str, state: str) -> bool:
    session_state_ok = bool(state)
    try:
        from ..db import get_connection
        with get_connection() as db:
            row = db.execute(
                "SELECT value FROM settings WHERE key=?",
                (f"oauth_state_{kind}",),
            ).fetchone()
            db.execute("DELETE FROM settings WHERE key=?", (f"oauth_state_{kind}",))
            return session_state_ok and bool(row and row["value"] == state)
    except Exception:
        return False


def auth_enabled() -> bool:
    return bool(os.environ.get("GOOGLE_CLIENT_ID"))


def is_authenticated(request: Request) -> bool:
    if not auth_enabled():
        return True  # 로컬 개발 — 인증 없이 통과
    return bool(request.session.get("user_email"))


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """로그인 페이지 표시. 이미 인증됐으면 홈으로."""
    if is_authenticated(request):
        return RedirectResponse("/")
    return _templates.TemplateResponse(request, "login.html", {})


@router.get("/login/google")
async def login_google(request: Request):
    """Google OAuth 흐름 시작."""
    cfg = _cfg()
    if not cfg["client_id"]:
        return RedirectResponse("/")  # OAuth 미설정 → 그냥 통과

    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    _remember_oauth_state("login", state)

    callback_url = f"{_callback_base(request, cfg['app_url'])}/auth/callback"
    url = (
        f"{_GOOGLE_AUTH_URL}"
        f"?client_id={cfg['client_id']}"
        f"&redirect_uri={callback_url}"
        f"&response_type=code"
        f"&scope={_SCOPE.replace(' ', '+')}"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=select_account"
    )
    return RedirectResponse(url)


@router.get("/callback", response_class=HTMLResponse)
async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    cfg = _cfg()

    if error:
        return HTMLResponse(_error_page(f"Google 인증 거절: {error}"), status_code=403)

    session_state = request.session.pop("oauth_state", None)
    if state != session_state and not _consume_oauth_state("login", state):
        return HTMLResponse(_error_page("잘못된 state 값입니다. 다시 로그인해주세요."), status_code=400)

    callback_url = f"{_callback_base(request, cfg['app_url'])}/auth/callback"

    async with httpx.AsyncClient(timeout=10) as client:
        # 코드 → 토큰 교환
        token_res = await client.post(_GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri":  callback_url,
            "grant_type":    "authorization_code",
        })
        if token_res.status_code != 200:
            return HTMLResponse(_error_page("토큰 교환 실패. 다시 시도해주세요."), status_code=500)

        access_token = token_res.json().get("access_token")

        # 사용자 정보 조회
        user_res = await client.get(
            _GOOGLE_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            return HTMLResponse(_error_page("사용자 정보 조회 실패."), status_code=500)

    user = user_res.json()
    email = user.get("email", "")

    # 허용 이메일 확인
    allowed = cfg["allowed_email"]
    if allowed and email.lower() != allowed.lower():
        return HTMLResponse(_error_page(
            f"접근 거부: {email} 은(는) 허용된 계정이 아닙니다."
        ), status_code=403)

    # 세션 저장
    request.session["user_email"] = email
    request.session["user_name"]  = user.get("name", email)
    request.session["user_pic"]   = user.get("picture", "")

    return RedirectResponse("/")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/auth/login")


# ── Google Calendar OAuth ─────────────────────────────────────────────────────

@router.get("/gcal/connect")
async def gcal_connect(request: Request):
    """GCal OAuth 시작 — calendar.readonly 스코프."""
    if request.query_params.get("force") != "1" and has_gcal_token():
        return RedirectResponse("/settings?gcal=connected")

    cfg = _gcal_cfg()
    if not cfg["client_id"]:
        return HTMLResponse("MC_GOOGLE_CLIENT_ID 미설정 — .env 파일을 확인하세요.", status_code=500)

    state = secrets.token_urlsafe(16)
    request.session["gcal_state"] = state
    _remember_oauth_state("gcal", state)

    callback_url = f"{_callback_base(request, cfg['app_url'])}/auth/gcal/callback"
    url = f"{_GOOGLE_AUTH_URL}?{urlencode({
        'client_id': cfg['client_id'],
        'redirect_uri': callback_url,
        'response_type': 'code',
        'scope': _GCAL_SCOPE,
        'state': state,
        'access_type': 'offline',
        'prompt': 'consent',
        'include_granted_scopes': 'true',
    })}"
    return RedirectResponse(url)


@router.get("/gcal/callback")
async def gcal_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    """GCal OAuth 콜백 — 토큰 저장 후 /settings 로 리디렉트."""
    cfg = _gcal_cfg()

    if error:
        return HTMLResponse(_error_page(f"GCal 연결 거절: {error}"), status_code=403)

    session_state = request.session.pop("gcal_state", None)
    if state != session_state and not _consume_oauth_state("gcal", state):
        return HTMLResponse(_error_page("state 불일치. 다시 시도해주세요."), status_code=400)

    callback_url = f"{_callback_base(request, cfg['app_url'])}/auth/gcal/callback"

    async with httpx.AsyncClient(timeout=10) as client:
        token_res = await client.post(_GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri":  callback_url,
            "grant_type":    "authorization_code",
        })
        if token_res.status_code != 200:
            return HTMLResponse(_error_page(f"GCal 토큰 교환 실패: {token_res.text}"), status_code=500)

    tokens = token_res.json()
    existing = _load_gcal_token()
    token_data = {
        "access_token":  tokens.get("access_token", ""),
        "refresh_token": tokens.get("refresh_token") or existing.get("refresh_token", ""),
        "token_type":    tokens.get("token_type", "Bearer"),
    }
    try:
        _save_gcal_token(token_data)
    except Exception as e:
        return HTMLResponse(_error_page(f"토큰 저장 실패: {e}"), status_code=500)

    return RedirectResponse("/settings?gcal=connected")


# ── 에러 페이지 ───────────────────────────────────────────────────────────────

def _error_page(msg: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<title>인증 오류 · MC</title>
<style>
  body {{ font-family: system-ui, sans-serif; display: flex; align-items: center;
         justify-content: center; min-height: 100vh; background: #fafafa; }}
  .box {{ text-align: center; padding: 40px; max-width: 400px; }}
  h1 {{ font-size: 20px; margin-bottom: 12px; color: #111; }}
  p  {{ font-size: 14px; color: #666; margin-bottom: 24px; }}
  a  {{ display: inline-block; padding: 10px 20px; background: #7c3aed; color: white;
       border-radius: 8px; text-decoration: none; font-size: 14px; }}
</style></head>
<body><div class="box">
  <h1>⚠ 인증 오류</h1>
  <p>{msg}</p>
  <a href="/auth/login">다시 로그인</a>
</div></body></html>"""
