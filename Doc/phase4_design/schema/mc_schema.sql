-- MC (Mission Control) SQLite Schema v1.4
-- Updated: 2026-05-04
-- ADR-004, ADR-008, ADR-010 참조
-- v1.3 변경: organizations/businesses/project_stages/labels/item_labels 추가
--            projects 재정의 (태그 기반 → 계층 기반), file_index 확장
-- v1.4 변경: gcal_cache 추가 (FR-INT-GCAL-01~02)

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA user_version=4;

-- ─────────────────────────────────────────
-- 조직 계층 (FR-ORG-01~02, ADR-010)
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS organizations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    logo_path   TEXT,                              -- MC-Notes/.assets/logos/{id}.{ext} 상대 경로
    color       TEXT    NOT NULL DEFAULT '#6366f1', -- OKLCH/hex 브랜드 색상
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS organization_profiles (
    org_id                INTEGER PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    purpose               TEXT,
    operating_scope       TEXT,
    stakeholders          TEXT,
    role_title            TEXT,
    role_responsibilities TEXT,
    decision_rights       TEXT,
    role_kpis             TEXT,
    ai_guidance           TEXT,
    constraints           TEXT,
    updated_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS businesses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id      INTEGER REFERENCES organizations(id) ON DELETE RESTRICT,  -- BR-ORG-01
    name        TEXT    NOT NULL,
    description TEXT,
    folder_path TEXT,                                  -- v1.6: notes_root/{org}/{biz}/
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (org_id, name)
);

-- ─────────────────────────────────────────
-- Core entities
-- ─────────────────────────────────────────

-- item type 정합성 (v1.0):
--   'schedule' = 시간이 지정된 일정
--   'task'     = 할 일 (scheduled_at 선택)
--   'memo'     = 텍스트/파일 메모
--   'project_ref' = 프로젝트 메타가 items에 등장하는 특수 행
CREATE TABLE IF NOT EXISTS items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    type         TEXT    NOT NULL CHECK(type IN ('schedule','task','memo','project_ref')),
    title        TEXT    NOT NULL,
    body         TEXT,                              -- file path (body_inline=0) or inline text (body_inline=1)
    body_inline  INTEGER NOT NULL DEFAULT 0,
    status       TEXT    NOT NULL DEFAULT 'todo'
                         CHECK(status IN ('todo','doing','done','waiting','cancelled')),
    location     TEXT    NOT NULL DEFAULT 'hot'
                         CHECK(location IN ('hot','cold')),
    scheduled_at TEXT,                              -- ISO8601 (specific time)
    due_at       TEXT,                              -- ISO8601 (deadline timestamp)
    start_date   TEXT,                              -- v1.6: YYYY-MM-DD (mini-project start)
    due_date     TEXT,                              -- v1.6: YYYY-MM-DD (mini-project deadline)
    parent_id              INTEGER REFERENCES items(id) ON DELETE CASCADE,  -- v1.6: hierarchical sub-tasks
    folder_path            TEXT,                    -- v1.6: optional folder for mini-project tasks
    recurrence_rule        TEXT,                    -- v1.7: DAILY|WEEKDAYS|WEEKLY|MONTHLY
    recurrence_parent_id   INTEGER REFERENCES items(id),  -- v1.7: points to original recurring item
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    source       TEXT    NOT NULL DEFAULT 'manual'
                         CHECK(source IN ('manual','telegram','voice','github','recurrence')),
    cold_path    TEXT                               -- Google Drive path, V1.1
);
CREATE INDEX IF NOT EXISTS idx_items_parent ON items(parent_id);

CREATE TABLE IF NOT EXISTS tags (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    color_hue  INTEGER DEFAULT 265                  -- OKLCH hue 0~360
);

CREATE TABLE IF NOT EXISTS item_tags (
    item_id    INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    tag_id     INTEGER NOT NULL REFERENCES tags(id)  ON DELETE CASCADE,
    PRIMARY KEY (item_id, tag_id)
);

-- ─────────────────────────────────────────
-- 프로젝트 계층 (FR-PROJ-01~04, ADR-010)
-- v1.3: tag_id 기반 모델 폐기 → business_id 계층 모델
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS projects (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id  INTEGER REFERENCES businesses(id) ON DELETE SET NULL, -- NULL = 무소속
    title        TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'planning'
                         CHECK(status IN ('planning','active','review','done','paused','archived')),
    start_date   TEXT,                             -- YYYY-MM-DD
    end_date     TEXT,                             -- YYYY-MM-DD 마감일
    github_repo  TEXT,                             -- "owner/repo"
    vision       TEXT,
    folder_path  TEXT,                             -- MC-Notes 상대 경로 (ADR-010)
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS project_stages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,                  -- 예: "01_기획", "02_개발"
    order_idx   INTEGER NOT NULL DEFAULT 0,
    status      TEXT    NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','active','done')),
    start_date  TEXT,
    end_date    TEXT,
    folder_path TEXT,                              -- MC-Notes 상대 경로
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (project_id, order_idx)
);

