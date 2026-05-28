"""
secret-bridge — Windows Credential Manager HTTP proxy (ADR-005).
Port 9999, loopback only. Never called from outside 127.0.0.1.

Start:  python -m uvicorn src.secret_bridge.main:app --port 9999 --host 127.0.0.1
Or via: Task Scheduler (ADR-008)
"""

from __future__ import annotations
import ipaddress

from fastapi import FastAPI, HTTPException, Request
import keyring

ALLOWED_KEYS = {"MC_GH_PAT", "MC_TG_BOT_TOKEN", "MC_GCAL_TOKEN"}
_KEYRING_USER = "iet03"

app = FastAPI(title="MC secret-bridge", docs_url=None, redoc_url=None)


@app.middleware("http")
async def loopback_only(request: Request, call_next):
    """Reject any request that isn't from 127.0.0.1 (ADR-005)."""
    client_host = request.client.host if request.client else ""
    try:
        addr = ipaddress.ip_address(client_host)
    except ValueError:
        raise HTTPException(403, "Forbidden")
    if not addr.is_loopback:
        raise HTTPException(403, "Loopback only")
    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "secret-bridge"}


@app.get("/secret/{key}")
def get_secret(key: str):
    if key not in ALLOWED_KEYS:
        raise HTTPException(404, f"Unknown key: {key}")
    val = keyring.get_password(key, _KEYRING_USER)
    if not val:
        raise HTTPException(404, f"Secret not set: {key}")
    return {"value": val}


@app.put("/secret/{key}")
async def set_secret(key: str, request: Request):
    """Set a secret (used by secret_set.py CLI)."""
    if key not in ALLOWED_KEYS:
        raise HTTPException(404, f"Unknown key: {key}")
    body = await request.json()
    value = body.get("value", "")
    if not value:
        raise HTTPException(422, "value required")
    keyring.set_password(key, _KEYRING_USER, value)
    return {"ok": True}


@app.delete("/secret/{key}")
def delete_secret(key: str):
    if key not in ALLOWED_KEYS:
        raise HTTPException(404)
    try:
        keyring.delete_password(key, _KEYRING_USER)
    except keyring.errors.PasswordDeleteError:
        pass
    return {"ok": True}
