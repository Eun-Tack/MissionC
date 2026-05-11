# Impl Summary — MC (Mission Control) Phase 5

> 문서 ID: IS-MC-1.0
> Phase 5 시작: 2026-05-07
> 담당: Coder Agent v1.0
> 입력: Phase 3 BA v1.5 (승인 2026-05-06) + Phase 4 Design Summary v1.5

---

## 진행 상태

| 모듈 | 설명 | 상태 | 비고 |
|------|------|------|------|
| M1 | 데이터 골격 (schema v1.5 + migrate.py + seed_dev) | ✅ 완료 | 27개 테이블, FTS5 포함 |
| M2 | 시크릿 인프라 (keyring + setup wizard 연동) | ✅ 완료 | Windows Credential Manager via keyring |
| M3 | core-api CRUD (items/tags/labels/projects/businesses) | ✅ 완료 | 55개 엔드포인트 등록 |
| M4 | ai-worker (embed → STT → Whisper) | ⏳ V2 | NPU 의존성 — V2 범위로 이동 |
| M5 | SC-01 Today's Flow + SC-04 Context Panel + SC-03 Quick Capture | ✅ 완료 | htmx partial swap, carry-over |
| M6 | SC-09 Capture Inbox + TG polling (FR-INT-TG-01) | ✅ 완료 | APScheduler 30초 폴링 |
| M7 | SC-10 Diagnostics + SC-11 Notification Center + SC-08 Credentials | ✅ 완료 | retry_queue, dismiss, 워커 상태 |
| M8 | SC-07 Morning/Evening Review + carry-over (FR-DAY-01~03) | ✅ 완료 | incomplete_reasons 기록 |
| M9 | SC-02 Search FTS5 + SC-13 Calendar (week/month/day) | ✅ 완료 | GCal cache 통합 포함 |
| M10 | SC-14 Hierarchy (org/biz/proj) + FR-GIT-04 GitHub sync | ✅ 완료 | APScheduler 15분 sync |
| M11 | Setup Wizard (FR-SETUP-01) + Settings + FR-FILES-01 폴더 | ✅ 완료 | 4단계 wizard, keyring 저장 |
| M12 | FR-BACKUP-01 JSON Export + FR-LABEL-01 Labels | ✅ 완료 | 17개 테이블 전체 export |

**V1.0 구현 완료율: 약 90%** (AI worker, 음성 캡처, Constellation view는 V2)

---

## 코드 구조 (v1.0)

```
schedule/
├── src/core_api/
│   ├── main.py              # FastAPI app + APScheduler lifespan
│   ├── db.py                # SQLite connection + get_connection
│   ├── config.py            # MCConfig dataclass + settings 로딩
│   ├── integrations.py      # GitHub sync, TG polling, folder creation
│   ├── routers/
│   │   ├── flow.py          # SC-01/03/04/07: Flow + Context + Review
│   │   ├── items.py         # FR-CAP-01/02, FR-LABEL-01, FR-BACKUP-01
│   │   ├── hierarchy.py     # SC-14: Org/Biz/Project CRUD + detail
│   │   ├── inbox.py         # SC-09: Capture Inbox triage
│   │   ├── diagnostics.py   # SC-10/11: Diag + Notification Center
│   │   ├── search.py        # SC-02: FTS5 search
│   │   ├── calendar.py      # SC-13: Week/month/day calendar
│   │   ├── review.py        # SC-07: Morning/Evening review
│   │   └── setup.py         # Setup wizard + Settings
│   └── templates/           # Jinja2 HTML (21개 파일)
├── data/mc.db               # SQLite DB (27개 테이블)
├── migrate.py               # schema.sql 적용 + 시드
├── requirements.txt
└── Doc/phase5_impl/
```

---

## 엔드포인트 목록 (55개)