CREATE TABLE IF NOT EXISTS item_projects (
    item_id    INTEGER NOT NULL REFERENCES items(id)    ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    stage_id   INTEGER REFERENCES project_stages(id)   ON DELETE SET NULL,
    PRIMARY KEY (item_id, project_id)
);

CREATE TABLE IF NOT EXISTS item_links (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    src_type   TEXT NOT NULL CHECK(src_type IN ('project','item','gh_issue','gh_pr','gcal_event','drive_file')),
    src_id     INTEGER NOT NULL,
    dst_type   TEXT NOT NULL CHECK(dst_type IN ('project','item','gh_issue','gh_pr','gcal_event','drive_file')),
    dst_id     INTEGER NOT NULL,
    relation   TEXT NOT NULL DEFAULT 'relates_to'
               CHECK(relation IN ('relates_to','blocks','depends_on','supports','duplicates','parent_child')),
    reason     TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(src_type, src_id, dst_type, dst_id, relation)
);
CREATE INDEX IF NOT EXISTS idx_item_links_src ON item_links(src_type, src_id);
CREATE INDEX IF NOT EXISTS idx_item_links_dst ON item_links(dst_type, dst_id);

CREATE TABLE IF NOT EXISTS integration_state (
    provider        TEXT PRIMARY KEY,
    status          TEXT NOT NULL DEFAULT 'unknown'
                    CHECK(status IN ('unknown','ok','not_configured','error')),
    last_success_at TEXT,
    last_error_at   TEXT,
    last_error      TEXT,
    last_run_at     TEXT,
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS schedules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    start_at    TEXT    NOT NULL,
    end_at      TEXT,
    recurrence  TEXT                                -- null | "daily" | "weekly" | cron-expr
);

-- ─────────────────────────────────────────
-- 라벨 시스템 (FR-LABEL-01)
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS labels (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT    NOT NULL UNIQUE,
    color TEXT    NOT NULL DEFAULT '#f59e0b',       -- hex
    type  TEXT    NOT NULL DEFAULT 'custom'
                  CHECK(type IN ('system','custom'))
);

