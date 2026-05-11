# API Contracts — MC (Mission Control)

> 작성: 2026-05-04 | Phase 4 Designer | v1.3 개정: 2026-05-04
> 범위: core-api (8000) · ai-worker (8001) · integrations (8002) · secret-bridge (9999)
> 인증: 없음 (loopback 전용). secret-bridge만 `X-Bridge-Key` 헤더 추가.
> v1.3 추가: Organizations, Businesses, Calendar, Labels, Projects(재정의) API

---

## 공통 규칙

### 에러 응답 형식 (전 서비스 공통)

```json
{
  "error": "ERROR_CODE",
  "message": "사용자 친화적 메시지"
}
```

| HTTP 코드 | 의미 | 공통 ERROR_CODE |
|----------|------|----------------|
| 400 | 입력 검증 실패 | `VALIDATION_ERROR` |
| 404 | 리소스 없음 | `NOT_FOUND` |
| 409 | 충돌 (일정 겹침 등) | `CONFLICT` |
| 422 | 상태 전이 불가 | `INVALID_TRANSITION` |
| 503 | 의존 서비스 불가 | `SERVICE_UNAVAILABLE` |
| 500 | 서버 오류 | `INTERNAL_ERROR` |

### 타임아웃 기준

| 구간 | 타임아웃 |
|------|---------|
| core-api → ai-worker (embed) | 500ms |
| core-api → ai-worker (STT) | 10s |
| core-api → secret-bridge | 1s |
| core-api → integrations | 3s |
| Browser → core-api (UI 부분 응답) | 2s |

### htmx 부분 응답

`Content-Type: text/html` 반환. JSON API와 구분을 위해 경로 패턴 구분:
- `/partial/*` — htmx fragment (text/html)
- `/api/*` — JSON CRUD
- `/infer/*`, `/notify/*`, `/github/*`, `/secret/*` — 각 서비스 내부 API

---

## 1. core-api (포트 8000)

### 1.1 htmx 부분 응답

#### `GET /partial/flow`

**FR**: FR-FLOW-01 | **NFR**: ≤1s 렌더

| 파라미터 | 위치 | 타입 | 필수 | 설명 |
|---------|------|------|------|------|
| date | query | `YYYY-MM-DD` | N | 기본값: 오늘 |

**응답** `200 text/html` — Today's Flow 아이템 목록 fragment

---

#### `GET /partial/context/{item_id}`

**FR**: FR-FLOW-03 | **NFR**: ≤500ms (3 DB 쿼리 병렬)

| 파라미터 | 위치 | 타입 | 필수 |
|---------|------|------|------|
| item_id | path | integer | Y |

**응답** `200 text/html` — 컨텍스트 패널 fragment (tags / memo / issues 섹션)
**오류** `404` — 해당 item_id 없음

---

#### `GET /partial/calendar`

**FR**: FR-FLOW-02

**응답** `200 text/html` — 캘린더 토글 뷰 fragment

---

#### `POST /partial/search`

**FR**: FR-AI-SEARCH | **NFR**: ≤200ms (FTS5) / ≤800ms (vec, ai-worker 포함)

| 파라미터 | 위치 | 타입 | 필수 |
|---------|------|------|------|
| q | form | string | Y |

**내부 로직**: 항목 수 <30 → FTS5; ≥30 → ai-worker `/infer/embed` → sqlite-vec
**응답** `200 text/html` — 검색 결과 fragment

---

### 1.2 Items CRUD

#### `POST /api/items`

**FR**: FR-CAP-01, FR-INT-TG-01

```json
{
  "title": "string (≤200자, 필수)",
  "type": "schedule|task|memo|project_ref (필수)",
  "source": "manual|telegram|voice|quick (기본 manual)",
  "tags": ["string"],
  "scheduled_at": "ISO8601 | null",
  "project_id": "integer | null"
}
```

**응답** `201`
```json
{"id": 42, "title": "...", "type": "task", "status": "todo", "created_at": "ISO8601"}
```

**오류**: `400 VALIDATION_ERROR` (title 누락), `409 CONFLICT` (일정 겹침, BR-CONFLICT-01)

충돌 시 응답:
```json
{
  "error": "CONFLICT",
  "message": "기존 일정과 겹칩니다",
  "conflicting_item_id": 7
}
```

---

#### `PATCH /api/items/{id}`

**FR**: FR-FLOW-01 (상태변경), FR-CAP-02 (인라인편집)

```json
{
  "status": "todo|doing|done|waiting|cancelled (선택)",
  "title": "string (선택)",
  "scheduled_at": "ISO8601 | null (선택)"
}
```

