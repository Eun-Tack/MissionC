# BA-Tech Traceability Matrix (D1-02)

> 작성: 2026-04-28 | v1.3 개정: 2026-05-04
> 목적: FR → Screen → API → Table → Worker → Test 한 줄 추적
> v1.3 추가: FR-ORG-01~03, FR-CAL-01, FR-LABEL-01, FR-FILES-01~02, FR-PROJ-01~04 재정의

---

## V1.0 FR 추적 (전체 43개)

| FR ID | 화면 | API | Table | Worker | Test 영역 |
|-------|------|-----|-------|--------|----------|
| FR-FLOW-01 Today's Flow | SC-01 | `GET /partial/flow` | items, item_tags, schedules | core-api | unit + e2e ≤1s |
| FR-FLOW-02 Calendar 토글 | SC-13 | `GET /partial/calendar` | schedules, items | core-api | unit |
| FR-FLOW-03 Context Panel ⭐ | SC-04 | `GET /partial/context/{id}` | items, item_tags, github_cache, item_github_links, file_index | core-api | unit + perf ≤500ms |
| FR-CAP-01 Quick Capture | SC-01 (dock) | `POST /api/items` | items, capture_inbox (조건부) | core-api | unit + auto-classify |
| FR-CAP-02 인라인 태그 추가 | SC-01 | `POST /api/items/{id}/tags` | item_tags, tags | core-api | unit |
| FR-MEMO-01~05 .md 단일 원본 | SC-04 | `GET /api/memo/{path}` | items, file_index | core-api + watchdog | integration |
| FR-PROJ-01 프로젝트 등록·계층 | SC-14, SC-06 | `POST /api/projects` | projects, businesses, organizations | core-api | unit + folder creation |
| FR-PROJ-02 단계 관리 | SC-06 | `POST /api/projects/{id}/stages` | project_stages | core-api | unit + state machine |
| FR-PROJ-03 프로젝트 뷰 | SC-06 | `GET /api/projects/{id}` | projects, project_stages, items, item_projects, file_index, github_cache | core-api | integration |
| FR-PROJ-04 GitHub 연동 | SC-06, SC-14 | `POST /api/projects/{id}/repo` | projects, github_cache | integrations | integration |
| FR-GIT-01 PAT 등록 | SC-08-Cred | `POST /api/cred/gh` | settings | secret-bridge | integration |
| FR-GIT-02 repo 링크 | SC-06 | `POST /api/projects/{id}/repo` | projects | core-api | unit |
| FR-GIT-03 issue/PR 조회 | SC-04, SC-06 | `GET /github/issues/{repo}` | github_cache, item_github_links | integrations | integration + rate limit |
| FR-GIT-04 15분 자동 갱신 | (백그라운드) | (APScheduler) | github_cache | integrations | integration |
| FR-DAY-01 Evening Review | SC-07 | `POST /evening/start` | review_memos, items | core-api | e2e |
| FR-DAY-02 이월 | SC-07 | `POST /api/carry-over` | items, schedules | core-api | unit + state machine |
| FR-DAY-03 Morning Preview | SC-07 | `GET /morning` | items, schedules | core-api | e2e |
| FR-NOTIFY-01 5분 전 OS Toast | SC-11 | (notifier-daemon) | notification_events, schedules | notifier-daemon | integration |
| FR-CONFLICT-01 .md 충돌 | SC-12 | `POST /api/conflict/resolve` | file_index, items | core-api + watchdog | integration |
| FR-BACKUP-01 JSON Export | SC-08 | `GET /api/export` | (read all) | core-api | unit |
| FR-AI-VOICE STT | SC-01 + SC-09 | `POST /infer/stt` → `POST /api/items` | items, capture_inbox | ai-worker + core-api | integration NPU |
| FR-AI-SEARCH 의미 검색 | SC-02 | `POST /partial/search` → `POST /infer/embed` | items, item_vectors, items_fts | ai-worker + core-api | unit + perf ≤200ms |
| FR-AI-TAG 태그 제안 | SC-01, SC-09 | `POST /infer/embed` | tags, item_vectors | ai-worker + core-api | unit |
| FR-INT-TG-01 Bot polling | (백그라운드) → SC-09 | (python-telegram-bot) | capture_inbox | integrations | integration |
| FR-INT-TG-02 알림 발송 | SC-11 | `POST /notify/telegram` | retry_queue, notification_events | integrations | integration |
| FR-INT-GH-01 issue 조회 | SC-04, SC-06 | (FR-GIT-03 동일) | item_github_links | integrations | (위 동일) |
| FR-INT-GH-02 issue 생성 | SC-04 | `POST /github/issues` | github_cache, item_github_links | integrations | integration |
| FR-INBOX-01 Capture Inbox | SC-09 | `GET /inbox`, `POST /inbox/{id}/accept` | capture_inbox, items | core-api | unit + e2e |
| FR-DIAG-01 Diagnostics | SC-10 | `GET /diag` | settings, notification_events, retry_queue, file_index | core-api | unit |
| FR-NOTIFY-CTR-01 알림 센터 | SC-11 | `GET /alerts`, `POST /alerts/{id}/dismiss` | notification_events, retry_queue | core-api | unit |
| FR-SET-CRED-01 Credential UI | SC-08-Cred | `POST /api/cred/{key}/verify` | settings | secret-bridge | integration |
| **신규** FR-ORG-01 소속 등록 | SC-14 | `POST /api/organizations` | organizations | core-api | unit + folder |
| **신규** FR-ORG-02 사업 등록 | SC-14 | `POST /api/businesses` | businesses | core-api | unit + folder |
| **신규** FR-ORG-03 계층 뷰 | SC-14 | `GET /api/hierarchy` | organizations, businesses, projects | core-api | unit + e2e |
| **신규** FR-CAL-01 캘린더 뷰 | SC-13 | `GET /partial/calendar?mode=day/week/month` | items, schedules, item_projects, item_labels | core-api | unit + perf ≤500ms |
| **신규** FR-LABEL-01 라벨 시스템 | SC-01, SC-06, SC-13 | `POST /api/items/{id}/labels` | labels, item_labels | core-api | unit |
| **신규** FR-FILES-01 폴더 자동 생성 | (백그라운드) | (폴더 생성 내부 로직) | file_index, project_stages | core-api | unit + fs |
| **신규** FR-FILES-02 파일-단계 매핑 | SC-06 | (watchdog 내부) | file_index | core-api + watchdog | integration |
| **신규** FR-INT-GCAL-01 GCal 읽기·표시 | SC-01, SC-13 | `GET /gcal/events` | gcal_cache | integrations (APScheduler) | integration + OAuth |
| **신규** FR-INT-GCAL-02 GCal 완료 표시 | SC-01, SC-13 | `POST /gcal/{id}/done` | gcal_cache | core-api | unit |
| **신규 v1.5** FR-MEMO-06 Milkdown 에디터 | SC-04 | `GET/PUT /api/memo/{path}` | items, file_index | core-api | E2E + LocalDocsHub 호환 |
| **신규 v1.5** FR-MEMO-07 Lifecycle + Morphing | SC-04, SC-01 | `GET /api/memo/{id}/timeline` | file_index, items | core-api | unit + WAAPI |
| **신규 v1.5** FR-DAY-04 미완료 사유 캡처 | SC-07 | `POST /api/items/{id}/incomplete-reason` | incomplete_reasons, items | core-api | E2E + DB |
| **V1.5 Radial** FR-RADIAL-01 8 슬라이스 진입 | SC-RADIAL | (재사용 — 신규 0) | (DB 영향 0) | core-api (frontend only) | unit + e2e ≤100ms |
| **V1.5 Radial** FR-RADIAL-02 키보드 우선 | SC-RADIAL | (재사용) | (DB 영향 0) | core-api (frontend only) | a11y + e2e |
| **V1.5 Radial** FR-RADIAL-03 컨텍스트 인지 | SC-RADIAL | `POST /api/items` (project_id 자동) | items, item_projects | core-api | unit + URL pattern |
| **V1.5 Radial** FR-RADIAL-04 글래스 + Spring 모션 | SC-RADIAL | (frontend only) | — | core-api (frontend only) | visual + motion |
| **V1.5 Radial** FR-RADIAL-05 모든 페이지 작동 | SC-RADIAL (overlay on all) | (모든 V1.0 라우터에 영향) | (DB 영향 0) | core-api (frontend only) | regression smoke (V1.0 7 페이지) |

