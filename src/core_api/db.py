"""SQLite connection management for core-api."""

import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_DB   = PROJECT_ROOT / "data" / "mc.db"

DB_PATH = Path(os.environ.get("MC_DB_PATH", _DEFAULT_DB))


def _make_connection(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.text_factory = str  # always return Python str (UTF-8); reject non-UTF-8 bytes
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def get_connection(path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    conn = _make_connection(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db():
    """FastAPI dependency — yields a committed-on-exit connection."""
    with get_connection() as conn:
        yield conn


def fetchall_as_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def fetchone_as_dict(cursor: sqlite3.Cursor) -> dict | None:
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))
