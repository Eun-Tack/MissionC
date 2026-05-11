"""
AI-free suggestion endpoint — rule-based type/tag/project classification.

GET /api/ai/suggest?q=<text>
"""

from __future__ import annotations
import sqlite3

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..db import get_db

router = APIRouter()

_SCHEDULE_KEYWORDS = {"회의", "미팅", "스탠드업", "발표", "컨퍼런스", "약속", "세미나"}
_MEMO_KEYWORDS = {"메모", "정리", "기록", "노트", "아이디어", "생각", "초안", "draft"}


def _detect_type(title: str) -> str:
    lower = title.lower()
    if any(k in lower for k in _SCHEDULE_KEYWORDS):
        return "schedule"
    if any(k in lower for k in _MEMO_KEYWORDS):
        return "memo"
    return "task"


def _suggest_tags(db: sqlite3.Connection, title: str) -> list[dict]:
    lower = title.lower()
    rows = db.execute("SELECT id, name FROM tags").fetchall()
    matched = [{"id": r[0], "name": r[1]} for r in rows if r[1].lower() in lower]
    return matched[:5]


def _suggest_project(db: sqlite3.Connection, title: str) -> dict | None:
    lower_words = set(title.lower().split())
    if not lower_words:
        return None
    rows = db.execute(
        "SELECT id, title FROM projects WHERE status != 'archived'"
    ).fetchall()
    best_id, best_title, best_score = None, None, 0
    for r in rows:
        proj_lower = r[1].lower()
        score = sum(1 for w in lower_words if w in proj_lower)
        if score > best_score:
            best_id, best_title, best_score = r[0], r[1], score
    if best_score > 0:
        return {"id": best_id, "title": best_title}
    return None


@router.get("/api/ai/suggest")
def ai_suggest(q: str = "", db: sqlite3.Connection = Depends(get_db)):
    q = q.strip()
    if not q:
        return JSONResponse({
            "type": "task",
            "tags": [],
            "project": None,
            "reason": "empty query",
        })

    item_type = _detect_type(q)
    tags = _suggest_tags(db, q)
    project = _suggest_project(db, q)

    return JSONResponse({
        "type": item_type,
        "tags": tags,
        "project": project,
        "reason": "keyword match",
    })
