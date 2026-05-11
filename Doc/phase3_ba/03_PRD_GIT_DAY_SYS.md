# PRD — Git 연동 (GIT) + 일별 의식 (DAY) + 시스템 (SYS)

> 모듈: FR-GIT-01~04, FR-DAY-01~04, FR-NOTIFY-01, FR-CONFLICT-01, FR-BACKUP-01
> 우선순위: Must (전체)
> 작성: 2026-04-27 | BA Writer v1.0
> v1.5 개정: 2026-05-06 — FR-DAY-04 (미완료 사유 캡처) 추가

---

## FR-GIT-01: GitHub PAT 등록

**한 줄**: GitHub Personal Access Token을 Windows Credential Manager에 안전하게 저장한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: PAT 정상 등록
  Given Settings > GitHub 연동 화면이 열려 있다
  When  유효한 PAT를 입력하고 "저장" 클릭한다
  Then  Windows Credential Manager(DPAPI)에 저장된다
  And   평문 파일에 기록되지 않는다
  And   유효성 검증 API 호출 성공 알림이 표시된다

Scenario: 무효 PAT 입력
  Given PAT 입력 필드가 있다
  When  만료된 또는 권한 없는 PAT를 입력한다
  Then  "PAT가 유효하지 않습니다. 권한을 확인하세요" 오류가 표시된다
  And   저장되지 않는다

Scenario: PAT 평문 저장 금지
  Given PAT가 입력된다
  When  저장 후 파일시스템을 확인한다
  Then  어떤 .txt/.json/.env 파일에도 PAT 값이 없다
```

### 테스트 케이스

| TC-ID | 연결 AC | 시나리오 | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|---------|------|---------|
| TC-GIT-01-01 | AC-1 | 정상 저장 | Credential Manager 확인 | 통합 | P0 |
| TC-GIT-01-02 | AC-2 | 무효 PAT | 오류 메시지, 미저장 | 통합 | P0 |
| TC-GIT-01-03 | AC-3 | 평문 없음 | 파일시스템 스캔 | 보안 | P0 |

---

## FR-GIT-02: 정식 프로젝트에 repo 연결

**한 줄**: 정식 프로젝트에 GitHub repo URL을 연결한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: 유효한 repo URL 연결
  Given 정식 프로젝트가 존재한다
  When  "https://github.com/iet03/mc" URL을 입력하고 연결한다
  Then  URL 패턴 검증 통과 후 projects.github_repo에 저장된다

Scenario: 잘못된 URL 형식
  Given repo URL 입력 필드가 있다
  When  "github.com/mc" (https:// 없음)를 입력한다
  Then  "올바른 GitHub URL 형식이 아닙니다" 인라인 오류가 표시된다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-GIT-02-01 | AC-1 | 유효 URL 저장 | 단위 | P1 |
| TC-GIT-02-02 | AC-2 | URL 형식 오류 | 단위 | P1 |

---

## FR-GIT-03: 이슈·PR·진척도 조회

**한 줄**: 연결된 repo의 이슈·PR을 조회하여 컨텍스트 패널에 표시한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: 이슈 목록 조회 성공
  Given 프로젝트에 repo가 연결되어 있고 PAT가 유효하다
  When  컨텍스트 패널을 열거나 주기 동기화가 실행된다
  Then  open 이슈 목록(번호·제목·상태)이 표시된다

Scenario: API 실패 시 캐시 표시
  Given GitHub API 호출이 네트워크 오류로 실패한다
  When  이슈 조회를 시도한다
  Then  마지막 캐시 데이터가 "(캐시)" 표시와 함께 출력된다
  And   "GitHub 연결 불가 — 마지막 동기: {시각}" 알림이 표시된다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-GIT-03-01 | AC-1 | 이슈 목록 표시 | 통합 | P1 |
| TC-GIT-03-02 | AC-2 | 오프라인 캐시 fallback | 통합 | P0 |

---

## FR-GIT-04: 자동 동기 캐시

**한 줄**: 설정 주기(디폴트 15분)로 GitHub 이슈·PR 캐시를 자동 갱신한다. `[추론]`

### Acceptance Criteria

```gherkin
Scenario: 자동 동기 실행
  Given 마지막 동기로부터 15분이 경과했다 (디폴트 설정)
  When  자동 동기 타이머가 실행된다
  Then  background에서 API 호출 후 SQLite github_items 캐시가 갱신된다
  And   UI가 차단되지 않는다

