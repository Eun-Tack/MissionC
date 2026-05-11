# BR / AC — Radial Command Palette

> **버전**: V1.5 | **연관 FR**: FR-RADIAL-01~05
> **AI_SDLC 글로벌 규칙**: BR = IF-THEN, AC = Gherkin (정상/예외/경계 ≥ 3)

---

## A. Business Rules (IF-THEN)

### A.1 진입 / 종료 규칙

| ID | IF | THEN | 근거 |
|----|----|------|------|
| BR-RADIAL-01 | 사용자가 `Cmd+K` (또는 `Ctrl+K`) 를 누르고 현재 포커스가 `<input>`/`<textarea>` 가 아니다 | radial 진입 | FR-RADIAL-01 |
| BR-RADIAL-02 | 사용자가 `Cmd+K` 를 누르고 현재 포커스가 `<input>`/`<textarea>` 이다 | 그래도 radial 진입 (포커스 blur 후) — `/` 만 차단 | FR-RADIAL-05 |
| BR-RADIAL-03 | radial 이 열린 상태에서 `Esc` | radial 닫기 (모션 100ms) | FR-RADIAL-02 |
| BR-RADIAL-04 | radial 이 열린 상태에서 외부 영역 클릭 | radial 닫기 | FR-RADIAL-02 |
| BR-RADIAL-05 | radial 이 열린 상태에서 동일 트리거 (`Cmd+K`) 재입력 | radial 닫기 (토글 동작) | FR-RADIAL-01 |

### A.2 슬라이스 선택 / 실행 규칙

| ID | IF | THEN | 근거 |
|----|----|------|------|
| BR-RADIAL-10 | 화살표 키 입력 | 해당 방향 슬라이스 강조 + 중앙 hub 라벨 변경 | FR-RADIAL-02 |
| BR-RADIAL-11 | 강조된 슬라이스가 있을 때 `Enter` | 강조 슬라이스 액션 실행 | FR-RADIAL-02 |
| BR-RADIAL-12 | 단일 문자 단축키 (`c/s/t/x/r/y/p/v`) | 해당 슬라이스 즉시 실행 (강조 단계 생략) | FR-RADIAL-02 |
| BR-RADIAL-13 | 슬라이스 클릭 (마우스) | 해당 슬라이스 액션 실행 | FR-RADIAL-02 |
| BR-RADIAL-14 | 비활성 슬라이스 선택 시도 | 무시 (시각: 회색 + shake 모션 200ms) | BR-RADIAL-21 |

### A.3 컨텍스트 인지 규칙 (FR-RADIAL-03)

| ID | IF | THEN | 근거 |
|----|----|------|------|
| BR-RADIAL-20 | 현재 URL 이 `/project/{id}` 패턴 | 캡처 슬라이스의 액션 payload 에 `project_id` 자동 포함 | FR-RADIAL-03 |
| BR-RADIAL-21 | 현재 URL 이 `/partial/context/*` 또는 컨텍스트 패널이 이미 펼쳐진 상태 | 컨텍스트 슬라이스 비활성 (gray) | FR-RADIAL-03 |
| BR-RADIAL-22 | 현재 시각 < 12:00 | 회고 슬라이스 액션 = `/morning` | FR-RADIAL-03 |
| BR-RADIAL-23 | 현재 시각 ≥ 12:00 | 회고 슬라이스 액션 = `/evening` | FR-RADIAL-03 |
| BR-RADIAL-24 | 현재 URL 이 `/inbox` | 캡처 슬라이스 라벨 = "분류로 점프" + 액션 = inbox 첫 카드 포커스 | FR-RADIAL-03 |
| BR-RADIAL-25 | 마이크 권한이 거부된 상태 | 음성 슬라이스 비활성 + tooltip "마이크 권한 필요" | FR-RADIAL-04 |

### A.4 InlineForm / Modal 동작 규칙

| ID | IF | THEN | 근거 |
|----|----|------|------|
| BR-RADIAL-30 | 캡처 슬라이스 실행 | radial 외곽 유지 + 중앙 hub 가 input 으로 morph | Screen_Spec § 5.3 |
| BR-RADIAL-31 | InlineForm 제출 (`Enter`) 시 빈 입력 | submit 무시 + 빨간 outline 깜박임 200ms | UX |
| BR-RADIAL-32 | InlineForm 제출 성공 | radial 닫기 + toast "✓ 저장됨" 1.5초 표시 | UX |
| BR-RADIAL-33 | 검색 슬라이스에서 입력 ≥ 2 글자 | 250ms debounce 후 `/api/cmdk` 호출 | 성능 |
| BR-RADIAL-34 | 음성 슬라이스 실행 | radial 닫기 + Voice 모달 즉시 표시 (FR-AI-VOICE 재사용) | 통합 |

