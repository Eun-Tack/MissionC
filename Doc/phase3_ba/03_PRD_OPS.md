# PRD — 운영성 (OPS): Inbox · Diagnostics · Alerts · Credentials

> 모듈: FR-INBOX-01, FR-DIAG-01, FR-NOTIFY-CTR-01, FR-SET-CRED-01
> 우선순위: Must (V1.0 출하 필수, 코덱스 외부 검토 2026-04-28에서 부재 지적)
> 작성: 2026-05-04 | BA Writer v1.0 (Phase 4 v1.1 보충)
> 인풋: [Screen_Spec_Addendum](../phase4_design/Screen_Spec_Addendum.md), [Traceability_Matrix](../phase4_design/Traceability_Matrix.md), [ADR-005](../phase4_design/ADR/ADR-005_Secret_Storage_Policy.md), [ADR-006](../phase4_design/ADR/ADR-006_Background_Execution_Model.md)

---

## 본 모듈 추가 배경

Phase 3 BA 1차 작성 시 운영 도구로서의 4가지 핵심 컴포넌트가 누락됐다 — Inbox(triage), Diagnostics(가시성), Alerts(복구), Credentials(보안). 코덱스 외부 검토에서 "운영 도구가 안정해지려면 화면 수보다 신뢰성 우선"으로 지적되어 본 모듈로 PRD 본문 보강한다.

---

## FR-INBOX-01: Capture Inbox (통합 미확정 큐)

**한 줄**: Telegram·음성·Quick Capture 등 외부 입력을 수락 전 한 큐에 모아 사용자가 일괄 검수·확정한다. `[iet03][코덱스 검토]`
**비즈니스 가치**: 다양한 채널 입력을 검증 없이 items에 직행시키면 메인 Today's Flow가 오염된다. Inbox 경유로 신뢰도 0.8 미만 입력은 사용자 손에서 끝낸다. `[iet03]`

### AS-IS → TO-BE

| 구분 | 내용 | 출처 |
|------|------|------|
| AS-IS | tg_inbound 테이블만 있고 사용자 검수 화면 부재 | `[Phase 4 v1.0]` |
| TO-BE | capture_inbox 통합 테이블 + SC-09 triage 화면 | `[코덱스 검토]` |
| 변경 유형 | 신규(중) | |

### 입력 / 라우팅 규칙

| 채널 | Inbox 경유 조건 | 즉시 items 직행 조건 |
|------|---------------|------------------|
| Telegram (FR-INT-TG-01) | 항상 | 없음 |
| Voice (FR-AI-VOICE) | confidence < 0.8 | confidence ≥ 0.8 |
| Quick Capture (FR-CAP-01) | 사용자 설정 (기본: AI 자동분류 신뢰도 < 0.8) | 명시 입력(`#태그`/시간/타입) 포함 |
| Gmail (V1.1) | 항상 | 없음 |

### 처리 흐름

```
1. 외부 입력 수신 → capture_inbox INSERT (status='pending')
2. ai-worker가 비동기로 suggested_type/suggested_tags 분석
3. 사용자가 SC-09 진입 → Inbox 목록 표시
4. 항목별 [a 수락] / [r 거부] / [t 태그수정]
   - 수락: items INSERT + capture_inbox.status='accepted', accepted_item_id 설정
   - 거부: capture_inbox.status='rejected'
5. 14일 미처리 → status='expired' (자동 폐기 안 함)
```

### Acceptance Criteria

```gherkin
Scenario: Telegram 메시지 Inbox 진입
  Given Telegram Bot이 사용자로부터 텍스트 메시지를 수신한다
  When  integrations 컨테이너가 메시지를 처리한다
  Then  capture_inbox 테이블에 status='pending'으로 INSERT된다
  And   ai-worker가 suggested_type, suggested_tags를 분석한다
  And   SC-09 Inbox 화면에 5초 이내 표시된다

Scenario: Voice 신뢰도 낮을 때 Inbox 우회
  Given 사용자가 음성 입력을 한다 (confidence=0.65)
  When  Whisper STT 결과를 받는다
  Then  items 직행이 아닌 capture_inbox로 라우팅된다
  And   raw_payload에 confidence=0.65가 저장된다

Scenario: 단축키 수락
  Given Inbox 화면에 pending 항목이 있다
  When  사용자가 항목 선택 후 'a' 키를 누른다
  Then  items 테이블에 새 행이 생성되고
  And   capture_inbox.status='accepted', accepted_item_id가 설정된다
  And   해당 항목이 Inbox 목록에서 사라진다

Scenario: 14일 만료
  Given received_at이 14일 전인 pending 항목이 있다
  When  자정 정리 작업이 실행된다
  Then  status가 'expired'로 변경된다
  And   화면 별도 탭 "오래됨"에 표시된다 (자동 삭제 안 함)
```