**오류**: `422 INVALID_TRANSITION` (상태 전이 불가, task_state.md 참조)

---

#### `DELETE /api/items/{id}`

**오류**: `404 NOT_FOUND`

---

#### `POST /api/items/{id}/tags`

**FR**: FR-CAP-02

```json
{"tag_name": "string (≤50자, 필수)"}
```

**응답** `200` `{"tag_id": 5, "tag_name": "work"}`

---

### 1.3 Projects

#### `POST /api/projects/from-tag`

**FR**: FR-PROJ-01

```json
{"tag_id": "integer (필수)", "name": "string (선택, 기본 tag명)"}
```

**응답** `201` `{"project_id": 3, "name": "...", "status": "active"}`

---

#### `POST /api/projects/{id}/repo`

**FR**: FR-GIT-02

```json
{"github_repo": "owner/repo (필수)"}
```

**오류**: `400 VALIDATION_ERROR` (형식 불일치)

---

### 1.4 Credentials

#### `POST /api/cred/gh`

**FR**: FR-GIT-01 → secret-bridge 위임

```json
{"pat": "string (필수)"}
```

내부: `POST http://127.0.0.1:9999/secret/MC_GH_PAT` 호출 (ADR-008: Docker 제거)
**응답** `200` `{"stored": true}`
**오류** `503 SERVICE_UNAVAILABLE` (secret-bridge 응답 없음)

---

### 1.5 Capture Inbox

#### `GET /inbox`

**FR**: FR-INBOX-01

**응답** `200 JSON`
```json
{
  "items": [
    {"id": 1, "source": "telegram", "raw_text": "...", "received_at": "ISO8601", "status": "pending"}
  ],
  "count": 12
}
```

---

#### `POST /inbox/{id}/accept`

**FR**: FR-INBOX-01

```json
{"title": "string (선택, 기본 raw_text 앞 100자)", "type": "task|memo|schedule", "tags": ["string"]}
```

**응답** `200` `{"item_id": 55}` (items 테이블에 생성된 ID)

---

#### `POST /inbox/{id}/reject`

**FR**: FR-INBOX-01

**응답** `200` `{"status": "rejected"}`

---

### 1.6 일일 사이클

#### `GET /morning`

**FR**: FR-DAY-03

**응답** `200 text/html` — Morning Preview 화면 (SC-07)

---

#### `POST /evening/start`

**FR**: FR-DAY-01

**응답** `200 text/html` — Evening Review 화면 (SC-07)

---

#### `POST /api/carry-over`

**FR**: FR-DAY-02

**응답** `200 JSON`
```json
{"carried_count": 3, "skipped_count": 1}
```

---

### 1.7 Diagnostics & Alerts

#### `GET /diag`

**FR**: FR-DIAG-01 | **NFR**: ≤1.5s

**응답** `200 JSON`
```json
{
  "services": {
    "ai_worker": {"status": "ok|degraded|down", "latency_ms": 45},
    "integrations": {"status": "ok|degraded|down", "latency_ms": 12},
    "secret_bridge": {"status": "ok|down", "latency_ms": 3}
  },
  "db": {"size_mb": 12.4, "wal_pages": 0},
  "inbox_pending": 2,
  "retry_queue_failed": 1
}
```

---

#### `GET /alerts`

**FR**: FR-NOTIFY-CTR-01

**응답** `200 JSON`
```json
{
  "alerts": [
    {"id": 9, "type": "schedule_reminder|integration_error|system", "message": "...", "status": "pending|dismissed", "created_at": "ISO8601"}
  ]
}
```

---

#### `POST /alerts/{id}/dismiss`

**FR**: FR-NOTIFY-CTR-01

**응답** `200` `{"status": "dismissed"}`

---

### 1.8 Organizations & Businesses (v1.3 신규)

#### `GET /api/hierarchy`

**FR**: FR-ORG-03

**응답** `200 JSON`
```json
{
  "organizations": [
    {
      "id": 1, "name": "플링크데이터", "logo_path": ".assets/logos/1.png", "color": "#6366f1",
      "businesses": [
        {
          "id": 1, "name": "플링크케어 사업",
          "projects": [
            {"id": 1, "title": "MC 개발", "status": "active", "progress": 0.68, "end_date": "2026-08-31"}
          ]
        }
      ]
    }
  ],
  "unaffiliated": {"item_count": 23}
}
```

---

#### `POST /api/organizations`

**FR**: FR-ORG-01