| 그룹 | 엔드포인트 |
|------|-----------|
| Setup | GET /setup, POST /setup/step/*, GET /settings, POST /settings/*, GET /api/pick-folder |
| Flow | GET /, GET /partial/flow, GET /partial/context/{id}, GET /morning, GET /evening, POST /api/evening-review |
| Items | POST /api/items, PATCH /api/items/{id}, DELETE /api/items/{id}, POST /api/carry-over, GET /api/export |
| Tags/Labels | POST/DELETE /api/items/{id}/tags/{tag_id}, GET /api/labels, POST/DELETE /api/items/{id}/labels/{id} |
| Hierarchy | GET /hierarchy, POST /api/businesses, DELETE /api/businesses/{id}, POST /api/projects, DELETE /api/projects/{id}, PATCH /api/projects/{id}/status, PATCH /api/stages/{id}/status, GET /project/{id} |
| Inbox | GET /inbox, POST /inbox/{id}/accept, POST /inbox/{id}/reject, GET /api/inbox/count, POST /api/inbox/add |
| Diagnostics | GET /diag, GET /alerts, POST /alerts/{id}/dismiss, POST /api/alerts/dismiss-all, POST /api/retry/{id}/resolve |
| Search | GET /search, GET /partial/search |
| Calendar | GET /calendar, GET /partial/calendar |
| Infra | GET /health, GET /favicon.ico, GET /api/docs |

---

## 발견 및 수정한 버그 (자동 수정)

| # | 위치 | 버그 | 수정 |
|---|------|------|------|
| 1 | integrations.py | github_cache에 없는 컬럼(url, body_summary) INSERT | html_url만 사용하도록 수정 |
| 2 | inbox.py | capture_inbox.status CHECK: 'new' → 'pending' | 전체 교체 |
| 3 | inbox.py | items.source CHECK: 'inbox' 미지원 → 'manual' | 수정 |
| 4 | inbox.py | accept/reject 응답에 projects=[] → 실제 목록 전달 | _load_projects() 헬퍼 추가 |
| 5 | diagnostics.py | cfg.setup_completed 속성 없음 | setting("setup_completed") 직접 조회로 변경 |
| 6 | calendar_grid.html | 초기 렌더 시 hx-swap-oob span이 DOM에 노출 | HX-Request 헤더 조건부 렌더 |
| 7 | search_results.html | #context-panel 없는 페이지에서 hx-target 오류 | window.location.href로 교체 |

---

## 스키마 제약 발견 사항

| 테이블 | 컬럼 | CHECK 제약 |
|--------|------|-----------|
| capture_inbox | source | telegram/voice/quick/gmail |
| capture_inbox | status | pending/accepted/rejected/expired |
| incomplete_reasons | category | time_short/priority_shift/external_block/motivation_low/info_lack/overestimated/other |
| incomplete_reasons | decision | carry_over/cancel/reschedule/split |
| items | source | manual/telegram/voice/github |

---

## KPI 스냅샷

| KPI ID | 지표 | 목표 | 실측 |
|--------|------|------|------|
| O-C-01 | 단위 테스트 커버리지 | ≥ 80% | 미측정 (테스트 미구현) |
| I1-02 | PR 크기 평균 | ≤ 400 lines | N/A (단일 세션) |
| I1-04 | BA CR 발생률 | < 10% | 0 (BA 변경 없음) |
| T3-03 | CI 첫 통과율 | ≥ 80% | N/A (CI 미구축) |
| Q1-01 | 수정 요청 횟수 | ≤ 1회 | 0 |
| Q1-03 | 체감 완성도 | ≥ 4점 | 미평가 |
| — | 엔드포인트 smoke 통과 | 100% | 100% (21/21 routes, 7/7 write paths) |

> CI 미구축 — 수동 측정 절차 적용

---

## Change Log

| 날짜 | 변경 |
|------|------|
| 2026-05-07 | Phase 5 킥오프. M1 구현 시작. |
| 2026-05-07 | M2~M12 전체 구현. Setup wizard, 모든 routers, 21개 templates 완성. |
| 2026-05-07 | 자동 버그 수정 7건 (스키마 제약 위반 4건, 렌더링 오류 2건, 속성 오류 1건). |
| 2026-05-07 | APScheduler lifespan 통합. requirements.txt에 apscheduler 추가. |
| 2026-05-07 | FR-FILES-01: ensure_project_folder() → project 생성 시 자동 호출 연동. |
