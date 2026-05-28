"""MC core-api — FastAPI application entrypoint. Port 8000."""

from __future__ import annotations
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import reload_config
from .routers import flow, items, hierarchy, review, setup, inbox, diagnostics, search, calendar, wbs, voice, notifications, dashboard, ai_suggest, contacts, auth

log = logging.getLogger("mc.main")

_STATIC_DIR = Path(__file__).parent / "static"
_PROJECT_ROOT = Path(__file__).parent.parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env")
except ImportError:
    pass


def _start_scheduler():
    # Background polling disabled for local use — syncs happen on-demand per page.
    # Re-enable when deploying to cloud (Railway).
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from .integrations import expire_stale_inbox

        sched = AsyncIOScheduler(timezone="UTC")
        sched.add_job(expire_stale_inbox, "interval", hours=6, id="inbox_expire", misfire_grace_time=600)
        sched.start()
        log.info("APScheduler started (inbox_expire=6h; gh/tg/gcal on-demand)")
        return sched
    except ImportError:
        log.warning("apscheduler not installed — background tasks disabled")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = reload_config()
    app.state.scheduler = _start_scheduler()
    yield
    if app.state.scheduler:
        app.state.scheduler.shutdown(wait=False)


app = FastAPI(
    title="MC core-api",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# Auth guard must be registered BEFORE SessionMiddleware so that after reversal
# SessionMiddleware wraps auth_guard (SessionMiddleware runs first on each request).
_PUBLIC_PREFIXES = ("/auth/", "/health", "/static/", "/favicon")

@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path
    if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return await call_next(request)
    if not auth.is_authenticated(request):
        return RedirectResponse("/auth/login")
    return await call_next(request)

# SessionMiddleware added last → outermost layer → runs before auth_guard
_SESSION_SECRET = os.environ.get("SESSION_SECRET", "mc-dev-secret-change-in-prod")
app.add_middleware(SessionMiddleware, secret_key=_SESSION_SECRET, https_only=False)

# Static files (app.js, radial.css, radial.js …)
_STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# Routers — auth first, then setup (owns /setup, /settings, /api/pick-folder)
app.include_router(auth.router)
app.include_router(setup.router)
app.include_router(flow.router)
app.include_router(items.router)
app.include_router(hierarchy.router)
app.include_router(review.router)
app.include_router(inbox.router)
app.include_router(diagnostics.router)
app.include_router(search.router)
app.include_router(calendar.router)
app.include_router(wbs.router)
app.include_router(voice.router)
app.include_router(notifications.router)
app.include_router(dashboard.router)
app.include_router(ai_suggest.router)
app.include_router(contacts.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "core-api"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # Inline 1×1 purple SVG favicon — no file needed
    from fastapi.responses import Response
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="oklch(58%25 0.18 280)"/><text x="16" y="22" text-anchor="middle" font-size="18" font-weight="800" fill="white" font-family="system-ui">M</text></svg>'
    return Response(content=svg, media_type="image/svg+xml")


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse({"error": "not found", "path": str(request.url)}, status_code=404)


@app.exception_handler(500)
async def server_error(request: Request, exc):
    return JSONResponse({"error": "internal server error"}, status_code=500)