```json
{"name": "string (필수)", "color": "#hex (선택)", "logo_path": "string (선택)"}
```

**응답** `201` `{"id": 1, "name": "플링크데이터", "folder_created": true}`
**오류** `409` (이름 중복)

---

#### `PATCH /api/organizations/{id}`

```json
{"name": "string (선택)", "color": "#hex (선택)", "logo_path": "string (선택)"}
```

**응답** `200` `{"updated": true}`

---

#### `DELETE /api/organizations/{id}`

**오류** `409 CONFLICT` — 하위 businesses 존재 시 (BR-ORG-01)

---

#### `POST /api/businesses`

**FR**: FR-ORG-02

```json
{"org_id": "integer (선택, null=무소속)", "name": "string (필수)", "description": "string (선택)"}
```

**응답** `201` `{"id": 2, "name": "플링크케어 사업", "folder_created": true}`

---

#### `DELETE /api/businesses/{id}`

**오류** `409 CONFLICT` — 하위 projects 존재 시 (BR-BUS-02)

---

### 1.9 Projects (v1.3 재정의)

#### `POST /api/projects`

**FR**: FR-PROJ-01

```json
{
  "title": "string (필수)",
  "business_id": "integer | null",
  "start_date": "YYYY-MM-DD (선택)",
  "end_date": "YYYY-MM-DD (선택)",
  "github_repo": "owner/repo (선택)",
  "vision": "string (선택)"
}
```

**응답** `201`
```json
{"id": 3, "title": "MC 개발", "status": "planning", "folder_path": "플링크데이터/플링크케어-사업/MC-개발", "folder_created": true}
```

---

#### `POST /api/projects/{id}/stages`

**FR**: FR-PROJ-02

```json
{"name": "string (필수)", "order_idx": "integer (필수)", "start_date": "YYYY-MM-DD (선택)", "end_date": "YYYY-MM-DD (선택)"}
```

**응답** `201` `{"stage_id": 5, "folder_path": "...MC-개발/02_개발", "folder_created": true}`

---

#### `GET /api/projects/{id}`

**FR**: FR-PROJ-03

**응답** `200 JSON`
```json
{
  "id": 3, "title": "MC 개발", "status": "active", "progress": 0.68,
  "start_date": "2026-05-01", "end_date": "2026-08-31",
  "breadcrumb": {"org": "플링크데이터", "business": "플링크케어 사업"},
  "stages": [
    {"id": 1, "name": "01_기획", "status": "done", "order_idx": 1},
    {"id": 2, "name": "02_개발", "status": "active", "order_idx": 2},
    {"id": 3, "name": "03_검토", "status": "pending", "order_idx": 3}
  ],
  "current_stage_items": [...],
  "linked_files": [...],
  "github_issues": [...]
}
```

---

### 1.10 Calendar (v1.3 신규)

#### `GET /partial/calendar`

**FR**: FR-CAL-01 | **NFR**: ≤500ms

| 파라미터 | 위치 | 타입 | 필수 | 기본값 |
|---------|------|------|------|--------|
| mode | query | `day\|week\|month` | N | `week` |
| date | query | `YYYY-MM-DD` | N | 오늘 |
| org_id | query | integer | N | 전체 |
| project_id | query | integer | N | 전체 |
| label_id | query | integer | N | 전체 |

**응답** `200 text/html` — 캘린더 뷰 fragment

---

### 1.11 Labels (v1.3 신규)

#### `GET /api/labels`

**FR**: FR-LABEL-01

**응답** `200 JSON` `{"labels": [{"id": 1, "name": "확인 필요", "color": "#f59e0b", "type": "system"}]}`

---

#### `POST /api/items/{id}/labels`

**FR**: FR-LABEL-01

```json
{"label_id": "integer (필수)"}
```

**응답** `200` `{"attached": true}`

---

#### `DELETE /api/items/{id}/labels/{label_id}`

**응답** `200` `{"removed": true}`

---

#### `POST /api/labels`

커스텀 라벨 생성.

```json
{"name": "string (필수)", "color": "#hex (필수)"}
```

**응답** `201` `{"id": 10, "type": "custom"}`

---

### 1.12 Google Calendar 완료 표시 (v1.4 신규)

#### `POST /gcal/{gcal_event_id}/done`

**FR**: FR-INT-GCAL-02 | gcal_cache.mc_status = 'done' 로컬 저장. GCal에 쓰지 않음 (BR-GCAL-05).

**응답** `200 JSON`
```json
{"gcal_event_id": "abc123", "mc_status": "done"}
```

