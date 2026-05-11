"""
Dev seed — populates data/mc.db with realistic sample data for local development.

Usage:  python -m src.tools.seed_dev
        python -m src.tools.seed_dev --reset   (wipe + re-seed)
"""

from __future__ import annotations
import argparse
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DB_PATH = ROOT / "data" / "mc.db"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _today(offset_days: int = 0, hour: int = 0, minute: int = 0) -> str:
    d = date.today() + timedelta(days=offset_days)
    return f"{d.isoformat()}T{hour:02d}:{minute:02d}:00+09:00"


def seed(conn: sqlite3.Connection) -> None:
    today = date.today().isoformat()

    # ── Organizations ──────────────────────────────────────────────
    conn.execute("""
        INSERT OR IGNORE INTO organizations(name, color) VALUES
        ('플링크데이터',     'oklch(58% 0.18 280)'),
        ('한국보훈진흥원',   'oklch(55% 0.20 145)'),
        ('개인',             'oklch(60% 0.15 200)')
    """)

    def org_id(name: str) -> int:
        return conn.execute("SELECT id FROM organizations WHERE name=?", (name,)).fetchone()[0]

    # ── Businesses ─────────────────────────────────────────────────
    conn.execute("""
        INSERT OR IGNORE INTO businesses(org_id, name, description) VALUES
        (?, '플링크케어', '케어 서비스 사업부'),
        (?, 'ODC', 'Open Data Center 개발')
    """, (org_id('플링크데이터'), org_id('플링크데이터')))

    conn.execute("""
        INSERT OR IGNORE INTO businesses(org_id, name, description) VALUES
        (?, 'Q2 보훈서비스', '2026 Q2 보훈 서비스 운영')
    """, (org_id('한국보훈진흥원'),))

    def biz_id(name: str) -> int:
        return conn.execute("SELECT id FROM businesses WHERE name=?", (name,)).fetchone()[0]

    # ── Projects ───────────────────────────────────────────────────
    conn.executemany("""
        INSERT OR IGNORE INTO projects(business_id, title, status, start_date, end_date, github_repo, vision)
        VALUES (?,?,?,?,?,?,?)
    """, [
        (biz_id('플링크케어'), 'MC 개발',        'active',   '2026-04-26', '2026-07-31', 'iet03/mc', 'AI 기반 1인 운영 도구'),
        (biz_id('플링크케어'), 'API 연동 v2',    'planning', '2026-06-01', '2026-08-31', None,       None),
        (biz_id('ODC'),        'ODC 백엔드',     'active',   '2026-03-01', '2026-06-30', None,       None),
        (biz_id('Q2 보훈서비스'), 'Q2 리뷰 대시보드', 'active', '2026-04-01', '2026-06-30', 'iet03/q2-dashboard', None),
        (None,                 '개인 학습',      'active',   '2026-01-01', None,         None,       'AI/NPU 역량 강화'),
    ])

    def proj_id(title: str) -> int:
        return conn.execute("SELECT id FROM projects WHERE title=?", (title,)).fetchone()[0]

    # ── Project Stages ─────────────────────────────────────────────
    conn.executemany("""
        INSERT OR IGNORE INTO project_stages(project_id, name, order_idx, status, start_date, end_date)
        VALUES (?,?,?,?,?,?)
    """, [
        (proj_id('MC 개발'), '01_기획/BA',  0, 'done',   '2026-04-26', '2026-05-06'),
        (proj_id('MC 개발'), '02_설계',     1, 'done',   '2026-04-27', '2026-05-06'),
        (proj_id('MC 개발'), '03_구현',     2, 'active', '2026-05-07', '2026-06-30'),
        (proj_id('MC 개발'), '04_검토',     3, 'pending','2026-07-01', '2026-07-15'),
        (proj_id('MC 개발'), '05_배포',     4, 'pending','2026-07-16', '2026-07-31'),
        (proj_id('Q2 리뷰 대시보드'), '01_요구사항',  0, 'done',   '2026-04-01', '2026-04-15'),
        (proj_id('Q2 리뷰 대시보드'), '02_개발',      1, 'active', '2026-04-16', '2026-06-15'),
        (proj_id('Q2 리뷰 대시보드'), '03_검수',      2, 'pending','2026-06-16', '2026-06-30'),
    ])

    # ── Tags ───────────────────────────────────────────────────────
    conn.executemany("INSERT OR IGNORE INTO tags(name, color_hue) VALUES (?,?)", [
        ('회의',     265), ('NPU',      200), ('아이디어',  145),
        ('mc-dev',   280), ('보훈',     145), ('AI',       200),
        ('리뷰',     50),  ('긴급',     25),  ('학습',     80),
    ])

    def tag_id(name: str) -> int:
        return conn.execute("SELECT id FROM tags WHERE name=?", (name,)).fetchone()[0]

    # ── Items (today's schedule) ───────────────────────────────────
    items = [
        # (type, title, body, status, source, scheduled_at)
        ('schedule', '팀 스탠드업',           None, 'done',  'manual', _today(hour=9)),
        ('schedule', '투자자 미팅',            None, 'doing', 'manual', _today(hour=10)),
        ('task',     'PR #42 리뷰',            None, 'todo',  'manual', _today(hour=11)),
        ('memo',     '아키텍처 결정 노트',     'Doc/phase4_design/Design_Summary.md', 'todo', 'manual', _today(hour=14)),
        ('schedule', '설계 리뷰',              None, 'todo',  'manual', _today(hour=15, minute=30)),
        ('schedule', '1on1 — 김OO',           None, 'todo',  'manual', _today(hour=17)),
        ('task',     'GitHub 이슈 #38 확인',  None, 'todo',  'manual', None),
        ('task',     'V1.1 아이디어 정리',    None, 'todo',  'manual', None),
        ('task',     'requirements.txt 정리', None, 'todo',  'manual', None),
    ]

    for type_, title, body, status, source, sched in items:
        body_inline = 0 if (body and body.startswith('Doc/')) else (1 if body else 0)
        conn.execute("""
            INSERT OR IGNORE INTO items(type, title, body, body_inline, status, location, scheduled_at, source, created_at, updated_at)
            SELECT ?,?,?,?,?,'hot',?,?,?,?
            WHERE NOT EXISTS (SELECT 1 FROM items WHERE title=? AND date(created_at)=?)
        """, (type_, title, body, body_inline, status, sched, source, _now(), _now(), title, today))

    def item_id(title: str) -> int | None:
        row = conn.execute("SELECT id FROM items WHERE title=?", (title,)).fetchone()
        return row[0] if row else None

    # ── Schedules ──────────────────────────────────────────────────
    schedule_map = {
        '팀 스탠드업':  (9, 0,  9, 30),
        '투자자 미팅':  (10, 0, 11, 0),
        '설계 리뷰':    (15, 30, 16, 30),
        '1on1 — 김OO': (17, 0, 17, 30),
    }
    for title, (sh, sm, eh, em) in schedule_map.items():
        iid = item_id(title)
        if iid:
            conn.execute("""
                INSERT OR IGNORE INTO schedules(item_id, start_at, end_at)
                SELECT ?,?,?
                WHERE NOT EXISTS (SELECT 1 FROM schedules WHERE item_id=?)
            """, (iid, _today(hour=sh, minute=sm), _today(hour=eh, minute=em), iid))

    # ── item ↔ tags ────────────────────────────────────────────────
    tag_links = {
        '팀 스탠드업':           ['회의'],
        '투자자 미팅':           ['보훈'],
        'PR #42 리뷰':           ['NPU', 'mc-dev'],
        '아키텍처 결정 노트':    ['아이디어', 'mc-dev'],
        '설계 리뷰':             ['mc-dev'],
        'GitHub 이슈 #38 확인': ['mc-dev'],
        'V1.1 아이디어 정리':    ['아이디어', 'AI'],
    }
    for title, tags in tag_links.items():
        iid = item_id(title)
        if not iid:
            continue
        for tname in tags:
            tid = tag_id(tname)
            conn.execute("INSERT OR IGNORE INTO item_tags(item_id, tag_id) VALUES (?,?)", (iid, tid))

    # ── item ↔ labels ──────────────────────────────────────────────
    label_links = {
        '투자자 미팅':        '중요',
        'PR #42 리뷰':        '블로킹',
        '설계 리뷰':          '검토중',
        'V1.1 아이디어 정리': '확인 필요',
    }
    for title, lname in label_links.items():
        iid = item_id(title)
        if not iid:
            continue
        row = conn.execute("SELECT id FROM labels WHERE name=?", (lname,)).fetchone()
        if row:
            conn.execute("INSERT OR IGNORE INTO item_labels(item_id, label_id) VALUES (?,?)", (iid, row[0]))

    # ── item ↔ projects ────────────────────────────────────────────
    proj_links = {
        '투자자 미팅':           'Q2 리뷰 대시보드',
        'PR #42 리뷰':           'MC 개발',
        '아키텍처 결정 노트':    'MC 개발',
        '설계 리뷰':             'MC 개발',
        'GitHub 이슈 #38 확인': 'MC 개발',
    }
    for title, pname in proj_links.items():
        iid = item_id(title)
        pid = proj_id(pname)
        if iid and pid:
            conn.execute(
                "INSERT OR IGNORE INTO item_projects(item_id, project_id) VALUES (?,?)",
                (iid, pid),
            )

    # ── file_index (memo lifecycle) ────────────────────────────────
    memo_id = item_id('아키텍처 결정 노트')
    if memo_id:
        conn.execute("""
            INSERT OR REPLACE INTO file_index(path, item_id, project_id, evolution_count, last_seen_at)
            VALUES (?,?,?,?,?)
        """, ('MC 개발/03_구현/architecture_decisions.md', memo_id, proj_id('MC 개발'), 5, _now()))

    # ── github_cache ───────────────────────────────────────────────
    conn.executemany("""
        INSERT OR IGNORE INTO github_cache(repo, number, type, title, state, html_url)
        VALUES (?,?,?,?,?,?)
    """, [
        ('iet03/mc', 42, 'issue', 'Q2 리뷰 자료 준비',   'open',   'https://github.com/iet03/mc/issues/42'),
        ('iet03/mc', 39, 'pr',    '대시보드 PR',          'closed', 'https://github.com/iet03/mc/pull/39'),
        ('iet03/mc', 38, 'issue', 'sqlite-vec 연동 테스트', 'open',  'https://github.com/iet03/mc/issues/38'),
    ])

    # ── link items → github issues ─────────────────────────────────
    pr42_row = conn.execute(
        "SELECT id FROM github_cache WHERE repo='iet03/mc' AND number=42"
    ).fetchone()
    investor_id = item_id('투자자 미팅')
    if pr42_row and investor_id:
        conn.execute(
            "INSERT OR IGNORE INTO item_github_links(item_id, github_cache_id) VALUES (?,?)",
            (investor_id, pr42_row[0]),
        )
    pr38_row = conn.execute(
        "SELECT id FROM github_cache WHERE repo='iet03/mc' AND number=38"
    ).fetchone()
    gh_issue_id = item_id('GitHub 이슈 #38 확인')
    if pr38_row and gh_issue_id:
        conn.execute(
            "INSERT OR IGNORE INTO item_github_links(item_id, github_cache_id) VALUES (?,?)",
            (gh_issue_id, pr38_row[0]),
        )

    conn.commit()
    print(f"[SEED] Done - organizations: 3, projects: 5, items: {len(items)}, tags: 9")


def reset(conn: sqlite3.Connection) -> None:
    tables = [
        'item_github_links', 'item_projects', 'item_labels', 'item_tags',
        'file_index', 'github_cache', 'schedules', 'items',
        'project_stages', 'projects', 'businesses', 'organizations', 'tags',
    ]
    for t in tables:
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    print("[SEED] Reset complete.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true', help='Wipe data then re-seed')
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"[ERROR] DB not found: {DB_PATH}\nRun: python migrate.py first", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    if args.reset:
        reset(conn)

    seed(conn)
    conn.close()


if __name__ == '__main__':
    main()
