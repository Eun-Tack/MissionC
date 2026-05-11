# ADR-004: 데이터 레이어

> 상태: Accepted | 결정일: 2026-04-27
> 결정자: iet03

---

## 컨텍스트

MC는 단일 SQLite 파일(`mc.db`) + .md 파일 시스템을 데이터 레이어로 사용한다. V1.0에서 항목 수는 수백~수천 규모. 시맨틱 검색(sqlite-vec), 전문 검색(FTS5), 실시간 파일 감지(watchdog)가 필요하다. Hot/Cold 티어는 V1.2.

---

## 결정

**SQLite 삼중 확장 전략**: 코어 SQLite + FTS5 + sqlite-vec를 단일 파일에서 운용.

```
mc.db
├── items              (핵심 엔티티)
├── tags               (태그 마스터)
├── item_tags          (N:M 매핑)
├── projects           (정식 프로젝트)
├── item_projects      (N:M 매핑)
├── schedules          (일정)
├── github_cache       (GitHub 이슈/PR 캐시)
├── tg_inbound         (Telegram 수신 큐)
├── settings           (키-값 설정)
│
├── items_fts          (FTS5 가상 테이블)
└── item_vectors       (sqlite-vec 벡터 테이블)
```

---

## ERD

```
items
  id          INTEGER PK
  type        TEXT  -- task|memo|note|event|project_ref
  title       TEXT  NOT NULL
  body        TEXT  -- .md 파일 경로 또는 인라인 텍스트
  body_inline BOOLEAN DEFAULT 0  -- 0: 파일 경로, 1: 인라인
  status      TEXT  -- todo|doing|done|waiting|cancelled
  location    TEXT  DEFAULT 'hot'  -- hot|cold
  scheduled_at DATETIME
  due_at      DATETIME
  created_at  DATETIME NOT NULL
  updated_at  DATETIME NOT NULL
  source      TEXT  -- manual|telegram|voice|github
  cold_path   TEXT  -- Drive 경로 (V1.2)

tags
  id          INTEGER PK
  name        TEXT  UNIQUE NOT NULL
  color_hue   INTEGER  -- 0~360, OKLCH hue

item_tags
  item_id     INTEGER FK items.id
  tag_id      INTEGER FK tags.id
  PRIMARY KEY (item_id, tag_id)

projects
  id          INTEGER PK
  tag_id      INTEGER FK tags.id  -- 프로젝트 ⊂ 태그 (BR-PROJ-02)
  title       TEXT
  status      TEXT  -- active|paused|completed|archived
  github_repo TEXT  -- owner/repo 형식
  vision      TEXT
  created_at  DATETIME

item_projects
  item_id     INTEGER FK items.id
  project_id  INTEGER FK projects.id
  PRIMARY KEY (item_id, project_id)

schedules
  id          INTEGER PK
  item_id     INTEGER FK items.id
  start_at    DATETIME NOT NULL
  end_at      DATETIME
  recurrence  TEXT  -- null | daily | weekly | cron-expr

github_cache
  id          INTEGER PK
  repo        TEXT  NOT NULL
  number      INTEGER NOT NULL
  type        TEXT  -- issue|pr
  title       TEXT
  state       TEXT
  labels      TEXT  -- JSON array
  html_url    TEXT
  fetched_at  DATETIME
  UNIQUE (repo, number, type)

tg_inbound
  id          INTEGER PK
  tg_message_id INTEGER
  text        TEXT
  processed   BOOLEAN DEFAULT 0
  received_at DATETIME

settings
  key         TEXT PK
  value       TEXT
  updated_at  DATETIME
```

---

## FTS5 & 벡터 테이블

```sql
-- FTS5 (전문 검색)
CREATE VIRTUAL TABLE items_fts USING fts5(
  title, body,
  content=items, content_rowid=id,
  tokenize='unicode61'
);

-- sqlite-vec (시맨틱 검색)
CREATE VIRTUAL TABLE item_vectors USING vec0(
  item_id INTEGER PRIMARY KEY,
  embedding FLOAT[384]  -- BGE-small-ko 출력 차원
);
```

**검색 라우팅 규칙** (BR-SEARCH-02):
```python
def search(query: str, item_count: int) -> list:
    if item_count < 30:
        return fts5_search(query)       # FTS5 전용
    embed = ai_worker.embed(query)
    return vec_search(embed, top_k=20)  # 시맨틱 우선
```

---

## 파일 시스템 연동

### 단일 원본 원칙 (BR-MEMO-01)

```
MC-Notes/
  2026/
    04/
      27-project-meeting.md    ← 원본 .md
      27-review.md             ← Evening Review (BR-DAY-01)
  archive/                     ← Cold 항목 이동 전 임시 (V1.2)
```

### watchdog 감지 → SQLite 동기화

```python
# watchdog 이벤트 → items.updated_at 갱신 + FTS5 재인덱스
class MCFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            item_id = db.lookup_by_path(event.src_path)
            if item_id:
                db.touch_updated_at(item_id)
                db.reindex_fts(item_id)
```

---

## 트랜잭션 & 동시성

- `core-api` Docker 컨테이너가 SQLite **단독 writer**
- `ai-worker`는 벡터 INSERT(`item_vectors`)만 별도 트랜잭션
- SQLite WAL 모드 활성화: `PRAGMA journal_mode=WAL`
- `core-api` ↔ `ai-worker` SQLite 경합 최소화: 임베딩 INSERT는 배치(5초마다 flush)

---

## 마이그레이션 전략

```
schema/
  v001_initial.sql
  v002_add_cold_tier.sql  (V1.2)
```

시작 시 버전 체크:
```python
def migrate(conn):
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for migration in sorted(MIGRATIONS):
        if migration.version > current:
            migration.apply(conn)
            conn.execute(f"PRAGMA user_version={migration.version}")
```

---

## 고려한 대안

| 옵션 | 이유로 제외 |
|------|-----------|
| PostgreSQL | 설치 복잡. 1인 로컬 도구에 과잉. |
| DuckDB | sqlite-vec 통합 불가. 분석 쿼리 없음. |
| 별도 벡터 DB (Chroma/Qdrant) | 추가 프로세스 필요. SQLite 단일 파일 원칙 위반. |
| Prisma ORM | JS 전용. Python 스택 부적합. |

---

## 결과

- 단일 `mc.db` 파일 — 백업/이동 단순
- FTS5 + sqlite-vec 동일 파일 — 검색 JOIN 쿼리 가능
- watchdog → SQLite 동기화 → 외부 에디터 편집 즉시 반영
- V1.2 Cold 티어: `items.location='cold'` + `items.cold_path` 컬럼 추가만으로 확장