**오류** `404` — 이벤트 ID 없음

---

#### `DELETE /gcal/{gcal_event_id}/done`

**FR**: FR-INT-GCAL-02 (완료 취소) | mc_status → NULL 복원.

**응답** `200 JSON`
```json
{"gcal_event_id": "abc123", "mc_status": null}
```

---

### 1.13 미완료 사유 캡처 (v1.5 신규, FR-DAY-04)

#### `POST /api/items/{id}/incomplete-reason`

**FR**: FR-DAY-04 | 저녁 회고에서 미완료 항목별로 호출.

```json
{
  "review_date": "2026-05-06",
  "category": "external_block",
  "free_text": "고객 답변 대기",
  "decision": "carry_over"
}
```

**필수**: `review_date`, `category` (7종 enum), `decision` (4종 enum)
**옵션**: `free_text`

**응답** `201 JSON`
```json
{
  "id": 12,
  "item_id": 42,
  "category": "external_block",
  "decision": "carry_over",
  "applied": {"scheduled_at": "2026-05-07"}
}
```

**부작용**:
- `decision='carry_over'` → items.scheduled_at 내일로 갱신 (BR-DAY-06)
- `decision='cancel'` → items.status='cancelled' (BR-DAY-07)
- `decision='reschedule'` → 응답에 `requires_date` 표시, 후속 요청 필요

**오류** `422` — category 또는 decision enum 외 값 / `400` — review_date 미입력

---

#### `GET /api/insights/incomplete-reasons` (V1.1 예비)

**FR**: FR-INSIGHTS-01 (V1.1) | 카테고리·프로젝트별 빈도 시계열. V1.0은 데이터 적재만.

**Query**: `from`, `to`, `project_id` (선택), `group_by=category|project|day`

**응답** `200 JSON` — V1.1에서 정식 구현. V1.0 단계는 stub.

---

### 1.14 기타

#### `GET /api/export`

**FR**: FR-BACKUP-01

**응답** `200 application/json` — 전체 items/tags/projects/schedules/organizations/businesses JSON export

---

#### `POST /api/conflict/resolve`

**FR**: FR-CONFLICT-01

```json
{"file_path": "string", "resolution": "keep_local|keep_remote|merge"}
```

**응답** `200` `{"resolved": true}`

---

## 2. ai-worker (포트 8001)

로컬 호스트 프로세스. core-api 전용. 브라우저 직접 접근 없음.

### `POST /infer/embed`

**FR**: FR-AI-SEARCH, FR-AI-TAG | **NFR**: ≤200ms

```json
{"text": "string (필수)"}
```

**응답** `200`
```json
{"vector": [0.12, ...], "dim": 384, "ep": "NPU|CPU", "latency_ms": 87}
```

**오류** `503` (모델 미로드) → core-api는 FTS5 fallback

---

### `POST /infer/stt`

**FR**: FR-AI-VOICE | **NFR**: ≤3s (Whisper Base)

```
Content-Type: multipart/form-data
audio: WAV bytes (16kHz mono int16)
```

**응답** `200`
```json
{"transcript": "string", "confidence": 0.87, "latency_ms": 1240, "ep": "NPU|CPU"}
```

confidence < 0.6 → core-api가 capture_inbox에 `status='low_conf'`로 저장 (BR-AI-06)

---

### `POST /infer/slot` (V1.1)

**FR**: FR-AI-SLOT

```json
{"text": "string"}
```

**응답** `200`
```json
{"slots": {"title": "string|null", "date": "YYYY-MM-DD|null", "tags": ["string"], "project": "string|null"}}
```

---

### `GET /health`

**응답** `200`
```json
{"status": "ok", "ep": "NPU|CPU", "models_loaded": ["whisper", "bge", "vad"]}
```

---

## 3. integrations (포트 8002)

Docker 컨테이너. core-api 및 notifier-daemon 전용.

### `GET /github/issues/{repo}`

**FR**: FR-INT-GH-01 | repo 형식: `owner/repo`

**응답** `200 JSON`
```json
{
  "repo": "owner/repo",
  "issues": [
    {"number": 42, "title": "string", "state": "open", "cached_at": "ISO8601"}
  ],
  "rate_limit_remaining": 58
}
```

**오류** `503` (rate limit 초과, BR-GIT-04) → `{"error": "RATE_LIMITED", "retry_after": "ISO8601"}`

---

### `POST /github/issues`

**FR**: FR-INT-GH-02

```json
{"repo": "owner/repo", "title": "string", "body": "string (선택)"}
```