### 비즈니스 규칙

| BR-ID | 규칙 | 출처 |
|-------|------|------|
| BR-INBOX-01 | 외부 capture는 inbox 경유. Quick Capture는 신뢰도/명시성 기반 분기. | `[코덱스 검토]` |
| BR-INBOX-02 | pending 14일 → expired. 자동 삭제 금지. | `[iet03]` |
| BR-INBOX-03 | 수락 시 items 생성 + capture_inbox.accepted_item_id 양방향 추적. raw_text 영구 보존. | `[iet03]` |
| BR-INBOX-04 | 거부된 항목은 30일 후 자동 삭제. | `[iet03]` |

### 테스트 케이스

| TC-ID | 연결 AC | 시나리오 | 입력 | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|------|---------|
| TC-INBOX-01-01 | AC-1 | TG 메시지 라우팅 | "회의 7시" TG | capture_inbox 1행, 5s 내 SC-09 표시 | E2E | P1 |
| TC-INBOX-01-02 | AC-2 | Voice 저신뢰 | conf=0.65 | inbox 진입, raw_payload에 conf 보존 | 통합 | P1 |
| TC-INBOX-01-03 | AC-3 | 'a' 단축키 | pending 1건 | items INSERT + status=accepted | 단위 | P1 |
| TC-INBOX-01-04 | AC-4 | 14일 만료 | received_at=15일 전 | status=expired | 단위 | P2 |

### NFR

| 항목 | 값 |
|------|---|
| Inbox 표시 지연 | ≤ 5초 (외부 입력 → SC-09) |
| 단축키 응답 | ≤ 100ms |
| pending 누적 한도 | 1000건 (초과 시 사용자 경고) |

### Edge Cases

| 케이스 | 처리 |
|------|------|
| ai-worker 다운으로 suggested_type 분석 실패 | suggested_type=NULL, 사용자 직접 선택 드롭다운 표시 |
| TG 동일 메시지 중복 수신 | tg_message_id UNIQUE 체크, 중복 무시 |
| inbox에서 수락 직후 사용자가 items 삭제 | capture_inbox.accepted_item_id를 NULL로 (FK ON DELETE SET NULL) |

---

## FR-DIAG-01: Diagnostics / Worker Status

**한 줄**: Tier 1·2 워커, DB 통계, 최근 이벤트를 한 화면에서 확인한다. `[iet03][코덱스 검토]`
**비즈니스 가치**: "왜 검색 안 됨?", "왜 알림 안 옴?" 같은 운영 질문에 즉답 가능. 1인 도구는 디버깅 도구 부재 시 유지비용 폭증. `[iet03]`

### 입력 / 데이터 소스

| 데이터 | 소스 |
|------|------|
| ai-worker 상태 | `GET http://localhost:8001/health` |
| secret-bridge 상태 | `GET http://localhost:9999/health` |
| notifier-daemon 상태 | settings.worker_status_notifier + last_seen |
| Docker 컨테이너 상태 | `GET /diag` 내부에서 `docker ps` 또는 컨테이너 self-report |
| TG polling 마지막 시각 | settings.worker_status_tg_polling |
| GH sync 상태 + Rate Limit | github_cache.fetched_at MAX + settings |
| watchdog 통계 | file_index 24h 이벤트 카운트 |
| DB 통계 | `SELECT COUNT(*) FROM items, item_vectors` |
| 최근 이벤트 | notification_events + retry_queue 최근 20건 |

### 처리 흐름

```
1. 사용자 SC-10 진입
2. core-api /diag 엔드포인트 → 위 데이터 수집 (병렬)
   - 외부 워커는 timeout 1s, 미응답 시 'unknown'
3. 결과 렌더 + 자동 새로고침 (10초 간격)
4. 사용자 액션 버튼: [재시작 모든 워커] [모델 재로드] [DB VACUUM]
```

