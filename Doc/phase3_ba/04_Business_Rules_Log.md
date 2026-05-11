# Business Rules Log — MC

> 단일 진실 원천. 원본: [03_Business_Rules](../phase1_interview/03_Business_Rules.md)
> 작성: 2026-04-27 | BA Writer v1.0
> 상태: Draft

---

## §1 인증 / 권한

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 |
|-------|---------|-----------|------|---------|------|
| BR-AUTH-01 | 사용자가 MC 실행 | 자동 진입. 인증 없음 (단일 사용자). | `[iet03]` | Must | 확인됨 |
| BR-AUTH-02 | GitHub PAT 등록 시 | Windows Credential Manager(DPAPI)에 저장. 평문 파일 저장 금지. | `[iet03]` | Must | 확인됨 |
| BR-AUTH-03a | AI 추론 요청 발생 시 | 외부 SaaS AI API 송신 금지. 모든 AI 추론은 로컬 NPU/iGPU 전용. | `[iet03]` | Must | 확인됨 |
| BR-AUTH-03b | Google Drive 백업 설정 시 (V1.2) | 초기 설정에서 동의 화면 필수. 동의 후 사용자 자신의 Drive에만 송신 허용. | `[iet03]` | Must | 확인됨 |

---

## §2 데이터 유효성

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 | 관련 FR |
|-------|---------|-----------|------|---------|------|--------|
| BR-VAL-01 | Quick Capture 텍스트 입력 | 1자 이상, 10,000자 이하. 초과 시 "너무 긴 입력입니다. 메모로 전환하시겠어요?" | `[추론]` | Must | 검토중 | FR-CAP-01 |
| BR-VAL-02 | 태그명 입력 | 1~50자. 공백·`/\?<>` 거부. 대소문자 무시 unique. | `[추론]` | Must | 검토중 | FR-PROJ-01 |
| BR-VAL-03 | 일정 시간이 현재보다 과거 | 경고 표시("이미 지난 시간입니다") + 등록은 허용. | `[추론]` | Should | 검토중 | FR-CAP-01 |
| BR-VAL-04 | 정식 프로젝트 메타 필드 | 빈 값 허용. 디폴트: priority=P2, status=active, progress=0. | `[추론]` | Must | 검토중 | FR-PROJ-02 |
| BR-VAL-05 | .md 파일 본문 1MB 초과 | "파일이 큽니다. 분할을 권장합니다." 알림. 강제 차단 X. | `[추론]` | Should | 검토중 | FR-MEMO-01 |
| BR-VAL-06 | GitHub repo URL 입력 | `https://github.com/owner/repo` 패턴 검증. 불일치 시 인라인 오류. | `[추론]` | Must | 검토중 | FR-GIT-02 |

---

## §3 상태 전이

### 태스크

| BR ID | 현재 상태 | 이벤트 (IF) | 다음 상태 (THEN) | 부수 효과 | 출처 | 우선순위 |
|-------|---------|-----------|----------------|---------|------|---------|
| BR-STATE-01 | `todo` | 시작 클릭 | `doing` | `started_at` 기록 | `[추론]` | Should |
| BR-STATE-02 | `doing` | 완료 클릭 | `done` | `completed_at` 기록 + 뷰 갱신 | `[추론]` | Must |
| BR-STATE-03 | `todo`/`doing` | 보류 클릭 | `waiting` | 사유 메모 입력 가능 | `[추론]` | Should |
| BR-STATE-04 | `waiting` | 재시작 클릭 | `doing` | — | `[추론]` | Should |
| BR-STATE-05 | 모든 상태 | 취소 | `cancelled` | hidden 보존, 통계 제외 | `[추론]` | Should |
| BR-STATE-06 | 미완료 | 저녁 회고 "내일로" | 다음 날로 이동 (원본 ID 보존, 날짜만 변경) | — | `[iet03]` | Must |

### 정식 프로젝트

