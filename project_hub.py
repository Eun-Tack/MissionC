from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = DATA_DIR / "project_hub.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    area TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'idea',
    priority TEXT NOT NULL DEFAULT 'P2',
    path TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    vision TEXT NOT NULL DEFAULT '',
    energy INTEGER NOT NULL DEFAULT 50,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    label TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    progress INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'todo',
    due TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    cleaned = []
    last_dash = False
    for char in value.strip().lower():
        if char.isalnum() or "\uac00" <= char <= "\ud7a3":
            cleaned.append(char)
            last_dash = False
        elif not last_dash:
            cleaned.append("-")
            last_dash = True
    slug = "".join(cleaned).strip("-")
    return slug or "project"


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_storage()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA)


def seed_if_empty() -> None:
    with get_connection() as connection:
        count = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        if count:
            return
        created_at = now_iso()
        project_slug = "founder-operating-system"
        connection.execute(
            """
            INSERT INTO projects (slug, name, area, status, priority, path, summary, vision, energy, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_slug,
                "Founder Operating System",
                "leadership",
                "active",
                "P1",
                str(BASE_DIR),
                "대표 업무, 연구, 개발을 하나의 리듬으로 묶는 개인 운영 시스템",
                "매일의 실행과 장기 비전을 같은 화면에서 관리한다.",
                76,
                created_at,
                created_at,
            ),
        )
        project_id = connection.execute(
            "SELECT id FROM projects WHERE slug = ?",
            (project_slug,),
        ).fetchone()[0]
        connection.executemany(
            """
            INSERT INTO links (project_id, kind, label, value, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (project_id, "folder", "Workspace", str(BASE_DIR), created_at),
                (project_id, "account", "Main AI Stack", "OpenAI / local experiments", created_at),
                (project_id, "reference", "North Star", "몰입과 실행 속도를 동시에 높이는 운영 시스템", created_at),
            ],
        )
        connection.executemany(
            """
            INSERT INTO logs (project_id, summary, status, progress, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (project_id, "로컬 기반 프로젝트 허브 초안 정의", "working", 20, created_at),
                (project_id, "웹 인터페이스와 SQLite 구조 설계", "review", 45, created_at),
            ],
        )
        connection.executemany(
            """
            INSERT INTO notes (project_id, kind, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            [
                (project_id, "decision", "업무를 카테고리가 아니라 프로젝트와 흐름 단위로 본다.", created_at),
                (project_id, "memo", "링크, 메모, 할 일을 한 화면에서 빠르게 연결할 수 있어야 한다.", created_at),
            ],
        )
        connection.executemany(
            """
            INSERT INTO tasks (project_id, title, status, due, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (project_id, "주간 운영 리뷰 화면 정리", "doing", "2026-04-27", created_at),
                (project_id, "연구 아이디어 인박스 프로젝트 추가", "todo", "2026-04-28", created_at),
            ],
        )


def row_to_project(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "area": row["area"],
        "status": row["status"],
        "priority": row["priority"],
        "path": row["path"],
        "summary": row["summary"],
        "vision": row["vision"],
        "energy": row["energy"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_projects() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT p.*,
                   SUM(CASE WHEN t.status != 'done' THEN 1 ELSE 0 END) AS open_tasks,
                   MAX(l.created_at) AS last_log_at
            FROM projects p
            LEFT JOIN tasks t ON t.project_id = p.id
            LEFT JOIN logs l ON l.project_id = p.id
            GROUP BY p.id
            ORDER BY
                CASE p.priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END,
                p.updated_at DESC
            """
        ).fetchall()
    projects = []
    for row in rows:
        project = row_to_project(row)
        project["open_tasks"] = row["open_tasks"] or 0
        project["last_log_at"] = row["last_log_at"]
        projects.append(project)
    return projects


def get_project_details(project_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            return None
        project = row_to_project(row)
        project["links"] = [
            dict(link)
            for link in connection.execute(
                "SELECT id, kind, label, value, created_at FROM links WHERE project_id = ? ORDER BY id DESC",
                (project_id,),
            ).fetchall()
        ]
        project["logs"] = [
            dict(log)
            for log in connection.execute(
                "SELECT id, summary, status, progress, created_at FROM logs WHERE project_id = ? ORDER BY id DESC LIMIT 12",
                (project_id,),
            ).fetchall()
        ]
        project["notes"] = [
            dict(note)
            for note in connection.execute(
                "SELECT id, kind, content, created_at FROM notes WHERE project_id = ? ORDER BY id DESC LIMIT 12",
                (project_id,),
            ).fetchall()
        ]
        project["tasks"] = [
            dict(task)
            for task in connection.execute(
                "SELECT id, title, status, due, created_at FROM tasks WHERE project_id = ? ORDER BY CASE status WHEN 'doing' THEN 0 WHEN 'todo' THEN 1 WHEN 'waiting' THEN 2 ELSE 3 END, due, id DESC",
                (project_id,),
            ).fetchall()
        ]
        return project


def create_project(payload: dict[str, Any]) -> dict[str, Any]:
    created_at = now_iso()
    slug = payload.get("slug") or slugify(payload["name"])
    values = (
        slug,
        payload["name"],
        payload.get("area", ""),
        payload.get("status", "idea"),
        payload.get("priority", "P2"),
        payload.get("path", ""),
        payload.get("summary", ""),
        payload.get("vision", ""),
        int(payload.get("energy", 50)),
        created_at,
        created_at,
    )
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO projects (slug, name, area, status, priority, path, summary, vision, energy, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        return get_project_details(cursor.lastrowid) or {}


def add_entry(table: str, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    created_at = now_iso()
    with get_connection() as connection:
        if table == "tasks":
            cursor = connection.execute(
                "INSERT INTO tasks (project_id, title, status, due, created_at) VALUES (?, ?, ?, ?, ?)",
                (project_id, payload["title"], payload.get("status", "todo"), payload.get("due", ""), created_at),
            )
        elif table == "logs":
            cursor = connection.execute(
                "INSERT INTO logs (project_id, summary, status, progress, created_at) VALUES (?, ?, ?, ?, ?)",
                (project_id, payload["summary"], payload.get("status", "working"), payload.get("progress"), created_at),
            )
        elif table == "notes":
            cursor = connection.execute(
                "INSERT INTO notes (project_id, kind, content, created_at) VALUES (?, ?, ?, ?)",
                (project_id, payload.get("kind", "memo"), payload["content"], created_at),
            )
        elif table == "links":
            cursor = connection.execute(
                "INSERT INTO links (project_id, kind, label, value, created_at) VALUES (?, ?, ?, ?, ?)",
                (project_id, payload.get("kind", "reference"), payload["label"], payload["value"], created_at),
            )
        else:
            raise ValueError(f"Unsupported table: {table}")
        connection.execute(
            "UPDATE projects SET updated_at = ? WHERE id = ?",
            (created_at, project_id),
        )
        entry_id = cursor.lastrowid
        return dict(
            connection.execute(
                f"SELECT * FROM {table} WHERE id = ?",
                (entry_id,),
            ).fetchone()
        )


def update_task_status(task_id: int, status: str) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id),
        )
        return cursor.rowcount > 0


def fetch_summary() -> dict[str, Any]:
    with get_connection() as connection:
        totals = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM projects) AS project_count,
                (SELECT COUNT(*) FROM tasks WHERE status != 'done') AS open_tasks,
                (SELECT COUNT(*) FROM notes) AS note_count,
                (SELECT COUNT(*) FROM logs) AS log_count,
                (SELECT AVG(energy) FROM projects) AS avg_energy
            """
        ).fetchone()
        radar = [
            {"label": "Leadership", "value": score_projects_by_area(connection, "leadership")},
            {"label": "Research", "value": score_projects_by_area(connection, "research")},
            {"label": "Build", "value": score_projects_by_area(connection, "build")},
            {"label": "Ops", "value": score_projects_by_area(connection, "ops")},
        ]
    return {
        "project_count": totals["project_count"],
        "open_tasks": totals["open_tasks"],
        "note_count": totals["note_count"],
        "log_count": totals["log_count"],
        "avg_energy": int(totals["avg_energy"] or 0),
        "radar": radar,
    }


def score_projects_by_area(connection: sqlite3.Connection, area: str) -> int:
    row = connection.execute(
        "SELECT COALESCE(AVG(energy), 0) AS avg_energy FROM projects WHERE area = ?",
        (area,),
    ).fetchone()
    return int(row["avg_energy"])


def hardware_snapshot() -> dict[str, Any]:
    snapshot = {
        "timestamp": now_iso(),
        "cpu": [],
        "gpu": [],
        "npu": [],
        "ideas": [],
    }
    if sys.platform != "win32":
        snapshot["ideas"] = [
            {
                "title": "Ambient Project Pulse",
                "description": "작업 강도와 일정 밀도를 바탕으로 오늘의 운영 텐션을 시각화합니다.",
            }
        ]
        return snapshot

    commands = {
        "cpu": "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name",
        "gpu": "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
        "npu": "Get-PnpDevice | Where-Object { $_.FriendlyName -match 'NPU|Neural|AI' } | Select-Object -ExpandProperty FriendlyName",
    }
    for key, command in commands.items():
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            snapshot[key] = lines
        except (OSError, subprocess.SubprocessError):
            snapshot[key] = []

    snapshot["ideas"] = build_accelerator_ideas(snapshot)
    return snapshot


def build_accelerator_ideas(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    gpu_ready = bool(snapshot["gpu"])
    npu_ready = bool(snapshot["npu"])
    ideas = [
        {
            "title": "Daily Energy Trailer",
            "description": "하루 로그와 태스크 변화를 바탕으로 짧은 모션 카드나 리캡 이미지를 생성합니다.",
        },
        {
            "title": "Focus Constellation",
            "description": "프로젝트들 사이의 관계와 밀도를 별자리처럼 시각화해 우선순위 충돌을 빠르게 파악합니다.",
        },
    ]
    if gpu_ready:
        ideas.append(
            {
                "title": "Local Vision Board Generator",
                "description": "GPU를 활용해 프로젝트별 무드보드, 커버 이미지, 주간 포스터를 로컬 생성하는 기능을 붙일 수 있습니다.",
            }
        )
    if npu_ready:
        ideas.append(
            {
                "title": "Voice-to-Project Inbox",
                "description": "노트북 NPU 기반 음성 입력이나 요약 모델을 연결해 즉석 메모를 프로젝트 카드로 전환할 수 있습니다.",
            }
        )
    return ideas


def guess_content_type(path: Path) -> str:
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    if path.suffix == ".js":
        return "application/javascript; charset=utf-8"
    if path.suffix == ".html":
        return "text/html; charset=utf-8"
    return "text/plain; charset=utf-8"


class ProjectHubHandler(BaseHTTPRequestHandler):
    server_version = "ProjectHub/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_get(parsed)
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        self.handle_api_post(parsed.path, payload)

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/tasks/status":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        ok = update_task_status(int(payload["task_id"]), payload["status"])
        if not ok:
            self.send_json({"error": "Task not found"}, status=HTTPStatus.NOT_FOUND)
            return
        self.send_json({"ok": True})

    def handle_api_get(self, parsed: Any) -> None:
        if parsed.path == "/api/bootstrap":
            self.send_json(
                {
                    "summary": fetch_summary(),
                    "projects": list_projects(),
                    "hardware": hardware_snapshot(),
                }
            )
            return
        if parsed.path == "/api/project":
            query = parse_qs(parsed.query)
            project_id = int(query["id"][0])
            details = get_project_details(project_id)
            if details is None:
                self.send_json({"error": "Project not found"}, status=HTTPStatus.NOT_FOUND)
                return
            self.send_json(details)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def handle_api_post(self, path: str, payload: dict[str, Any]) -> None:
        try:
            if path == "/api/projects":
                project = create_project(payload)
                self.send_json(project, status=HTTPStatus.CREATED)
                return
            if path in {"/api/tasks", "/api/logs", "/api/notes", "/api/links"}:
                project_id = int(payload["project_id"])
                table = path.replace("/api/", "")
                entry = add_entry(table, project_id, payload)
                self.send_json(entry, status=HTTPStatus.CREATED)
                return
        except sqlite3.IntegrityError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def serve_static(self, raw_path: str) -> None:
        relative = "index.html" if raw_path in {"", "/"} else raw_path.lstrip("/")
        path = (STATIC_DIR / relative).resolve()
        if not str(path).startswith(str(STATIC_DIR.resolve())) or not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", guess_content_type(path))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve(host: str, port: int) -> None:
    init_db()
    seed_if_empty()
    server = ThreadingHTTPServer((host, port), ProjectHubHandler)
    print(f"Project Hub running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")


def export_json() -> None:
    init_db()
    payload = {
        "summary": fetch_summary(),
        "projects": list_projects(),
        "hardware": hardware_snapshot(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Project Hub with SQLite and browser UI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create the local SQLite database")
    init_parser.set_defaults(func=lambda _args: init_db())

    seed_parser = subparsers.add_parser("seed", help="Add starter data if the database is empty")
    seed_parser.set_defaults(func=lambda _args: (init_db(), seed_if_empty()))

    serve_parser = subparsers.add_parser("serve", help="Run the local web app")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.set_defaults(func=lambda args: serve(args.host, args.port))

    export_parser = subparsers.add_parser("export", help="Print app data as JSON")
    export_parser.set_defaults(func=lambda _args: export_json())

    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = args.func(args)
    if result is not None:
        print(result)


if __name__ == "__main__":
    main()