### Acceptance Criteria

```gherkin
Scenario: 모든 워커 정상
  Given Tier 1·2 워커가 모두 응답한다
  When  사용자가 SC-10을 연다
  Then  각 워커 옆에 ● ok 표시가 보인다
  And   응답 지연(예: ai-worker 2.1s)이 함께 표시된다

Scenario: ai-worker 다운
  Given ai-worker /health에 1초 내 응답 없음
  When  /diag가 실행된다
  Then  ai-worker 옆에 ● down (red) 표시
  And   "재시작" 버튼이 활성화된다
  And   페이지 상단에 "AI 검색·STT 비활성" 배너가 표시된다

Scenario: GH Rate Limit 근접
  Given github API 잔여 100건 미만
  When  /diag가 실행된다
  Then  rate=NN/5000 옆에 ⚠ 경고 색상이 표시된다
```

### 비즈니스 규칙

| BR-ID | 규칙 | 출처 |
|-------|------|------|
| BR-DIAG-01 | 외부 워커 health 체크 timeout 1초. 미응답 시 'unknown' 표시 (장애 단정 금지). | `[iet03]` |
| BR-DIAG-02 | 사용자 트리거 액션(재시작/VACUUM)은 audit성 로그를 notification_events에 남긴다. | `[추론]` |
| BR-DIAG-03 | SC-10 자동 새로고침 10초. 사용자가 탭 비활성화 시 멈춤. | `[추론]` |

### 테스트 케이스

| TC-ID | 연결 AC | 시나리오 | 입력 | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|------|---------|
| TC-DIAG-01-01 | AC-1 | 정상 표시 | 모든 워커 up | 6개 ● ok + 지연 표시 | E2E | P1 |
| TC-DIAG-01-02 | AC-2 | ai-worker 다운 | 8001 미응답 | ● down + 재시작 버튼 | 통합 | P1 |
| TC-DIAG-01-03 | AC-3 | Rate Limit | gh 잔여 50 | ⚠ 색상 표시 | 단위 | P2 |

### NFR

| 항목 | 값 |
|------|---|
| /diag 응답 시간 | ≤ 1.5s (병렬 health 체크) |
| 자동 새로고침 부하 | 10초 1회, GET only |

---

## FR-NOTIFY-CTR-01: Notification & Retry Center (Alerts)

**한 줄**: 모든 알림(OS Toast/TG/UI)과 실패 재시도를 한 곳에 누적·재확인한다. `[iet03][코덱스 검토]`
**비즈니스 가치**: 토스트가 휘발되면 운영 도구는 신뢰를 잃는다. 실패 알림은 사용자 손이 닿는 곳에 누적되어야 한다. `[iet03]`

### 입력 / 처리 흐름

```
1. 모든 알림 발송 시 notification_events 동시 기록 (BR-NOTIFY-CTR-01)
2. 외부 통합(TG/GH/Drive) 발송 실패 시 retry_queue INSERT
3. SC-11 진입 시 두 테이블 JOIN 표시
   - 미해결 retry_queue 우선 (액션 버튼)
   - 일반 알림은 24h 이내 표시
4. 사용자 액션:
   - [재시도] → retry_queue.next_attempt_at = now
   - [건너뛰기] → resolved=1
   - [토큰 재등록] → SC-08-Cred로 이동
   - [dismiss] → notification_events.dismissed=1
```

### 재시도 백오프 (BR-RETRY-01)

```
attempts=1 → 1분 후
attempts=2 → 5분 후
attempts=3 → 30분 후
attempts=4 → 2시간 후
attempts=5 → 사용자 개입 요청 (UI 배너 + notification_events 'retry_failed')
```

### Acceptance Criteria