| BR ID | 현재 상태 | 이벤트 (IF) | 다음 상태 (THEN) | 출처 | 우선순위 |
|-------|---------|-----------|----------------|------|---------|
| BR-STATE-07 | `idea` | 활성화 | `active` | `[추론]` | Should |
| BR-STATE-08 | `active` | 보관 | `archived` | `[추론]` | Should |
| BR-STATE-09 | `archived` | 재활성화 | `active` (메타 복원) | `[추론]` | Should |
| BR-STATE-10 | 정식 프로젝트 | 일반 태그로 강등 | `tag` (메타 hidden 보존) | `[iet03]` | Must |

---

## §4 Quick Capture

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 |
|-------|---------|-----------|------|---------|------|
| BR-CAP-01 | 자유 텍스트 자동 분류 결과 도출 | 미리보기 표시 후 사용자 확인(Enter/클릭) 후 등록. 자동 등록 금지. | `[추론]` | Must | 검토중 |
| BR-CAP-02 | 텍스트에 시간 패턴(`14:00`, `오전 10시`, `내일 3시`) 포함 | 타입을 **일정**으로 분류 제안 | `[추론]` | Must | 검토중 |
| BR-CAP-03 | 텍스트에 `[ ]`, `- todo`, `- TODO` 패턴 포함 | 타입을 **태스크**로 분류 제안 | `[추론]` | Must | 검토중 |
| BR-CAP-04 | 위 패턴 없음 | 타입을 **메모**로 분류 제안 | `[추론]` | Must | 검토중 |
| BR-CAP-05 | 텍스트에 `#태그명` 포함 | 해당 태그 자동 추가. 신규 태그면 생성 후 사용자 확인 | `[추론]` | Should | 검토중 |
| BR-CAP-06 | 빈 입력 / 공백만 | 거부. "내용을 입력하세요" | `[추론]` | Must | 검토중 |
| BR-CAP-07 | 동일 텍스트 5초 내 연속 입력 | 중복 의심 알림 + 사용자 확인 후 처리 | `[추론]` | Should | 검토중 |

---

## §5 흐름·뷰

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 |
|-------|---------|-----------|------|---------|------|
| BR-FLOW-01 | 항목에 시간 미지정 | "Anytime" 묶음에 표시 | `[추론]` | Must | 검토중 |
| BR-FLOW-02 | 컨텍스트 패널 열린 상태에서 다른 항목 클릭 | 새 항목으로 패널 갱신 (한 번에 1개) | `[추론]` | Must | 검토중 |
| BR-FLOW-03 | 뷰 전환 (흐름↔캘린더↔Constellation) | 같은 데이터, 서버 호출 없이 클라이언트 전환 | `[추론]` | Should | 검토중 |
| BR-FLOW-04 | 렌더 항목 100개 이상 | 가상 스크롤 적용 | `[추론]` | Should | 검토중 |

---

## §6 메모 / .md

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 |
|-------|---------|-----------|------|---------|------|
| BR-MEMO-01 | 항목 생성 시 .md 원본 | .md 파일 1개만 생성. 다중 태그·프로젝트 매핑은 SQLite 메타만. 파일 복제 X. | `[iet03]` | Must | 확인됨 |
| BR-MEMO-02 | 외부 도구가 .md 편집 | 감지 → 1.5초 디바운스 → 인덱스 갱신. MC가 외부 변경 결과를 덮어쓰지 않음. | `[추론]` | Must | 검토중 |
| BR-MEMO-03 | 메모 입력 시점이 자정 이전 | 당일 `MC-Notes/YYYY/MM/DD.md`에 추가 | `[추론]` | Must | 검토중 |
| BR-MEMO-04 | 메모 입력 시점이 자정 이후 | 다음 날 파일에 추가 | `[추론]` | Must | 검토중 |
| BR-MEMO-05 | 자유 명명 메모 동일 파일명 충돌 | `_1`, `_2` 자동 접미사 | `[추론]` | Should | 검토중 |
| BR-MEMO-06 | .md 파일 외부 삭제 감지 | 인덱스 "결손" 마킹. 사용자 확인 후 인덱스 삭제 또는 복구. | `[추론]` | Must | 검토중 |
| BR-MEMO-07 | MC 편집 도중 외부에서 같은 파일 동시 변경 | 충돌 알림 + 3옵션: 외부 수용 / MC 유지 / 수동 병합. BR-MEMO-07이 BR-MEMO-02보다 우선. | `[추론]` | Must | 검토중 |