### A.5 성능 / 안전 규칙

| ID | IF | THEN | 근거 |
|----|----|------|------|
| BR-RADIAL-40 | radial 진입 ~ 표시 시간이 100ms 초과 | 콘솔 warn 로그 + telemetry 기록 (선택) | NFR |
| BR-RADIAL-41 | `prefers-reduced-motion: reduce` | 스프링 모션 비활성, 즉시 페이드 (모션 0ms) | 접근성 |
| BR-RADIAL-42 | 5초 동안 입력 없음 | radial 자동 닫지 않음 (사용자 의도 존중) | UX |

---

## B. Acceptance Criteria (Gherkin)

### B.1 정상 시나리오

#### AC-RADIAL-01: 키보드만으로 캡처 진입
```gherkin
Given 사용자가 Today 페이지(`/`) 에 있다
And 키보드 포커스가 어디에도 없다
When 사용자가 `Cmd+K` 를 누른다
Then radial 이 100ms 이내에 표시된다
When 사용자가 `↑` 화살표를 누른다
Then 12 시 슬라이스 (캡처) 가 강조된다
And 중앙 hub 에 "캡처" 라벨이 24px 로 표시된다
When 사용자가 `Enter` 를 누른다
Then 중앙 hub 가 input 으로 morph 된다 (200ms)
When 사용자가 "회의 정리하기" 를 입력하고 `Enter` 를 누른다
Then `/api/items` 에 type=task, title="회의 정리하기" 로 POST 된다
And radial 이 닫힌다 (100ms)
And toast "✓ 저장됨" 이 1.5초 표시된다
```

#### AC-RADIAL-02: 단일 문자 단축키로 즉시 실행
```gherkin
Given 사용자가 임의의 페이지에 있다
When 사용자가 `Cmd+K` 를 누른다
And `t` 를 누른다 (오늘 보기 단축키)
Then radial 이 진입 직후 즉시 닫힌다
And 페이지가 `/` 로 라우팅된다
```

#### AC-RADIAL-03: 컨텍스트 인지 — 프로젝트 페이지에서 캡처
```gherkin
Given 사용자가 `/project/12` 페이지에 있다
When 사용자가 `Cmd+K → c` 를 누른다
Then 캡처 InlineForm 이 표시된다
When 사용자가 "API 문서 작성" 을 입력하고 `Enter`
Then POST `/api/items` 의 payload 에 `project_id=12` 가 자동 포함된다
And 항목이 프로젝트 12 에 자동 연결된다
```

### B.2 예외 시나리오

#### AC-RADIAL-10: 입력 필드 포커스 중 진입 — `/` 키
```gherkin
Given 사용자가 검색 페이지의 input 에 포커스를 두었다
When 사용자가 `/` 를 누른다
Then radial 이 진입하지 않는다 (입력으로 통과)
And input 에 "/" 가 입력된다
When 사용자가 `Cmd+K` 를 누른다
Then 입력 필드 포커스가 blur 되고 radial 이 진입한다
```

#### AC-RADIAL-11: 비활성 슬라이스 선택 — 음성 슬라이스 권한 거부
```gherkin
Given 브라우저가 마이크 권한을 거부했다
And radial 이 열려 있다
When 사용자가 `↖` 를 누른다 (음성 슬라이스)
Then 음성 슬라이스가 회색으로 표시된다
And tooltip "마이크 권한 필요" 가 슬라이스 위에 표시된다
When 사용자가 `Enter` 또는 클릭한다
Then shake 애니메이션이 200ms 재생된다
And 액션이 실행되지 않는다
And radial 은 열린 상태로 유지된다
```

#### AC-RADIAL-12: 빈 캡처 입력 제출
```gherkin
Given radial 의 캡처 InlineForm 이 활성 상태이다
And input 이 비어 있다
When 사용자가 `Enter` 를 누른다
Then submit 이 발생하지 않는다
And input 외곽선이 빨간색으로 200ms 깜박인다
And radial 은 InlineForm 상태로 유지된다
```

### B.3 경계 시나리오

#### AC-RADIAL-20: 회고 슬라이스 — 정오 경계
```gherkin
Given 시스템 시각이 11:59 이다
When 사용자가 `Cmd+K → r` 을 누른다
Then 페이지가 `/morning` 으로 라우팅된다
Given 시스템 시각이 12:00 이다
When 사용자가 `Cmd+K → r` 을 누른다
Then 페이지가 `/evening` 으로 라우팅된다
```

