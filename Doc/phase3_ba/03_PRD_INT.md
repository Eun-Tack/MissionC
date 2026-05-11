# PRD — 외부 연동 (INT)

> 모듈: FR-INT-TG-01~02 (V1.0), FR-INT-GH-01~02 (V1.0), FR-INT-GCAL-01~02 (V1.0), FR-INT-DR-01~04 (V1.1)
> 작성: 2026-04-27 | BA Writer v1.0 | v1.3 개정: 2026-05-04 (FR-INT-GCAL 추가)
> 상세 연동 아키텍처: [04_Integration_Map](../phase2_strategy/04_Integration_Map.md)

---

## FR-INT-TG-01: Telegram → MC 빠른 캡처 (V1.0)

**한 줄**: Telegram Bot 수신 메시지를 MC 항목으로 자동 생성한다. `[iet03]`
**비즈니스 가치**: 이동 중에 MC 앱 없이도 빠른 캡처. `[iet03]`

### 처리 흐름

```
1. Telegram Bot이 메시지 수신 (polling/webhook)
2. 날짜·시간 패턴 파싱 (dateutil)
   ├─ 파싱 성공: 타입=일정, 미리보기 대기 없이 Inbox에 저장 (사용자 MC에서 확인)
   └─ 파싱 실패: 타입=메모로 Inbox 저장
3. SQLite 저장 + Today's Flow에 반영
실패: 재시도 큐에 보관, 다음 연결 시 처리
```

### Acceptance Criteria

```gherkin
Scenario: Telegram 텍스트 메시지 캡처
  Given Telegram Bot이 설정되어 있다
  When  "내일 오전 9시 조회 미팅"을 Bot에게 전송한다
  Then  MC Inbox에 {title: "조회 미팅", scheduled: "내일 09:00"} 항목이 생성된다
  And   MC Today's Flow에 표시된다

Scenario: 파싱 불가 메시지
  Given Bot에 "아이디어 정리 필요"를 전송한다
  When  날짜 파싱이 실패한다
  Then  타입 메모로 Inbox에 저장된다

Scenario: 네트워크 단절 중 메시지
  Given MC 서버가 일시적으로 오프라인이다
  When  Telegram으로 메시지가 전송된다
  Then  재시도 큐에 보관되어 연결 복구 시 처리된다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-TG-01-01 | AC-1 | 일정 파싱 + 저장 | 통합 | P0 |
| TC-TG-01-02 | AC-2 | 파싱 실패 메모 저장 | 통합 | P1 |
| TC-TG-01-03 | AC-3 | 오프라인 큐 | 통합 | P1 |

---

## FR-INT-TG-02: MC → Telegram 알림 push (V1.0)

**한 줄**: BR-NOTIFY-01 트리거 시 Telegram Bot이 사용자에게 알림을 발송한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: 일정 알림 Telegram 발송
  Given 일정 시작 5분 전이 되었다
  When  BR-NOTIFY-01이 트리거된다
  Then  Telegram Bot이 "📅 5분 후 — {일정명}" 메시지를 발송한다

Scenario: 사용자 "확인" reply
  Given Telegram 알림이 발송되었다
  When  사용자가 "확인"으로 reply한다
  Then  MC에서 해당 알림 상태가 dismissed로 변경된다

Scenario: 발송 실패 처리
  Given Telegram API가 일시적으로 실패한다
  When  알림 발송을 시도한다
  Then  재시도 큐에 추가된다 (최대 3회, 10분 간격)
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-TG-02-01 | AC-1 | 알림 발송 확인 | 통합 | P1 |
| TC-TG-02-02 | AC-2 | 확인 reply → dismissed | 통합 | P2 |
| TC-TG-02-03 | AC-3 | 실패 재시도 | 통합 | P1 |

---

## FR-INT-GH-01: GitHub 이슈·PR 조회 (V1.0)

**한 줄**: 정식 프로젝트에 연결된 repo의 이슈·PR을 주기적으로 캐시한다. `[iet03]`

*(주요 처리 흐름 및 AC는 FR-GIT-03/04에서 다룸. 여기서는 컨텍스트 패널 표시에 집중.)*

### Acceptance Criteria

```gherkin
Scenario: 컨텍스트 패널 이슈 표시
  Given 프로젝트에 GitHub repo가 연결되어 있고 이슈 3개가 open이다
  When  컨텍스트 패널을 연다
  Then  이슈 번호·제목·상태 3개가 표시된다

Scenario: 이슈 없음 상태
  Given repo에 open 이슈가 없다
  When  컨텍스트 패널을 연다
  Then  "GitHub 이슈 없음" 빈 상태가 표시된다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-GH-01-01 | AC-1 | 이슈 3개 표시 | 통합 | P1 |