Scenario: Rate Limit 도달
  Given GitHub API Rate Limit에 도달했다
  When  자동 동기를 시도한다
  Then  "Rate Limit 초과 — 다음 재시도: {시각}" 알림이 표시된다
  And   자동 동기가 Rate Limit 해제 시각까지 일시 정지된다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-GIT-04-01 | AC-1 | 백그라운드 동기 | UI 차단 없음, DB 갱신 | 통합 | P1 |
| TC-GIT-04-02 | AC-2 | Rate Limit 처리 | 알림 + 자동 정지 | 통합 | P1 |

---

## FR-DAY-01: 아침 프리뷰

**한 줄**: 당일 첫 실행 시 오늘 일정·이월 태스크·어제 메모를 한눈에 보여준다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: 아침 프리뷰 정상 표시
  Given 당일 첫 실행이다
  When  앱이 열린다
  Then  오늘 일정 목록, 이월된 미완료 태스크, 어제 메모 최근 1~3개가 표시된다
  And   1초 이내에 렌더된다

Scenario: 모든 항목이 없는 날
  Given 오늘 일정이 0개, 이월 태스크 0개다
  When  아침 프리뷰가 열린다
  Then  "좋은 아침입니다" 빈 상태 메시지 + Quick Capture가 표시된다

Scenario: 아침 프리뷰에서 Quick Capture
  Given 아침 프리뷰가 표시된다
  When  Quick Capture에 내용을 입력하고 저장한다
  Then  항목이 Today's Flow에 즉시 추가된다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-DAY-01-01 | AC-1 | 프리뷰 1초 이내 렌더 | E2E | P1 |
| TC-DAY-01-02 | AC-2 | 빈 상태 인사 | E2E | P1 |
| TC-DAY-01-03 | AC-3 | QC → 즉시 추가 | 통합 | P1 |

---

## FR-DAY-02: 저녁 회고 화면

**한 줄**: 오늘 완료·미완료 항목을 복기하고 반성 메모를 입력한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: 완료·미완료 항목 표시
  Given 저녁 회고 화면에 진입한다
  When  화면이 열린다
  Then  오늘 완료 항목과 미완료 항목이 구분되어 표시된다

Scenario: 반성 메모 저장
  Given 저녁 회고 화면이 열려 있다
  When  반성 메모를 입력하고 저장한다
  Then  MC-Notes/YYYY/MM/DD-review.md에 내용이 저장된다 (BR-DAY-01)

Scenario: 회고 없이 다음 날 진입
  Given 어제 회고를 하지 않았다
  When  오늘 앱에 진입한다
  Then  "어제 회고를 완료하시겠어요?" 옵션이 표시된다
  And   "나중에" 선택 시 스킵 가능하다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-DAY-02-01 | AC-1 | 항목 구분 표시 | E2E | P1 |
| TC-DAY-02-02 | AC-2 | review.md 저장 | 통합 | P0 |
| TC-DAY-02-03 | AC-3 | 어제 회고 안내 | E2E | P2 |

---

## FR-DAY-03: 미완료 이월·보류

**한 줄**: 미완료 태스크를 다음 날로 이월하거나 보류 상태로 전환한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: 이월 처리
  Given 미완료 태스크가 있다
  When  "내일로" 이월 액션을 선택한다
  Then  해당 태스크의 scheduled_at이 내일 날짜로 변경된다 (원본 ID 보존, BR-DAY-02)
  And   새 인스턴스가 생성되지 않는다

Scenario: 보류 처리
  Given 미완료 태스크가 있다
  When  "보류" 액션을 선택한다
  Then  태스크 상태가 waiting으로 변경된다 (BR-STATE-03)
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-DAY-03-01 | AC-1 | 이월 — 원본 ID 유지 | 단위 | P0 |
| TC-DAY-03-02 | AC-2 | 보류 상태 변경 | 단위 | P1 |