CREATE TABLE IF NOT EXISTS item_labels (
    item_id  INTEGER NOT NULL REFERENCES items(id)  ON DELETE CASCADE,
    label_id INTEGER NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
    PRIMARY KEY (item_id, label_id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT,
    phone      TEXT,
    org        TEXT,
    notes      TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS item_contacts (
    item_id    INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    role       TEXT NOT NULL DEFAULT 'attendee',
    PRIMARY KEY (item_id, contact_id)
);

CREATE INDEX IF NOT EXISTS idx_item_contacts_item ON item_contacts(item_id);

-- ─────────────────────────────────────────
-- External integrations
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS github_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    repo        TEXT    NOT NULL,
    number      INTEGER NOT NULL,
    type        TEXT    NOT NULL CHECK(type IN ('issue','pr')),
    title       TEXT,
    state       TEXT,
    labels      TEXT,                               -- JSON array
    html_url    TEXT,
    fetched_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (repo, number, type)
);

-- Google Calendar 이벤트 캐시 (FR-INT-GCAL-01~02)
CREATE TABLE IF NOT EXISTS gcal_cache (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    gcal_event_id  TEXT    NOT NULL UNIQUE,            -- Google Calendar eventId (dedup 키)
    calendar_id    TEXT    NOT NULL DEFAULT 'primary',
    title          TEXT    NOT NULL,
    start_at       TEXT    NOT NULL,                   -- ISO8601
    end_at         TEXT,
    description    TEXT,
    location       TEXT,
    mc_item_id     INTEGER REFERENCES items(id),
    mc_kind        TEXT,
    mc_last_seen_status TEXT,
    mc_status      TEXT    CHECK(mc_status IN ('done', NULL)),  -- BR-GCAL-05: 로컬 완료 상태만
    visible        INTEGER NOT NULL DEFAULT 1,         -- BR-GCAL-04: GCal 삭제 시 0
    fetched_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_gcal_cache_start ON gcal_cache(start_at, visible);
CREATE INDEX IF NOT EXISTS idx_gcal_cache_mc_item ON gcal_cache(mc_item_id);

CREATE TABLE IF NOT EXISTS mobile_sync_actions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    provider       TEXT NOT NULL DEFAULT 'gcal',
    external_id    TEXT NOT NULL,
    item_id        INTEGER REFERENCES items(id) ON DELETE SET NULL,
    action         TEXT NOT NULL CHECK(action IN ('mark_done','mark_waiting','cancel','reschedule','note')),
    title          TEXT NOT NULL,
    old_value      TEXT,
    new_value      TEXT,
    payload        TEXT,
    status         TEXT NOT NULL DEFAULT 'pending'
                   CHECK(status IN ('pending','accepted','rejected')),
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    resolved_at    TEXT,
    UNIQUE(provider, external_id, action, new_value, status)
);

CREATE INDEX IF NOT EXISTS idx_mobile_sync_actions_status ON mobile_sync_actions(status, created_at);

-- Capture inbox — Telegram, voice, quick capture 통합 큐 (FR-INBOX-01)
CREATE TABLE IF NOT EXISTS capture_inbox (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source           TEXT    NOT NULL CHECK(source IN ('telegram','voice','quick','gmail')),
    raw_text         TEXT,
    raw_payload      TEXT,                          -- JSON
    suggested_type   TEXT    CHECK(suggested_type IN ('task','memo','schedule')),
    suggested_tags   TEXT,                          -- JSON array
    status           TEXT    NOT NULL DEFAULT 'pending'
                             CHECK(status IN ('pending','accepted','rejected','expired')),
    accepted_item_id INTEGER REFERENCES items(id) ON DELETE SET NULL,
    received_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    processed_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_capture_inbox_status ON capture_inbox(status, received_at);

-- item ↔ GitHub issue/PR 연결
CREATE TABLE IF NOT EXISTS item_github_links (
    item_id         INTEGER NOT NULL REFERENCES items(id)         ON DELETE CASCADE,
    github_cache_id INTEGER NOT NULL REFERENCES github_cache(id)  ON DELETE CASCADE,
    linked_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (item_id, github_cache_id)
);

-- 알림 발송 이력 (FR-NOTIFY-01, ADR-006)
CREATE TABLE IF NOT EXISTS notification_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id      INTEGER REFERENCES items(id) ON DELETE CASCADE,
    kind         TEXT    NOT NULL CHECK(kind IN ('lead','overdue','tg','retry_failed')),
    channel      TEXT    NOT NULL DEFAULT 'os_toast'
                         CHECK(channel IN ('os_toast','telegram','ui_banner')),
    sent_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    dismissed    INTEGER NOT NULL DEFAULT 0,
    dismissed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_notification_pending ON notification_events(item_id, kind, dismissed);

-- 외부 통합 실패 재시도 큐 (FR-NOTIFY-CTR-01)
CREATE TABLE IF NOT EXISTS retry_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target          TEXT    NOT NULL CHECK(target IN ('telegram','github','drive','gcal','backup')),
    operation       TEXT    NOT NULL,
    payload         TEXT    NOT NULL,               -- JSON
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_error      TEXT,
    next_attempt_at TEXT    NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    resolved        INTEGER NOT NULL DEFAULT 0,
    resolved_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_retry_pending ON retry_queue(resolved, next_attempt_at);

-- 미완료 사유 캡처 (FR-DAY-04, BR-DAY-04)
-- 저녁 회고 시 미완료 항목별로 카테고리·사유·결정을 누적. Reflection Insights(V1.1)의 데이터 소스.
CREATE TABLE IF NOT EXISTS incomplete_reasons (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id      INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    review_date  TEXT    NOT NULL,                   -- YYYY-MM-DD (저녁회고 날짜)
    category     TEXT    NOT NULL CHECK(category IN
                         ('time_short','priority_shift','external_block',
                          'motivation_low','info_lack','overestimated','other')),
    free_text    TEXT,                               -- 자유 메모 (선택)
    decision     TEXT    NOT NULL CHECK(decision IN
                         ('carry_over','cancel','reschedule','split')),
    recorded_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_incomplete_reasons_date     ON incomplete_reasons(review_date);
CREATE INDEX IF NOT EXISTS idx_incomplete_reasons_category ON incomplete_reasons(category, review_date);
CREATE INDEX IF NOT EXISTS idx_incomplete_reasons_item     ON incomplete_reasons(item_id);

-- 회고 메모 메타 (BR-DAY-01)
CREATE TABLE IF NOT EXISTS review_memos (
    review_date TEXT    PRIMARY KEY,               -- "YYYY-MM-DD"
    file_path   TEXT,
    status      TEXT    NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','completed','skipped')),
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- .md 파일 인덱스 (ADR-010 — project/stage 매핑 + v1.5 lifecycle 추가)
CREATE TABLE IF NOT EXISTS file_index (
    path             TEXT    PRIMARY KEY,           -- MC-Notes 상대 경로
    item_id          INTEGER REFERENCES items(id)       ON DELETE SET NULL,
    project_id       INTEGER REFERENCES projects(id)    ON DELETE SET NULL,
    stage_id         INTEGER REFERENCES project_stages(id) ON DELETE SET NULL,
    sha256           TEXT,
    mtime            TEXT,
    state            TEXT    NOT NULL DEFAULT 'present'
                             CHECK(state IN ('present','missing','cold')),
    evolution_count  INTEGER NOT NULL DEFAULT 0,    -- v1.5: FR-MEMO-07 sha256 변경 횟수
    last_morphed_to  TEXT    CHECK(last_morphed_to IN (NULL, 'task', 'project_ref')),  -- v1.5: morphing 추적
    last_seen_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- ─────────────────────────────────────────
-- Configuration
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- ─────────────────────────────────────────
-- Full-text search (FTS5)
-- ─────────────────────────────────────────

CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
    title,
    body,
    content=items,
    content_rowid=id,
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
    INSERT INTO items_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
END;
CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
    INSERT INTO items_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;

-- ─────────────────────────────────────────
-- Vector search (sqlite-vec)
-- 임베딩 모델: KoE5 384-dim (기본) / bge-m3 1024-dim (OQ-D-01 Phase 5 결정)
-- NPU/GPU 없으면 (ADR-009 CPU_ONLY) 비활성화 — 테이블 생성만 건너뜀
-- ─────────────────────────────────────────

-- CREATE VIRTUAL TABLE IF NOT EXISTS item_vectors USING vec0(
--     item_id INTEGER PRIMARY KEY,
--     embedding FLOAT[384]
-- );
-- Uncomment after: conn.load_extension("vec0") AND ai_capability_level != 'CPU_ONLY'

-- ─────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_items_status        ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_scheduled_at  ON items(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_items_updated_at    ON items(updated_at);
CREATE INDEX IF NOT EXISTS idx_items_location      ON items(location);
CREATE INDEX IF NOT EXISTS idx_github_cache_repo   ON github_cache(repo, fetched_at);
CREATE INDEX IF NOT EXISTS idx_schedules_start     ON schedules(start_at);
CREATE INDEX IF NOT EXISTS idx_projects_business   ON projects(business_id, status);
CREATE INDEX IF NOT EXISTS idx_businesses_org      ON businesses(org_id);
CREATE INDEX IF NOT EXISTS idx_stages_project      ON project_stages(project_id, order_idx);
CREATE INDEX IF NOT EXISTS idx_file_project        ON file_index(project_id, stage_id);

-- ─────────────────────────────────────────
-- Seed: default settings
-- ─────────────────────────────────────────

INSERT OR IGNORE INTO settings(key, value) VALUES
    ('github_cache_interval_min',      '15'),
    ('notify_lead_min',                '5'),
    ('whisper_confidence_threshold',   '0.6'),
    ('semantic_search_min_items',      '30'),
    ('keyring_target_gh_pat',          'MC_GH_PAT'),
    ('keyring_target_tg_bot',          'MC_TG_BOT_TOKEN'),
    ('keyring_target_gcal_token',      'MC_GCAL_TOKEN'),
    ('secret_bridge_url',              'http://127.0.0.1:9999'),
    ('embedding_model',                'KoE5'),
    ('embedding_dim',                  '384'),
    ('ai_capability_level',            'unknown'),   -- ADR-009: NPU|GPU_DML|GPU_CUDA|CPU_ONLY
    ('mc_notes_root',                  ''),          -- ADR-010: 빈 값 = ~/Documents/MC-Notes
    ('gdrive_enabled',                 'false'),     -- ADR-010: V1.0 Drive for Desktop 안내용
    ('worker_status_ai_worker',        'unknown'),
    ('worker_status_notifier',         'unknown'),
    ('worker_status_tg_polling',       'unknown'),
    ('worker_status_gh_sync',          'unknown'),
    ('worker_status_watchdog',         'unknown'),
    ('gcal_poll_interval_min',         '30'),          -- FR-INT-GCAL-01: 30분 폴링 주기
    ('gcal_sync_days_range',           '7'),           -- 현재 ±7일 이벤트 조회
    ('tag_normalize_threshold',        '0.85'),        -- v1.5: 태그 자동 정규화 임계값 (FR-AI-TAG)
    ('memo_inbox_default_path',        'inbox'),       -- v1.5: 신규 메모 기본 폴더 (FR-MEMO-01)
    ('memo_editor',                    'milkdown');     -- v1.5: 블록형 노션 스타일 에디터 (FR-MEMO-06)

-- Seed: 시스템 라벨 (FR-LABEL-01)
INSERT OR IGNORE INTO labels(name, color, type) VALUES
    ('확인 필요',  '#f59e0b', 'system'),
    ('검토중',     '#3b82f6', 'system'),
    ('블로킹',     '#ef4444', 'system'),
    ('중요',       '#f97316', 'system'),
    ('완료 대기',  '#6b7280', 'system');