| TC-GH-01-02 | AC-2 | 빈 상태 표시 | E2E | P2 |

---

## FR-INT-GH-02: GitHub 이슈 생성 (V1.0)

**한 줄**: MC에서 직접 GitHub 이슈를 생성하고 태스크에 연결한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: 이슈 정상 생성
  Given 컨텍스트 패널에서 "→ GitHub 이슈 생성" 버튼을 클릭한다
  When  제목 "NPU 성능 프로파일링", 본문, 라벨 "enhancement"를 입력하고 생성한다
  Then  GitHub에 이슈가 생성된다
  And   생성된 이슈 번호가 MC 태스크 메타에 연결된다

Scenario: API 오류 시 draft 보존
  Given 이슈 생성 API 호출이 실패한다
  When  오류가 발생한다
  Then  입력한 제목·본문이 draft로 로컬 보존된다
  And   "GitHub 연결 실패 — draft 저장됨" 알림이 표시된다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-GH-02-01 | AC-1 | 이슈 생성 + 메타 연결 | 통합 | P1 |
| TC-GH-02-02 | AC-2 | 오류 시 draft 보존 | 통합 | P1 |

---

## FR-INT-GCAL-01: Google Calendar 이벤트 읽기·표시 (V1.0)

**한 줄**: Google Calendar 이벤트를 30분 간격으로 폴링하여 Today's Flow · Calendar 뷰에 표시한다. `[iet03]`
**비즈니스 가치**: 별도 앱 전환 없이 MC 안에서 당일 Google 일정 파악. `[iet03]`

### 처리 흐름

```
1. APScheduler (integrations 서비스) 30분 간격 트리거
2. Google Calendar API로 현재 날짜 ±7일 이벤트 조회
   └─ OAuth: secret-bridge의 MC_GOOGLE_OAUTH 키 사용
3. gcal_cache 테이블 upsert (gcal_event_id 기준 dedup)
   ├─ mc_status = 'done'인 기존 항목 → 덮어쓰지 않음 (BR-GCAL-03)
   └─ 신규·변경 항목만 갱신
4. SC-01 Today's Flow + SC-13 Calendar 뷰에 Google 뱃지로 표시
실패: 재시도 1회 후 무시, 마지막 성공 캐시 유지
```

### Business Rules

| BR-ID | IF | THEN | 출처 |
|-------|----|------|------|
| BR-GCAL-01 | GCal 이벤트가 MC 항목과 동일 시간대에 존재 | Today's Flow에 Google 뱃지(🗓)와 함께 별도 행으로 표시 | `[iet03]` |
| BR-GCAL-02 | GCal API 호출 실패 (network / OAuth 만료) | 마지막 캐시 유지, UI에 "GCal 동기화 오류" 소형 아이콘 표시 | `[추론]` |
| BR-GCAL-03 | gcal_cache.mc_status = 'done'인 항목 재폴링 | 해당 행의 mc_status 변경 없이 title/time만 갱신 | `[추론]` |
| BR-GCAL-04 | GCal 이벤트가 Google에서 삭제됨 | gcal_cache 행 soft-delete (visible=0). MC에서 제거 | `[추론]` |

### Acceptance Criteria

