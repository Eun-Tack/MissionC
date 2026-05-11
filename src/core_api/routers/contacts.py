"""
Contacts — people to attach to schedule items (attendees, organizers).

GET  /contacts                        → contacts page
GET  /api/contacts?q=                 → JSON search (autocomplete)
POST /api/contacts                    → create contact
DELETE /api/contacts/{id}             → delete contact

GET  /api/items/{id}/contacts         → JSON list attached to item
GET  /api/items/{id}/contacts/partial → HTML partial (for htmx load)
POST /api/items/{id}/contacts         → attach contact (or create+attach by name)
DELETE /api/items/{id}/contacts/{cid} → detach contact
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

_AVATAR_COLORS = [
    "oklch(55% 0.18 280)", "oklch(55% 0.18 160)", "oklch(55% 0.18 40)",
    "oklch(55% 0.18 20)",  "oklch(55% 0.18 200)", "oklch(55% 0.18 320)",
]


def _avatar_color(name: str) -> str:
    return _AVATAR_COLORS[ord(name[0].upper()) % len(_AVATAR_COLORS)]


def _contact_row_html(c: dict) -> str:
    color = _avatar_color(c["name"])
    sub = " · ".join(filter(None, [c.get("email") or "", c.get("org") or ""]))
    return f"""<div class="contact-row" id="contact-{c['id']}">
  <div class="contact-avatar" style="background:{color}">{c['name'][0].upper()}</div>
  <div class="contact-info">
    <div class="contact-name">{c['name']}</div>
    {"<div class='contact-sub'>" + sub + "</div>" if sub else ""}
  </div>
  <button class="contact-del"
          hx-delete="/api/contacts/{c['id']}"
          hx-target="closest .contact-row"
          hx-swap="outerHTML"
          hx-confirm="삭제?">✕</button>
</div>"""


def _attendee_pill_html(item_id: int, c: dict) -> str:
    color = _avatar_color(c["name"])
    return f"""<span class="attendee-pill" id="att-{item_id}-{c['id']}">
  <span class="att-av" style="background:{color}">{c['name'][0].upper()}</span>
  {c['name']}
  <span class="att-x"
        hx-delete="/api/items/{item_id}/contacts/{c['id']}"
        hx-target="closest .attendee-pill"
        hx-swap="outerHTML">×</span>
</span>"""


@router.get("/contacts", response_class=HTMLResponse)
async def contacts_page(request: Request, db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM contacts ORDER BY name").fetchall()
    return templates.TemplateResponse(
        request, "contacts.html",
        {"contacts": [dict(r) for r in rows]}
    )


@router.get("/api/contacts")
async def list_contacts(q: str = "", db: sqlite3.Connection = Depends(get_db)):
    if q:
        rows = db.execute(
            "SELECT id, name, email, org FROM contacts WHERE name LIKE ? OR org LIKE ? ORDER BY name LIMIT 12",
            (f"%{q}%", f"%{q}%"),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT id, name, email, org FROM contacts ORDER BY name LIMIT 20"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/contacts", response_class=HTMLResponse)
async def create_contact(
    name: Annotated[str, Form()],
    email: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
    org: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
    db: sqlite3.Connection = Depends(get_db),
):
    if not name.strip():
        raise HTTPException(422, "Name required")
    cur = db.execute(
        "INSERT INTO contacts(name, email, phone, org, notes) VALUES(?,?,?,?,?)",
        (name.strip(), email or None, phone or None, org or None, notes or None),
    )
    c = dict(db.execute("SELECT * FROM contacts WHERE id=?", (cur.lastrowid,)).fetchone())
    return HTMLResponse(_contact_row_html(c))


@router.delete("/api/contacts/{contact_id}", response_class=HTMLResponse)
async def delete_contact(contact_id: int, db: sqlite3.Connection = Depends(get_db)):
    db.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
    return HTMLResponse("")


@router.get("/api/items/{item_id}/contacts")
async def get_item_contacts(item_id: int, db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        """SELECT c.id, c.name, c.email, c.org, ic.role
           FROM item_contacts ic JOIN contacts c ON c.id=ic.contact_id
           WHERE ic.item_id=? ORDER BY c.name""",
        (item_id,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/items/{item_id}/contacts/partial", response_class=HTMLResponse)
async def item_contacts_partial(
    request: Request, item_id: int, db: sqlite3.Connection = Depends(get_db)
):
    rows = db.execute(
        """SELECT c.id, c.name, c.email, c.org, ic.role
           FROM item_contacts ic JOIN contacts c ON c.id=ic.contact_id
           WHERE ic.item_id=? ORDER BY c.name""",
        (item_id,),
    ).fetchall()
    contacts = [dict(r) for r in rows]
    all_contacts = db.execute(
        "SELECT id, name, org FROM contacts ORDER BY name"
    ).fetchall()
    return templates.TemplateResponse(
        request, "partials/attendees.html",
        {"item_id": item_id, "contacts": contacts,
         "all_contacts": [dict(r) for r in all_contacts]}
    )


@router.post("/api/items/{item_id}/contacts", response_class=HTMLResponse)
async def add_item_contact(
    item_id: int,
    contact_id: Annotated[str, Form()] = "",
    name: Annotated[str, Form()] = "",
    role: Annotated[str, Form()] = "attendee",
    db: sqlite3.Connection = Depends(get_db),
):
    cid = int(contact_id) if contact_id.strip() else None
    if not cid and name.strip():
        cur = db.execute("INSERT INTO contacts(name) VALUES(?)", (name.strip(),))
        cid = cur.lastrowid
    if not cid:
        raise HTTPException(422, "contact_id or name required")
    db.execute(
        "INSERT OR IGNORE INTO item_contacts(item_id, contact_id, role) VALUES(?,?,?)",
        (item_id, cid, role),
    )
    c = dict(db.execute(
        "SELECT id, name, email, org FROM contacts WHERE id=?", (cid,)
    ).fetchone())
    return HTMLResponse(_attendee_pill_html(item_id, c))


@router.delete("/api/items/{item_id}/contacts/{contact_id}", response_class=HTMLResponse)
async def remove_item_contact(
    item_id: int, contact_id: int, db: sqlite3.Connection = Depends(get_db)
):
    db.execute(
        "DELETE FROM item_contacts WHERE item_id=? AND contact_id=?",
        (item_id, contact_id),
    )
    return HTMLResponse("")