---

## §7 프로젝트·태그 (v1.3 재정의)

> **v1.3 변경**: 태그 기반 프로젝트 모델 폐기. 프로젝트는 독립 엔티티(business_id 또는 NULL).

### §7.1 폐기 (v1.3에서 무효)

| BR ID | 폐기 사유 | 대체 |
|-------|---------|------|
| ~~BR-PROJ-OLD-02~~ | "정식 프로젝트 ⊂ 태그" 모델 폐기 (v1.3) | BR-PROJ-01 (계층 모델) |
| ~~BR-PROJ-OLD-03~~ | 정식 프로젝트 ↔ 태그 전환 무의미 (독립 엔티티) | BR-PROJ-03 |
| ~~BR-STATE-10~~ | 정식 프로젝트 → 태그 강등 모델 폐기 | (대체 없음) |

### §7.2 활성 v1.3

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 |
|-------|---------|-----------|------|---------|------|
| BR-PROJ-01 | 프로젝트 생성 | FR-FILES-01에 따라 폴더 자동 생성 (MC-Notes/{org}/{business}/{project}/) | `[iet03]` | Must | 확인됨 |
| BR-PROJ-02 | business_id = NULL | "무소속" 섹션에 분류 | `[추론]` | Must | 검토중 |
| BR-PROJ-03 | 프로젝트 삭제 | 연결된 items는 project_id = NULL로 해제 (items 삭제 X) | `[추론]` | Must | 검토중 |
| BR-PROJ-04 | end_date 초과 + status != done | 알림 트리거 (notification_events) | `[추론]` | Should | 검토중 |
| BR-PROJ-05 | 자동 프로젝트 묶음 제안 | **금지** (V1). 사용자 수동 분류만. | `[iet03]` | Must | 확인됨 |

### §7.3 태그 (단순화)

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 |
|-------|---------|-----------|------|---------|------|
| BR-TAG-01 | 태그명 입력 | unique (대소문자 무시). 신규 태그 자동 생성. | `[추론]` | Must | 검토중 |
| BR-TAG-02 | 항목당 태그 100개 초과 | 경고 표시. 강제 한도 X. | `[추론]` | Could | 검토중 |

---

## §8 Git 연동

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 |
|-------|---------|-----------|------|---------|------|
| BR-GIT-01 | PAT 저장 | Windows Credential Manager(DPAPI). 평문 저장 금지. | `[iet03]` | Must | 확인됨 |
| BR-GIT-02 | 자동 동기 주기 설정 | 디폴트 15분. 사용자 옵션 5/15/30분. | `[추론]` | Should | 검토중 |
| BR-GIT-03 | API 호출 실패 (토큰 만료/네트워크) | 마지막 캐시 유지 + 알림 표시. | `[추론]` | Must | 검토중 |
| BR-GIT-04 | GitHub Rate Limit 도달 | 다음 재시도 시각 표시 + 자동 동기 일시 정지. | `[추론]` | Should | 검토중 |
| BR-GIT-05 | 1,000개 이상 이슈 | 페이지네이션 50개/페이지. 최근 활동 우선 정렬. | `[추론]` | Should | 검토중 |
| BR-GIT-06 | repo 권한 회수 감지 | 인증 실패 알림 + 토큰 재확인 안내. 캐시 read-only 유지. | `[추론]` | Must | 검토중 |

---