#### AC-RADIAL-21: 화살표 키 wrap-around
```gherkin
Given radial 이 열려 있고 12 시 슬라이스 (캡처) 가 강조되어 있다
When 사용자가 `↖` 를 누른다 (반시계 방향)
Then 10.5 시 슬라이스 (음성) 가 강조된다
When 사용자가 다시 `↖` 를 누른다
Then 9 시 슬라이스 (프로젝트) 가 강조된다
```

#### AC-RADIAL-22: `Cmd+K` 토글
```gherkin
Given 사용자가 Today 페이지에 있고 radial 이 닫혀 있다
When 사용자가 `Cmd+K` 를 누른다
Then radial 이 표시된다
When 사용자가 다시 `Cmd+K` 를 누른다
Then radial 이 닫힌다 (모션 100ms)
And 페이지 컨텍스트는 변경되지 않는다 (스크롤 위치, 포커스 등)
```

#### AC-RADIAL-23: 동시 트리거 — Cmd+K 누른 채 화살표
```gherkin
Given radial 이 닫혀 있다
When 사용자가 `Cmd+K` 를 누르고 손을 떼지 않은 채 0.05초 내에 `↑` 를 누른다
Then radial 이 진입하면서 12 시 슬라이스가 강조된 상태로 표시된다
And 중복 진입이 발생하지 않는다 (idempotent)
```

### B.4 회귀 / 통합 시나리오

#### AC-RADIAL-30: V1.0 기능 영향 0
```gherkin
Given V1.0 의 모든 페이지 (`/`, `/hierarchy`, `/calendar`, `/inbox`, `/settings`, `/search`, `/dashboard`, `/morning`, `/evening`) 가 있다
When V1.5 배포 후 각 페이지에 진입한다
Then 모든 페이지가 200 OK 로 로드된다
And 기존 페이지의 모든 인터랙션이 정상 동작한다
And radial 코드의 어떤 키 핸들러도 기존 페이지의 키 입력을 가로채지 않는다 (`Cmd+K` 와 `/` 제외)
```

#### AC-RADIAL-31: 프로젝트 페이지에서 캡처 → 자동 연결
```gherkin
Given 프로젝트 #12 가 존재하고 항목 0 개를 가진다
When 사용자가 `/project/12` 에 진입한다
And `Cmd+K → c → "테스트" → Enter` 시퀀스를 수행한다
Then DB 의 items 테이블에 새 row 가 생성된다
And item_projects 테이블에 `(new_item_id, 12)` row 가 생성된다
When 사용자가 페이지를 새로고침한다
Then 프로젝트 12 의 항목 목록에 "테스트" 가 표시된다
```

---

## C. AC 카운트 (Phase 6 R1-01 측정용)

| 카테고리 | 시나리오 수 |
|---------|------------|
| 정상 | 3 |
| 예외 | 3 |
| 경계 | 4 |
| 회귀/통합 | 2 |
| **총** | **12** |

각 시나리오 = 측정 단위. V1.5 종료 시 95% 이상 통과 (≥ 12 중 11 개) 가 게이트 조건.

---

## D. 자동 vs 수동 테스트 분류

| 시나리오 | 자동 (smoke) | 수동 (워크스루) |
|---------|--------------|-----------------|
| AC-RADIAL-01 정상 캡처 | △ (DOM 검증 가능) | ✓ (모션 / 시각 확인) |
| AC-RADIAL-02 단축키 라우팅 | ✓ | — |
| AC-RADIAL-03 컨텍스트 인지 | ✓ (POST payload 검증) | — |
| AC-RADIAL-10 입력 필드 통과 | ✓ | — |
| AC-RADIAL-11 권한 거부 슬라이스 | △ (mock 필요) | ✓ |
| AC-RADIAL-12 빈 제출 | ✓ | — |
| AC-RADIAL-20 정오 경계 | ✓ (시간 mock) | — |
| AC-RADIAL-21 wrap-around | ✓ | — |
| AC-RADIAL-22 토글 | ✓ | — |
| AC-RADIAL-23 동시 입력 | △ | ✓ |
| AC-RADIAL-30 V1.0 회귀 | ✓ (smoke 7 페이지) | — |
| AC-RADIAL-31 프로젝트 연결 | ✓ | — |

자동 가능: 9 / 부분 자동: 3 / 수동만: 0