```gherkin
Scenario: TG 발송 실패 재시도
  Given Telegram /sendMessage가 401을 반환한다
  When  integrations가 응답을 받는다
  Then  retry_queue에 INSERT (target='telegram', attempts=1, next_attempt_at=now+1m)
  And   SC-11에 ⚠ 항목으로 표시된다

Scenario: 사용자 재시도 버튼
  Given 미해결 retry_queue 항목이 있다
  When  사용자가 [재시도] 버튼을 누른다
  Then  next_attempt_at = now로 갱신
  And   integrations가 즉시 재실행

Scenario: 5회 실패 후 개입 요청
  Given retry_queue.attempts=5
  When  마지막 시도가 실패한다
  Then  notification_events에 kind='retry_failed' 행 생성
  And   SC-11 상단에 빨간 배너 + "토큰 재등록" 가이드 표시

Scenario: dismiss 후 보존
  Given notification_events 항목이 있다
  When  사용자가 dismiss 버튼을 누른다
  Then  dismissed=1로 갱신되지만 행은 보존된다
  And   SC-10 Diagnostics에서는 여전히 24h 이벤트로 카운트된다
```

### 비즈니스 규칙

| BR-ID | 규칙 | 출처 |
|-------|------|------|
| BR-NOTIFY-CTR-01 | 모든 토스트는 notification_events에 동시 기록. 사용자 dismiss 전까지 SC-11에 표시. | `[코덱스 검토]` |
| BR-RETRY-01 | 지수 백오프 1m/5m/30m/2h/실패. 최대 5회. | `[iet03]` |
| BR-RETRY-02 | 5회 실패 시 자동 재시도 중단, 사용자 개입 요청. | `[iet03]` |
| BR-RETRY-03 | 사용자가 [건너뛰기] 선택 시 resolved=1. 같은 페이로드 재발생 시 새 row. | `[추론]` |

### 테스트 케이스

| TC-ID | 연결 AC | 시나리오 | 입력 | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|------|---------|
| TC-NCTR-01-01 | AC-1 | TG 401 | bot 토큰 만료 | retry_queue 1행, attempts=1 | 통합 | P1 |
| TC-NCTR-01-02 | AC-2 | 재시도 버튼 | 미해결 1건 | next_attempt_at=now, 즉시 실행 | E2E | P1 |
| TC-NCTR-01-03 | AC-3 | 5회 실패 | attempts=5 | retry_failed 이벤트 + 배너 | 통합 | P1 |
| TC-NCTR-01-04 | AC-4 | dismiss | dismissed=1 | UI 사라짐, 행 보존 | 단위 | P2 |

### NFR

| 항목 | 값 |
|------|---|
| 재시도 지연 정확도 | ±10초 |
| SC-11 렌더 | ≤ 500ms (최근 50건) |

---

## FR-SET-CRED-01: Credential Manager (SC-08-Cred)

**한 줄**: 토큰을 등록·검증·삭제하되 평문은 절대 화면에 표시하지 않는다. `[iet03][ADR-005]`
**비즈니스 가치**: ADR-005 시크릿 정책의 사용자 접점. 토큰을 등록만 하고 끝나는 것이 아니라 검증·갱신·연결 상태가 항상 보여야 운영 신뢰가 생긴다. `[iet03]`

### 입력

| 필드 | 타입 | 필수 | 유효성 |
|------|------|------|--------|
| keyring target | enum (MC_GH_PAT / MC_TG_BOT_TOKEN / MC_GOOGLE_OAUTH) | Y | ADR-005 명시 3종만 |
| 토큰 값 | string | Y (등록 시) | 입력 후 즉시 마스킹, 화면 어디에도 표시 안 함 |

### 처리 흐름

```
[등록]
1. 사용자 SC-08-Cred → [등록] 버튼
2. 모달에서 토큰 값 입력 (마스킹된 input)
3. POST /api/cred/{key}/set → secret-bridge 또는 keyring 직접
4. 즉시 검증 호출 (아래 [검증] 흐름)
5. 결과: 등록됨 ● 또는 검증 실패 ○

[검증]
1. POST /api/cred/{key}/verify
2. 키별 read API 호출:
   - MC_GH_PAT       → GET https://api.github.com/user
   - MC_TG_BOT_TOKEN → GET https://api.telegram.org/bot{token}/getMe
   - MC_GOOGLE_OAUTH → GET https://www.googleapis.com/userinfo/v2/me
3. 성공: settings.cred_{key}_last_verify_at = now, scope/bot username 갱신
4. 실패: SC-08-Cred에 ○ 미검증 + 에러 사유

[삭제]
1. 확인 다이얼로그
2. keyring.delete_password() + settings 정리
3. 관련 워커 자동 재시작 (예: TG token 삭제 → integrations TG polling 중지)
```

### Acceptance Criteria