## §9 일별 의식

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 |
|-------|---------|-----------|------|---------|------|
| BR-DAY-01 | 저녁 회고에서 반성 메모 입력 | `MC-Notes/YYYY/MM/DD-review.md` 별도 파일에 저장. 같은 날 추가 시 해당 파일에 append. | `[iet03]` | Must | 확인됨 |
| BR-DAY-02 | 미완료 태스크 이월 | 원본 ID 보존. 날짜·시간만 다음 날 또는 지정 일자로 이동. 새 인스턴스 생성 X. | `[iet03]` | Must | 확인됨 |
| BR-DAY-03 | 회고 없이 다음 날 첫 진입 | 어제 회고 진입 옵션 표시. 스킵 가능. | `[추론]` | Should | 검토중 |
| BR-DAY-04 | 아침 프리뷰 | 오늘 일정 + 미완료(이월) 태스크 + 어제 메모 1~3개. 빈 상태도 인사 표시. | `[추론]` | Must | 검토중 |
| BR-DAY-09 | 저녁 회고 + 미완료 항목 존재 (v1.5) | 항목별 카테고리(7종) + 자유 메모 + 결정(4종) 입력 UI 표시 | `[iet03]` | Must | 확인됨 |
| BR-DAY-10 | 카테고리 미선택 + 결정 클릭 (v1.5) | "사유를 선택하세요" 인라인 안내. 저장 차단 | `[iet03]` | Must | 확인됨 |
| BR-DAY-11 | 결정 = `carry_over` (v1.5) | items.scheduled_at = 내일 (BR-DAY-02 동일 메커니즘) | `[iet03]` | Must | 확인됨 |
| BR-DAY-12 | 결정 = `cancel` (v1.5) | items.status = 'cancelled' | `[iet03]` | Must | 확인됨 |
| BR-DAY-13 | incomplete_reasons 저장 (v1.5) | review_date·item_id·category·decision 필수, free_text는 nullable | `[iet03]` | Must | 확인됨 |

---

## §10 알림·충돌·백업

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 |
|-------|---------|-----------|------|---------|------|
| BR-NOTIFY-01 | 일정 시작 5분 전 (디폴트 ON) | Windows OS 시스템 알림 발송. 사용자 OFF 옵션 있음. | `[iet03]` | Must | 확인됨 |
| BR-CONFLICT-01 | 일정 등록 시 동일 시간대(겹치는 구간) 일정 1건↑ 존재 | 경고: "같은 시간 일정 N건 있음 — [기존 보기] [그래도 등록] [다른 시간]". 강제 차단 X. LLM 없이 SQL 시간 범위 쿼리만. | `[iet03]` | Must | 확인됨 |
| BR-BACKUP-01 | 사용자가 "JSON export" 클릭 | DB 전체 JSON export → 사용자 지정 위치 저장. 자동 스케줄 X. | `[iet03]` | Must | 확인됨 |

---