```gherkin
Scenario: 오늘 GCal 이벤트 Today's Flow 표시
  Given Google Calendar에 "팀 스탠드업" 이벤트 (오전 10시)가 존재한다
  When  폴링 사이클이 완료된다
  Then  SC-01 Today's Flow에 🗓 뱃지와 함께 "팀 스탠드업 10:00" 행이 표시된다

Scenario: Calendar 뷰 GCal 이벤트 표시
  Given gcal_cache에 이번 주 이벤트 5개가 저장되어 있다
  When  SC-13 Calendar 뷰 (week 모드)를 연다
  Then  해당 5개 이벤트가 날짜·시간에 맞게 Google 뱃지로 표시된다

Scenario: OAuth 만료 시 오류 표시
  Given MC_GOOGLE_OAUTH 토큰이 만료되었다
  When  폴링 사이클이 실행된다
  Then  Today's Flow에 기존 캐시 이벤트는 유지되고, "GCal 동기화 오류" 아이콘이 표시된다
  And   SC-10 설정 화면에 재인증 안내가 노출된다

Scenario: GCal 삭제 이벤트 처리
  Given gcal_cache에 있는 이벤트가 Google에서 삭제되었다
  When  다음 폴링 사이클이 실행된다
  Then  해당 이벤트가 MC 뷰에서 사라진다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-GCAL-01-01 | AC-1 | 이벤트 캐시 + Today's Flow 표시 | 통합 | P0 |
| TC-GCAL-01-02 | AC-2 | Calendar 뷰 week 모드 표시 | 통합 | P1 |
| TC-GCAL-01-03 | AC-3 | OAuth 만료 오류 처리 | 통합 | P1 |
| TC-GCAL-01-04 | AC-4 | 삭제 이벤트 soft-delete | 통합 | P1 |

---

## FR-INT-GCAL-02: Google Calendar 이벤트 완료 표시 (V1.0)

**한 줄**: GCal 이벤트를 MC에서 완료 처리한다. Google Calendar에는 쓰지 않는다. `[iet03]`

### Business Rules

| BR-ID | IF | THEN | 출처 |
|-------|----|------|------|
| BR-GCAL-05 | 사용자가 GCal 이벤트의 "완료" 버튼을 클릭 | gcal_cache.mc_status = 'done' 저장. GCal API 쓰기 없음 | `[iet03]` |
| BR-GCAL-06 | mc_status = 'done'인 항목이 다음 폴링에서 재조회됨 | mc_status는 유지. title/time만 갱신 (BR-GCAL-03 연계) | `[추론]` |
| BR-GCAL-07 | mc_status = 'done'인 항목의 표시 | Today's Flow에서 취소선 + 흐린 처리. 필터 "완료 숨김" 적용 가능 | `[추론]` |

### Acceptance Criteria

```gherkin
Scenario: GCal 이벤트 완료 처리
  Given Today's Flow에 GCal 이벤트 "조회 미팅"이 표시되어 있다
  When  "완료" 버튼을 클릭한다
  Then  gcal_cache.mc_status가 'done'으로 저장된다
  And   Google Calendar의 해당 이벤트 상태는 변경되지 않는다
  And   Today's Flow에서 취소선 처리된다

Scenario: 완료 후 재폴링 시 상태 유지
  Given gcal_cache에 mc_status='done'인 이벤트가 있다
  When  다음 30분 폴링 사이클이 실행된다
  Then  mc_status는 'done'으로 유지되고, 이벤트 제목·시간만 최신값으로 갱신된다

Scenario: 완료 취소 (undo)
  Given GCal 이벤트가 완료 처리되어 취소선으로 표시된다
  When  완료 취소 버튼을 클릭한다
  Then  gcal_cache.mc_status가 null로 복원된다
  And   Today's Flow에서 정상 표시된다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-GCAL-02-01 | AC-1 | mc_status 저장 + GCal 미변경 | 통합 | P0 |
| TC-GCAL-02-02 | AC-2 | 재폴링 후 mc_status 유지 | 통합 | P1 |
| TC-GCAL-02-03 | AC-3 | 완료 취소 | 단위 | P2 |

---

## FR-INT-DR-01~04: Google Drive Cold tier 아카이브 (V1.2)

> **V1.2 항목 — V1.0에서 구현하지 않음.**

**한 줄**: 아카이브된 프로젝트 .md를 Google Drive에 업로드하고 로컬에서 삭제. 메타는 SQLite에 보존. `[iet03]`

### FR-INT-DR-01: 아카이브 업로드

```gherkin
Scenario: 아카이브 정상 처리 (V1.2)
  Given 프로젝트 "2026 Q1 리뷰"가 archived 상태로 전환된다
  When  Drive 업로드를 실행한다
  Then  MC/archive/2026-Q1-리뷰.md가 Drive에 업로드된다
  And   업로드 성공 확인 후에만 로컬 .md가 삭제된다 (BR-COLD-01/02)

Scenario: 업로드 실패 → 로컬 유지
  Given Drive 업로드가 네트워크 오류로 실패한다
  When  실패 감지 시
  Then  로컬 .md 파일이 삭제되지 않는다 (BR-COLD-01)
```

### FR-INT-DR-03: Cold 항목 검색

```gherkin
Scenario: Cold 항목 검색 가능
  Given 프로젝트가 Cold tier로 이동했다
  When  해당 프로젝트의 키워드로 검색한다
  Then  Cold 항목이 검색 결과에 표시된다 (브라운 뱃지 "(아카이브)")
  And   본문 내용 없이 메타데이터 기준 결과가 표시된다 (BR-COLD-03)
```

### FR-INT-DR-04: 재활성화

```gherkin
Scenario: Cold 항목 재활성화 (V1.2)
  Given Cold tier 항목의 컨텍스트 패널이 열려 있다
  When  "Drive에서 불러오기" 버튼을 클릭한다
  Then  Drive에서 .md 파일이 다운로드된다
  And   다운로드 완료 후 SQLite file_location이 'hot'으로 변경된다 (BR-COLD-04)
```

---

## Change Log

| 버전 | 날짜 | 변경 내용 | 변경자 |
|------|------|----------|--------|
| 1.0 | 2026-04-27 | 최초 작성 | BA Writer v1.0 |