---

## FR-DAY-04: 미완료 사유 캡처 (V1.0, v1.5 신규)

**한 줄**: 저녁 회고 시 미완료 항목별로 카테고리·자유 메모·결정을 입력하고 데이터로 누적한다. `[iet03]` (D4)
**비즈니스 가치**: "왜 미완료가 반복되는가"를 6개월 누적 후 패턴으로 발견. V1.1 Reflection Insights(SC-15)의 데이터 소스.

### 미완료 카테고리 7종 (D4 enum)

| 카테고리 | 의미 |
|---------|------|
| `time_short` | 시간 부족 |
| `priority_shift` | 우선순위 변경 |
| `external_block` | 외부 의존(다른 사람·자료 대기) |
| `motivation_low` | 동기·집중 부족 |
| `info_lack` | 정보 부족 |
| `overestimated` | 과대평가(처음부터 무리한 목표) |
| `other` | 기타(자유 메모로 보충) |

### 결정 4종

| 결정 | 의미 |
|------|------|
| `carry_over` | 다음 날로 이월 (FR-DAY-03 연계) |
| `cancel` | 취소(필요 없어짐) |
| `reschedule` | 다른 날짜로 재일정 |
| `split` | 분할(작은 task로 나눔, 사용자 후속 작업) |

### 비즈니스 규칙

| BR-ID | IF | THEN | 출처 |
|-------|----|------|------|
| BR-DAY-09 | 저녁 회고 진입 + 미완료 항목 존재 | 항목별로 카테고리 칩 + 자유 메모 + 결정 버튼 표시 | `[iet03]` |
| BR-DAY-10 | 카테고리 입력 없이 결정만 클릭 | 카테고리 필수 — "사유를 선택하세요" 인라인 안내 | `[iet03]` |
| BR-DAY-11 | 결정 = `carry_over` 선택 | items.scheduled_at 내일로 변경 (FR-DAY-03 BR-DAY-02 동일) | `[iet03]` |
| BR-DAY-12 | 결정 = `cancel` 선택 | items.status='cancelled' | `[iet03]` |
| BR-DAY-13 | incomplete_reasons에 record 저장 | review_date·item_id·category·decision 필수, free_text는 nullable | `[iet03]` |

> **ID 충돌 회피**: 04_Business_Rules_Log.md §9에 기존 BR-DAY-04 (아침 프리뷰)가 있어 v1.5 사유 캡처 BR은 BR-DAY-09부터 시작.

### Acceptance Criteria