## §11 AI

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 |
|-------|---------|-----------|------|---------|------|
| BR-AI-01 | AI 추론 결과 (STT, 슬롯 추출, 태그 제안) 도출 | 항상 사용자 확인 후 적용. 자동 적용 금지. | `[iet03]` | Must | 확인됨 |
| BR-AI-02 | 항목 추가 시 | 즉시 백그라운드 임베딩 → sqlite-vec 저장. 사용자 차단 없음. | `[추론]` | Must | 검토중 |
| BR-AI-03 | 첫 설치 또는 LocalDocsHub 폴더 등록 시 | 백그라운드 배치 인덱싱. 진행률 표시. | `[추론]` | Must | 검토중 |
| BR-AI-04 | 의미 검색 결과 0건 | FTS5 키워드 검색 fallback 자동 실행 후 결과 표시. | `[추론]` | Must | 검토중 |
| BR-AI-05 | 인덱스 항목 30개 미만 | 태그 제안 비활성. | `[iet03]` | Must | 확인됨 |
| BR-AI-06 | Whisper confidence < 0.6 | 결과 표시 + "다시 말하기" 버튼. | `[추론]` | Should | 검토중 |
| BR-AI-07 | Phi-3 슬롯 추출 실패 또는 모호 (V1.1) | 원문을 그대로 메모로 저장 (fallback). | `[추론]` | Must | 검토중 |
| BR-AI-08 | AI 모델 첫 로드 | 앱 시작 시 백그라운드 로드. 첫 호출이 로드 완료 전이면 진행률 + 대기 안내. | `[추론]` | Must | 검토중 |
| BR-AI-09 | 시스템 RAM 여유 < 1GB | Whisper/Phi-3 unload. 재호출 시 lazy load. | `[추론]` | Should | 검토중 |
| BR-AI-TAG-01 | 사용자가 신규 태그 입력 (v1.5) | KoE5 임베딩 + cosine sim ≥ 0.85 시 기존 태그 제안 ([기존 사용][신규 생성]) | `[iet03]` | Must | 확인됨 |
| BR-AI-TAG-02 | 사용자 "기존 태그 사용" 선택 (v1.5) | item_tags에 기존 tag_id 사용. 신규 tags row 생성 X | `[iet03]` | Must | 확인됨 |
| BR-AI-TAG-03 | 사용자 "그래도 신규" 선택 (v1.5) | tags 신규 row 생성. 머지 결정은 사용자 권한 | `[iet03]` | Must | 확인됨 |
| BR-AI-TAG-04 | 월 1회 위생 작업 (v1.5) | 사용 빈도 ≤ 1 + sim ≥ 0.9 태그쌍 → "병합 제안" 알림 | `[iet03]` | Should | 확인됨 |

---

## §12 외부 연동

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 | 상태 |
|-------|---------|-----------|------|---------|------|
| BR-COLD-01 | 프로젝트 아카이브 트리거 (V1.2) | Drive 업로드 성공 확인 후에만 로컬 .md 삭제. 실패 시 로컬 유지. | `[iet03]` | Must | 확인됨 |
| BR-COLD-02 | Drive 업로드 성공 후 | SQLite `file_location='cold'` + `drive_file_id` 기록 완료 후 로컬 .md 삭제. | `[iet03]` | Must | 확인됨 |
| BR-COLD-03 | Cold 전환 완료 후 | 태그·프로젝트 매핑·벡터 임베딩 SQLite 유지. Cold 상태에서도 검색 가능. | `[추론]` | Must | 검토중 |
| BR-COLD-04 | Cold 항목 재활성화 도중 | 로컬 복원 완료 전 SQLite `file_location` 변경 금지. | `[추론]` | Must | 검토중 |
| BR-GCAL-01 | GCal 이벤트 + MC 항목 동시간대 (v1.4) | Today's Flow에 Google 뱃지(🗓)와 함께 별도 행 표시 | `[iet03]` | Must | 확인됨 |
| BR-GCAL-02 | GCal API 실패 (network/OAuth) (v1.4) | 마지막 캐시 유지, "GCal 동기화 오류" 아이콘 표시 | `[추론]` | Must | 확인됨 |
| BR-GCAL-03 | mc_status='done' 항목 재폴링 (v1.4) | mc_status 보존, title/time만 갱신 | `[추론]` | Must | 확인됨 |
| BR-GCAL-04 | GCal에서 이벤트 삭제됨 (v1.4) | gcal_cache.visible=0 (soft-delete). MC에서 제거 | `[추론]` | Must | 확인됨 |
| BR-GCAL-05 | 사용자가 GCal 이벤트 "완료" 클릭 (v1.4) | gcal_cache.mc_status='done'만 저장. GCal API 쓰기 X | `[iet03]` | Must | 확인됨 |
| BR-GCAL-06 | mc_status='done' 항목 폴링 시 (v1.4) | mc_status 유지, title/time만 갱신 (BR-GCAL-03 연계) | `[추론]` | Must | 확인됨 |
| BR-GCAL-07 | mc_status='done' 항목 표시 (v1.4) | 취소선 + 흐린 처리. 필터 "완료 숨김" 적용 가능 | `[추론]` | Should | 확인됨 |

---

