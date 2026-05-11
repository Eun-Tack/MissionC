# MC V1.0 Issue Tracker

> GitHub 미사용 → 로컬 이슈 트래커. KPI L1-03 (Postmortem 이슈 등록 100%) 충족 증빙.

**총 이슈**: 7건 (P0=2, P1=5) / **closed**: 7건 / **open**: 0건

---

## P0 — 배포 차단

### #B-001 · XSS in Search Snippet — **closed**
- **발견**: Phase 6 (2026-05-08)
- **위치**: `src/core_api/routers/search.py`, `templates/partials/search_results.html:12`
- **문제**: FTS5 `snippet()` 출력을 `| safe` 로 그대로 렌더 → 항목 제목에 HTML 주입 가능
- **수정**: `_safe_snippet()` 추가 — `html.escape()` 후 `<mark>` 태그만 복원
- **commit**: 2026-05-08

### #B-002 · XSS in Items f-string HTML — **closed**
- **발견**: Phase 6 (2026-05-08)
- **위치**: `src/core_api/routers/items.py:129`, `:255`
- **문제**: `POST /api/items`, `PATCH /api/items/{id}` 응답 f-string 에 `{title}` 비이스케이프 삽입
- **수정**: `from html import escape` → `escape(title.strip())` 적용
- **commit**: 2026-05-08

---

## P1 — V1.0 게이트 차단 (모두 2026-05-10 일괄 fix)

### #B-003 · Title Length Validation — **closed**
- **위치**: `items.py` POST/PATCH/subtask
- **문제**: 제목 길이 검증 없음 → 메모리 폭주 / DB row 크기 폭증 위험
- **수정**: `_TITLE_MAX = 10000` + `_check_title()` helper 도입, POST/PATCH/create_subtask 모두 적용
- **검증**: `POST /api/items` with 10001 char title → 422 OK

### #B-004 · 14-day Inbox Expiry — **closed**
- **위치**: `integrations.py`, `main.py`
- **문제**: capture_inbox 의 pending 행이 무한 누적 (BR-INBOX-02 위반)
- **수정**: `expire_stale_inbox(days=14)` 함수 추가 → APScheduler 6시간 간격 cron 등록
- **검증**: 함수 호출 시 정상 동작 ("expired 0 rows" — 현재 만료 대상 없음)

### #B-005 · Org Folder Auto-create — **closed**
- **위치**: `setup.py:settings_add_org`, `integrations.py`
- **문제**: org 생성 시 INSERT 만 하고 MC-Notes/{org}/ 폴더 미생성 (PRD 핵심 가치 위반)
- **수정**: `ensure_org_folder()` 추가 → `settings_add_org` 에서 `mc_notes_root` 설정 시 자동 호출
- **참고**: business 폴더 자동 생성은 이미 구현되어 있었음 (`add_business` 에서 `ensure_business_folder` 호출)

### #B-006 · Project Archive Cascade — **closed**
- **위치**: `hierarchy.py:archive_project`
- **문제**: `UPDATE projects SET status='archived'` 만 실행 → `item_projects` 행 잔존, flow/export 에 false positive
- **수정**: archive 후 `DELETE FROM item_projects WHERE project_id=?` 추가 (BR-PROJ-03)

### #B-007 · Export Content-Disposition — **closed**
- **위치**: `items.py:export_all`
- **문제**: JSON export 응답에 `Content-Disposition` 헤더 없음 → 브라우저에서 파일 다운로드 안 됨
- **수정**: `JSONResponse(headers=...)` 로 `attachment; filename="mc-export-YYYYMMDD-HHMMSS.json"` 추가
- **검증**: `GET /api/export` 응답 헤더 확인 OK

---

## V2 백로그 (이번 릴리즈 외)

> P0/P1 아님. V2 에서 처리 예정.

| ID | 영역 | 내용 |
|----|------|------|
| F-V2-01 | AI | FR-AI-SLOT (자유 텍스트 구조화 추출, Phi-3) |
| F-V2-02 | UX | FR-MEMO-06 Milkdown 블록 에디터 |
| F-V2-03 | UX | FR-MEMO-07 Memo Lifecycle 시각화 |
| F-V2-04 | Mobile | 모바일 캡처 모듈 (Telegram Bot 재활용) |
| F-V2-05 | DB | FR-INT-DR-* Google Drive Cold tier |
| Q-V2-01 | Quality | N+1 쿼리: `_load_biz_projects()` JOIN 통합 |
| Q-V2-02 | Quality | GitHub rate-limit header 체크 + diagnostics 알림 |
| Q-V2-03 | Quality | smoke test 자동화 (POST/PATCH/DELETE) |
| Q-V2-04 | UX | FR-DAY-04 미완료 사유 7종 + 결정 4종 |