```gherkin
Scenario: GitHub PAT 등록 + 검증
  Given 사용자가 SC-08-Cred를 연다
  When  [등록] 후 유효한 PAT 입력
  Then  keyring.set_password("MC_GH_PAT", "iet03", value) 호출
  And   GET /user 검증 성공
  And   화면에 ● 등록됨 + scope (repo, read:org) + 마지막 검증 시각 표시
  And   토큰 값은 화면 어디에도 표시되지 않는다

Scenario: 잘못된 토큰
  Given 사용자가 잘못된 PAT를 입력한다
  When  검증 호출 시 401
  Then  keyring 등록은 유지되지만
  And   SC-08-Cred에 ○ 미검증 + "401 Unauthorized" 표시
  And   사용자가 [재등록] 또는 [삭제] 가능

Scenario: 토큰 삭제
  Given MC_TG_BOT_TOKEN이 등록되어 있다
  When  사용자가 [삭제] 후 확인
  Then  keyring에서 제거
  And   settings.worker_status_tg_polling = 'stopped'
  And   integrations TG polling 워커가 중지된다
```

### 비즈니스 규칙

| BR-ID | 규칙 | 출처 |
|-------|------|------|
| BR-SET-CRED-01 | 토큰 평문 절대 화면 표시 금지. 등록 여부 + 검증 시각만. | `[ADR-005][iet03]` |
| BR-SET-CRED-02 | "검증" = 해당 API read 호출 1회. 쓰기 호출 금지. | `[추론]` |
| BR-SET-CRED-03 | 삭제 시 keyring + settings + 관련 워커 일괄 정리. | `[iet03]` |
| BR-SET-CRED-04 | secret-bridge 미동작 시 SC-08-Cred는 read-only로 표시 (등록·삭제 비활성). | `[ADR-005]` |
| BR-SET-CRED-05 | 검증 실패한 토큰은 24h 후 자동 재검증 (워커가 1회 시도). | `[iet03]` |

### 테스트 케이스

| TC-ID | 연결 AC | 시나리오 | 입력 | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|------|---------|
| TC-CRED-01-01 | AC-1 | 정상 등록·검증 | 유효 PAT | ●등록 + scope 표시, 토큰 화면 미표시 | E2E | P1 |
| TC-CRED-01-02 | AC-2 | 401 토큰 | 만료 PAT | ○미검증 + 401 표시 | 통합 | P1 |
| TC-CRED-01-03 | AC-3 | 삭제 cascade | TG 삭제 | keyring 제거 + polling 중지 | E2E | P1 |
| TC-CRED-01-04 | — | secret-bridge 다운 | 9999 미응답 | SC-08-Cred read-only 모드 | 통합 | P2 |
| TC-CRED-01-05 | — | 토큰 화면 노출 시도 | 개발자 도구로 GET /api/cred/{key} | 응답에 토큰 값 포함 안 함 (404 또는 metadata만) | 보안 | P0 |

### NFR

| 항목 | 값 |
|------|---|
| 검증 응답 | ≤ 3초 |
| 평문 노출 | 0건 (P0 보안 게이트) |

### Edge Cases

| 케이스 | 처리 |
|------|------|
| Windows DPAPI 잠김 (사용자 비밀번호 변경 직후) | secret-bridge가 401 반환 → SC-08-Cred에 "Windows 재로그인 필요" 안내 |
| keyring 라이브러리 백엔드 변경 | settings.keyring_backend 기록, 변경 시 마이그레이션 가이드 |

---

## 모듈 간 의존성

```
FR-INBOX-01 ─── 입력 ──→ FR-AI-VOICE, FR-INT-TG-01, FR-CAP-01
FR-DIAG-01  ─── 표시 ──→ FR-NOTIFY-CTR-01, FR-INT-GH-01, FR-AI-* 워커
FR-NOTIFY-CTR-01 ─ 기록 ─→ FR-NOTIFY-01 (OS Toast), FR-INT-TG-02
FR-SET-CRED-01 ─ 차단 ──→ FR-INT-TG-*, FR-INT-GH-* (토큰 미등록 시 워커 idle)
```

---

## Change Log

| 버전 | 날짜 | 변경 |
|------|------|------|
| 1.0 | 2026-05-04 | 최초 작성 — Phase 4 v1.1 코덱스 검토 반영, OQ-D-02 해결 |