## §15 운영성 (v1.1, OPS 모듈)

> 출처: 03_PRD_OPS.md (Phase 4 v1.1 코덱스 검토 보강)

### §15.1 Capture Inbox

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 |
|-------|---------|-----------|------|---------|
| BR-INBOX-01 | 외부 입력(TG/Voice<0.8/Quick Capture 모호) | capture_inbox 경유. 사용자 검수 후 items 직행 | `[코덱스 검토]` | Must |
| BR-INBOX-02 | pending 14일 경과 | status='expired'. 자동 삭제 X | `[iet03]` | Must |
| BR-INBOX-03 | 수락 시 | items 생성 + capture_inbox.accepted_item_id 양방향. raw_text 영구 보존 | `[iet03]` | Must |
| BR-INBOX-04 | 거부 후 30일 경과 | 자동 삭제 | `[iet03]` | Should |

### §15.2 Diagnostics

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 |
|-------|---------|-----------|------|---------|
| BR-DIAG-01 | 외부 워커 health 1초 timeout | 'unknown' 표시 (장애 단정 금지) | `[iet03]` | Must |
| BR-DIAG-02 | 사용자 액션(재시작/VACUUM) | notification_events에 audit 로그 | `[추론]` | Should |
| BR-DIAG-03 | SC-10 자동 새로고침 | 10초 간격. 탭 비활성 시 멈춤 | `[추론]` | Should |

### §15.3 Notification & Retry Center

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 |
|-------|---------|-----------|------|---------|
| BR-NOTIFY-CTR-01 | 모든 토스트 발송 시 | notification_events에 동시 기록. dismiss 전까지 SC-11 표시 | `[코덱스 검토]` | Must |
| BR-RETRY-01 | 외부 통합 실패 | 지수 백오프 1m/5m/30m/2h. 최대 5회 | `[iet03]` | Must |
| BR-RETRY-02 | 5회 실패 | 자동 재시도 중단, 사용자 개입 요청 (kind='retry_failed') | `[iet03]` | Must |
| BR-RETRY-03 | 사용자 [건너뛰기] | resolved=1. 같은 페이로드 재발생 시 새 row | `[추론]` | Should |

### §15.4 Credentials

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 |
|-------|---------|-----------|------|---------|
| BR-SET-CRED-01 | 토큰 등록·표시 | 평문 화면 표시 절대 금지. 등록 여부 + 검증 시각만 | `[ADR-005][iet03]` | Must |
| BR-SET-CRED-02 | "검증" 버튼 | 해당 API read 호출 1회. 쓰기 호출 금지 | `[추론]` | Must |
| BR-SET-CRED-03 | 토큰 삭제 | keyring + settings + 관련 워커 일괄 정리 | `[iet03]` | Must |
| BR-SET-CRED-04 | secret-bridge 미동작 | SC-08-Cred read-only. 등록·삭제 비활성 | `[ADR-005]` | Must |
| BR-SET-CRED-05 | 검증 실패 토큰 | 24h 후 자동 재검증 1회 | `[iet03]` | Should |

---

## §16 조직 계층 · 라벨 · 파일 (v1.3 신설)

> 출처: 03_PRD_ORG.md

### §16.1 Organization · Business

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 |
|-------|---------|-----------|------|---------|
| BR-ORG-01 | 소속 삭제 + 하위 사업 > 0 | 삭제 차단 + 경고 | `[추론]` | Must |
| BR-ORG-02 | 로고 파일 저장 | MC-Notes/.assets/logos/{org_id}.{ext}로 복사 | `[추론]` | Must |
| BR-ORG-03 | 소속 생성 | MC-Notes/{org_name}/ 폴더 자동 생성 | `[iet03]` | Must |
| BR-BUS-01 | 사업 생성 | MC-Notes/{org}/{business}/ 폴더 자동 생성 | `[iet03]` | Must |
| BR-BUS-02 | 사업 삭제 + 하위 프로젝트 > 0 | 삭제 차단 + 경고 | `[추론]` | Must |
| BR-BUS-03 | org_id = NULL | MC-Notes/무소속/{business}/ 폴더 생성 | `[추론]` | Must |

