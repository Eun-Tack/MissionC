"""Application configuration — reads from the `settings` table at startup."""

from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass, field
from .db import get_connection


@dataclass
class MCConfig:
    mc_notes_root: str = ""
    secret_bridge_url: str = "http://127.0.0.1:9999"
    embedding_model: str = "KoE5"
    embedding_dim: int = 384
    ai_capability_level: str = "unknown"
    gcal_poll_interval_min: int = 30
    gcal_sync_days_range: int = 7
    tag_normalize_threshold: float = 0.85
    memo_inbox_default_path: str = "inbox"
    memo_editor: str = "milkdown"
    worker_statuses: dict[str, str] = field(default_factory=dict)

    @property
    def notes_root(self) -> Path:
        if self.mc_notes_root:
            return Path(self.mc_notes_root)
        return Path.home() / "Documents" / "MC-Notes"


def load_config() -> MCConfig:
    cfg = MCConfig()
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            settings = {r["key"]: r["value"] for r in rows}

        cfg.mc_notes_root          = settings.get("mc_notes_root", "")
        cfg.secret_bridge_url      = settings.get("secret_bridge_url", cfg.secret_bridge_url)
        cfg.embedding_model        = settings.get("embedding_model", cfg.embedding_model)
        cfg.embedding_dim          = int(settings.get("embedding_dim", cfg.embedding_dim))
        cfg.ai_capability_level    = settings.get("ai_capability_level", cfg.ai_capability_level)
        cfg.gcal_poll_interval_min = int(settings.get("gcal_poll_interval_min", cfg.gcal_poll_interval_min))
        cfg.gcal_sync_days_range   = int(settings.get("gcal_sync_days_range", cfg.gcal_sync_days_range))
        cfg.tag_normalize_threshold = float(settings.get("tag_normalize_threshold", cfg.tag_normalize_threshold))
        cfg.memo_inbox_default_path = settings.get("memo_inbox_default_path", cfg.memo_inbox_default_path)
        cfg.memo_editor            = settings.get("memo_editor", cfg.memo_editor)
        cfg.worker_statuses = {
            k.removeprefix("worker_status_"): v
            for k, v in settings.items()
            if k.startswith("worker_status_")
        }
    except Exception:
        pass  # DB not yet initialized — return defaults
    return cfg


# Module-level singleton; refreshed on demand via reload_config()
_config: MCConfig | None = None


def get_config() -> MCConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> MCConfig:
    global _config
    _config = load_config()
    return _config