**응답** `201`
```json
{"issue_number": 43, "html_url": "https://github.com/..."}
```

---

### `GET /gcal/events`

**FR**: FR-INT-GCAL-01 | 캐시된 GCal 이벤트 조회 (core-api가 호출)

| Query | 기본값 | 설명 |
|-------|-------|------|
| `date` | 오늘 | `YYYY-MM-DD` |
| `range_days` | 7 | ±N일 범위 |

**응답** `200 JSON`
```json
{
  "events": [
    {
      "gcal_event_id": "abc123",
      "title": "팀 스탠드업",
      "start_at": "2026-05-04T10:00:00+09:00",
      "end_at": "2026-05-04T10:30:00+09:00",
      "mc_status": null,
      "visible": 1
    }
  ],
  "last_synced_at": "ISO8601"
}
```

**오류** `503` (OAuth 만료, BR-GCAL-02) → `{"error": "GCAL_AUTH_REQUIRED"}`

---

### `POST /gcal/sync`

**FR**: FR-INT-GCAL-01 | APScheduler가 30분마다 호출. core-api도 수동 트리거 가능.

**응답** `200 JSON`
```json
{"synced": 12, "new": 3, "deleted": 1, "errors": 0}
```

---

### `POST /notify/telegram`

**FR**: FR-INT-TG-02

```json
{"chat_id": 123456789, "message": "string (≤4096자)"}
```

**응답** `200` `{"sent": true, "message_id": 999}`
**오류** `503` → retry_queue에 자동 추가 (notifier-daemon 담당, BR-RETRY-01)

---

### `GET /health`

**응답** `200`
```json
{"status": "ok", "telegram_polling": true, "github_last_refresh": "ISO8601"}
```

---

## 4. secret-bridge (포트 9999)

Windows 호스트 프로세스. loopback(`127.0.0.1`) 및 `host.docker.internal`에서만 접근 허용.

### 인증

모든 요청에 `X-Bridge-Key: {BRIDGE_KEY}` 헤더 필요. BRIDGE_KEY는 서비스 시작 시 환경변수로 주입 (랜덤 UUID, `.env`에 저장 — 민감정보 아님).

허용 키 목록 (화이트리스트):
- `MC_GH_PAT`
- `MC_TG_BOT_TOKEN`
- `MC_GOOGLE_OAUTH`

---

### `GET /secret/{key}`

**ADR**: ADR-005

**응답** `200`
```json
{"key": "MC_GH_PAT", "value": "ghp_..."}
```

**오류**:
- `403 FORBIDDEN` — 허용되지 않은 key 또는 잘못된 X-Bridge-Key
- `404 NOT_FOUND` — keyring에 등록 안 됨

---

### `POST /secret/{key}`

```json
{"value": "string (필수)"}
```

**응답** `200` `{"stored": true}`
**오류** `403` (허용되지 않은 key)

---

### `DELETE /secret/{key}`

**응답** `200` `{"deleted": true}`

---

### `POST /secret/{key}/verify`

**FR**: FR-SET-CRED-01 | **NFR**: ≤3s (외부 API 검증)

실제 외부 API 호출로 토큰 유효성 확인.

| key | 검증 방법 |
|-----|---------|
| `MC_GH_PAT` | `GET https://api.github.com/user` |
| `MC_TG_BOT_TOKEN` | `GET https://api.telegram.org/bot{token}/getMe` |
| `MC_GOOGLE_OAUTH` | `GET https://oauth2.googleapis.com/tokeninfo` |

**응답** `200`
```json
{"valid": true, "identity": "github_username or telegram_botname"}
```
또는 `{"valid": false, "reason": "expired|invalid|network_error"}`

---

## 5. 서비스 간 통신 맵

```
Browser ──── HTTP ────► core-api :8000
                              │
                    ┌─────────┼─────────────────┐
                    │         │                 │
                    ▼         ▼                 ▼
             ai-worker    integrations    secret-bridge
               :8001         :8002           :9999
               (host)      (Docker)         (host)

notifier-daemon ──── SQLite read-only ──── (별도 프로세스, HTTP 없음)
                     notification_events, schedules
```

Docker 컨테이너(core-api, integrations)의 host 접근:
- ai-worker: `http://host.docker.internal:8001`
- secret-bridge: `http://host.docker.internal:9999`

---

## Change Log

| 버전 | 날짜 | 변경 내용 |
|------|------|---------|
| 1.0 | 2026-05-04 | 최초 작성. 4개 서비스 전체 계약 정의. |
