"""Shared pytest fixtures."""

import sqlite3
import tempfile
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SCHEMA_PATH  = PROJECT_ROOT / "Doc" / "phase4_design" / "schema" / "mc_schema.sql"


@pytest.fixture
def tmp_db(tmp_path: Path) -> sqlite3.Connection:
    """Provide a fresh in-memory-equivalent DB with schema applied."""
    db_path = tmp_path / "test_mc.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.execute("PRAGMA user_version = 7")
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Return path to a fresh DB file (for migrate.py tests)."""
    return tmp_path / "mc_test.db"