---

## V1.1 / V1.2 FR 추적 (참조용)

| FR ID | 버전 | 비고 |
|-------|------|------|
| FR-AI-SLOT 슬롯 추출 | V1.1 | `POST /infer/slot` (Phi-3) |
| FR-UX-04 Voice Glass UI | V1.1 | SC-05 — `/design` 스킬 활용 |
| FR-INT-GMAIL Gmail | V1.1 | integrations 모듈 추가 |
| FR-INT-DR-01~04 Drive Cold | V1.1 | Drive API 직접 연동 (ADR-010 참조) |
| FR-UX-01 Time Constellation | V1.2 | SC-03 Canvas 2D |

---

## 신규 FR 출처 (v1.3)

| 신규 FR | 출처 |
|---------|------|
| FR-ORG-01~02 | iet03 요청 — 소속·사업 계층 관리 |
| FR-ORG-03 | iet03 요청 — 소속-사업-프로젝트 계층 뷰 |
| FR-CAL-01 | iet03 요청 — 일/주/월 캘린더 뷰 |
| FR-LABEL-01 | iet03 요청 — 이슈·체크 라벨 시스템 |
| FR-FILES-01~02 | iet03 요청 — 로컬 폴더 계층 자동 생성 |
| FR-INT-GCAL-01~02 | iet03 요청 — Google Calendar 연동, 완료 표시 |
| FR-MEMO-06 | iet03 D1 — Milkdown 블록 에디터 (Notion 스타일) |
| FR-MEMO-07 | iet03 D6 — Memo Lifecycle 시각화 + Memo→Task Morphing |
| FR-DAY-04 | iet03 D4 — 저녁 회고 미완료 사유 카테고리 7종 + 결정 4종 데이터화 |

---

## 추적성 점수 산출 (D1-02)

| 항목 | 결과 |
|------|------|
| V1.0 FR 총수 | 43개 |
| 화면 매핑 완료 | 43 / 43 (100%) |
| API 매핑 완료 | 43 / 43 (100%) |
| Table 매핑 완료 | 43 / 43 (100%) |
| Worker 책임 명시 | 43 / 43 (100%) |
| Test 영역 명시 | 43 / 43 (100%) |
| **D1-02 점수** | **100%** |

---

## 변경 이력

| 날짜 | 변경 |
|------|------|
| 2026-04-28 | v1.0 최초 작성. 30 FR × 6열. |
| 2026-05-04 | v1.3: FR-ORG-01~03, FR-CAL-01, FR-LABEL-01, FR-FILES-01~02 추가. FR-PROJ-01~04 재정의. 총 38 FR. |
| 2026-05-04 | v1.4: FR-INT-GCAL-01~02 추가 (Google Calendar 연동). 총 40 FR. |
| 2026-05-06 | v1.5: FR-MEMO-06 (Milkdown), FR-MEMO-07 (Lifecycle/Morphing), FR-DAY-04 (미완료 사유) 추가. 총 43 FR. |