```gherkin
Scenario: 미완료 항목별 사유·결정 입력
  Given 저녁 회고 화면이 열려 있고 미완료 task 3개가 표시된다
  When  첫 task에 카테고리 "external_block" 선택, 자유 메모 "고객 답변 대기", 결정 "carry_over"를 입력한다
  Then  incomplete_reasons에 row 1개가 저장된다
  And   해당 task의 scheduled_at이 내일로 변경된다 (BR-DAY-11)

Scenario: 카테고리 미선택 시 결정 차단
  Given 미완료 항목 행이 있다
  When  카테고리 없이 결정 버튼을 클릭한다
  Then  "사유를 선택하세요" 인라인 안내가 표시된다 (BR-DAY-10)
  And   incomplete_reasons에 저장되지 않는다

Scenario: cancel 결정 처리
  Given 미완료 task가 있다
  When  카테고리 "priority_shift" 선택 후 결정 "cancel" 클릭한다
  Then  items.status가 'cancelled'로 변경된다 (BR-DAY-12)
  And   incomplete_reasons에 사유가 보존된다

Scenario: 자유 메모 옵셔널
  Given 카테고리 "time_short" 선택, 자유 메모 비움, 결정 "carry_over"를 입력한다
  When  저장한다
  Then  free_text=NULL로 정상 저장된다 (BR-DAY-13)
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-DAY-04-01 | AC-1 | 사유·결정 → DB + 이월 | E2E | P0 |
| TC-DAY-04-02 | AC-2 | 카테고리 필수 검증 | 단위 | P0 |
| TC-DAY-04-03 | AC-3 | cancel → status 변경 | 통합 | P1 |
| TC-DAY-04-04 | AC-4 | free_text NULL 허용 | 단위 | P2 |

> **V1.1 연계**: incomplete_reasons 누적 데이터 → SC-15 "Reflection Insights" 화면에서 카테고리별 시계열·프로젝트별 빈도·자동 인사이트 도출 (D5).

---

## FR-NOTIFY-01: 일정 5분 전 OS 알림

**한 줄**: 일정 시작 5분 전 Windows OS 시스템 알림을 발송한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: 5분 전 알림 정상 발송
  Given 일정이 15:00에 예약되어 있다
  When  14:55가 된다
  Then  Windows toast 알림이 표시된다 ("15:00 — {일정명}" 메시지)

Scenario: 알림 OFF 설정
  Given 사용자가 Settings에서 알림을 OFF로 설정했다
  When  일정 5분 전이 된다
  Then  알림이 발송되지 않는다

Scenario: MC 미실행 중 알림
  Given MC 앱이 종료되어 있다
  When  일정 5분 전이 된다
  Then  트레이 백그라운드 프로세스가 알림을 발송한다 (트레이 모드 전제)
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-NOTIFY-01-01 | AC-1 | toast 발송 시각 | 통합 | P0 |
| TC-NOTIFY-01-02 | AC-2 | OFF 시 미발송 | 통합 | P1 |
| TC-NOTIFY-01-03 | AC-3 | 백그라운드 발송 | E2E | P1 |

### NFR

| 항목 | 값 |
|------|---|
| 알림 발송 지연 | ≤ 10초 (5분 기준 ±10초) |
| 백그라운드 트레이 메모리 | ≤ 30MB |

---

## FR-CONFLICT-01: 일정 충돌 경고

**한 줄**: 일정 등록 시 겹치는 구간의 기존 일정을 경고한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: 충돌 경고 표시
  Given 14:00~15:00 일정이 존재한다
  When  14:30~15:30 새 일정을 등록하려 한다
  Then  "같은 시간 일정 1건 있음" 경고가 표시된다
  And   [기존 보기] [그래도 등록] [다른 시간] 3가지 옵션이 제공된다

Scenario: 경고에서 그래도 등록
  Given 충돌 경고가 표시된 상태다
  When  [그래도 등록]을 클릭한다
  Then  중복 일정이 등록된다 (강제 차단 X)

Scenario: 충돌 없는 일정 등록
  Given 14:00~15:00 일정이 있고 15:00~16:00 신규 일정을 등록한다
  When  시간 범위 SQL 쿼리를 실행한다
  Then  충돌 없음으로 경고 없이 정상 등록된다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-CONFLICT-01-01 | AC-1 | 겹침 경고 + 3옵션 | 통합 | P0 |
| TC-CONFLICT-01-02 | AC-2 | 강제 등록 허용 | E2E | P1 |
| TC-CONFLICT-01-03 | AC-3 | 비충돌 정상 등록 | 단위 | P1 |

---

## FR-BACKUP-01: JSON export 백업

**한 줄**: 메뉴에서 DB 전체를 JSON으로 export한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: JSON export 정상 실행
  Given Settings > "JSON export" 메뉴가 있다
  When  클릭하고 저장 경로를 선택한다
  Then  items·projects·tags·mappings·github_items 전체가 JSON으로 저장된다
  And   파일명: mc_backup_YYYYMMDD_HHMMSS.json

Scenario: export 중 오류
  Given 저장 경로의 디스크가 꽉 찼다
  When  export를 실행한다
  Then  "디스크 공간이 부족합니다" 오류가 표시된다
  And   불완전한 파일이 남지 않는다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-BACKUP-01-01 | AC-1 | JSON 파일 생성, 전체 테이블 포함 | E2E | P1 |
| TC-BACKUP-01-02 | AC-2 | 오류 시 불완전 파일 없음 | 통합 | P1 |

---

## Change Log

| 버전 | 날짜 | 변경 내용 | 변경자 |
|------|------|----------|--------|
| 1.0 | 2026-04-27 | 최초 작성 | BA Writer v1.0 |