### §16.2 라벨

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 |
|-------|---------|-----------|------|---------|
| BR-LABEL-01 | 시스템 라벨 삭제 시도 | 차단 — 비활성화만 가능 | `[추론]` | Must |
| BR-LABEL-02 | 항목에 라벨 추가 | Today's Flow + 캘린더 동시 반영 | `[추론]` | Must |

### §16.3 파일·폴더

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 |
|-------|---------|-----------|------|---------|
| BR-FILES-01 | 폴더명 특수문자 포함 | `/\:*?"<>\|` → `-` 치환 | `[추론]` | Must |
| BR-FILES-02 | 폴더 이미 존재 | 기존 폴더 재사용. 오류 X | `[추론]` | Must |
| BR-FILES-03 | 소속/사업/프로젝트 이름 변경 | 폴더 rename + file_index 경로 일괄 갱신 (트랜잭션) | `[추론]` | Must |
| BR-FILES-04 | Google Drive for Desktop 설정 | MC-Notes를 Drive sync 폴더 내 위치 안내 | `[iet03]` | Should |

---

## §17 메모 v1.5 (Milkdown · Lifecycle · Morphing)

> 출처: 03_PRD_MEMO_PROJ.md FR-MEMO-06~07

| BR ID | 조건 (IF) | 동작 (THEN) | 출처 | 우선순위 |
|-------|---------|-----------|------|---------|
| BR-MEMO-08 | 메모 편집 시 sha256 변경 | file_index.evolution_count += 1 | `[iet03]` | Must |
| BR-MEMO-09 | evolution_count ≥ 3 | SC-04에서 미세한 pulse CSS 효과 표시 | `[iet03]` | Should |
| BR-MEMO-10 | 메모에 `- [ ]` 체크박스 추가 | items.type='memo' → 'task' 자동 변환 + WAAPI 300ms morph | `[iet03]` | Must |
| BR-MEMO-11 | 신규 메모 캡처 (v1.5 D7) | MC-Notes/inbox/ 자동 저장. 정리 시 프로젝트 폴더 이동 | `[iet03]` | Must |

---

## §13 규칙 간 충돌·우선순위

| 규칙 A | 규칙 B | 충돌 상황 | 해결 방안 |
|--------|--------|---------|---------|
| BR-MEMO-02 (외부 변경 인덱스 갱신) | BR-MEMO-07 (충돌 3옵션) | "MC 변경 유지" 선택 시 외부 변경 무시 | BR-MEMO-07 우선. 사용자 명시 선택 시만 적용 |
| BR-AI-01 (자동 적용 금지) | BR-CAP-05 (#태그 자동 추가) | `#태그`는 사용자 명시 입력 — 충돌 아님 | OK |
| BR-PROJ-05 (자동 묶음 금지) | BR-AI-05 (태그 제안) | 태그 *제안*은 자동 묶음 아님 — 충돌 아님 | OK |

---

## §14 미확인 규칙 ([추론], Phase 3 내 확인 필요)

| Rule ID | 추정 규칙 | 근거 | 확인 담당 | 상태 |
|---------|---------|------|---------|------|
| BR-CAP-01 ~ 07 전체 | 자동 분류 로직 세부 | OQ-02-03 | iet03 | Phase 3 셀프 검토 |
| BR-VAL-01 ~ 06 전체 | 입력 유효성 수치 | 합리적 디폴트 | iet03 | Phase 3 셀프 검토 |
| BR-AI-06 (confidence 임계값 0.6) | Whisper 실제 분포 기반 | `[추론]` | Phase 4 실험 | Open |

---

## Change Log

| 버전 | 날짜 | 변경 내용 | 변경자 |
|------|------|----------|--------|
| 1.0 | 2026-04-27 | Phase 1 BRs + Phase 2 추가분 통합 | BA Writer v1.0 |
