# PRD — 메모 (MEMO) + 프로젝트 (PROJ)

> 모듈: FR-MEMO-01~07, FR-PROJ-01~04
> 우선순위: Must (전체)
> 작성: 2026-04-27 | BA Writer v1.0
> v1.3 개정: 2026-05-04 — FR-PROJ-01~04 전면 재정의 (태그 기반 → 소속-사업-프로젝트 계층)
> v1.5 개정: 2026-05-06 — FR-MEMO-06 (Milkdown 블록 에디터), FR-MEMO-07 (Lifecycle + Morphing) 추가
> 메모 정의: 자유로운 사고의 단편(아직 task/schedule이 아닌 변수·고려사항·아이디어). 표준 .md로 저장되어 LocalDocsHub에서 즉시 조회 가능.

---

## FR-MEMO-01: 일자 .md 자동 생성·추가

**한 줄**: 메모 입력 시 `MC-Notes/inbox/YYYY/MM/DD.md`에 자동 추가한다. 정리 시 프로젝트 폴더로 이동. `[iet03]` (D7)
**비즈니스 가치**: .md 단일 원본 원칙(BR-MEMO-01)의 핵심 구현. 캡처 마찰을 줄이고, 분류는 사후에. `[iet03]`

> **D7 결정 (v1.5)**: 캡처 시점 = 무조건 `inbox/`로 들어감. 사용자가 메모를 검토하며 프로젝트/사업 폴더로 이동(드래그 또는 "프로젝트 연결" 액션). 이동 시 file_index의 path·project_id·stage_id가 트랜잭션으로 일괄 갱신 (ADR-010, FR-FILES-02 동일 메커니즘).

### AS-IS → TO-BE

| 구분 | 내용 | 출처 |
|------|------|------|
| AS-IS | 메모를 매번 파일 열어서 수동 추가 또는 클라우드 앱 의존 | `[iet03]` |
| TO-BE | MC에 메모 입력 → 당일 .md에 자동 추가, LocalDocsHub에서 즉시 확인 가능 | `[iet03]` |

### Acceptance Criteria

```gherkin
Scenario: 신규 메모 일자 파일 생성
  Given 오늘 날짜의 .md 파일이 없다
  When  메모를 입력하고 저장한다
  Then  MC-Notes/inbox/YYYY/MM/DD.md 파일이 생성된다
  And   메모 내용이 해당 파일에 추가된다

Scenario: 기존 일자 파일에 append
  Given 오늘 날짜의 .md 파일이 이미 존재한다
  When  새 메모를 입력하고 저장한다
  Then  기존 파일에 메모가 append된다 (파일 내용 유실 X)

Scenario: 자정 직전 입력
  Given 현재 시각이 23:59:30이다
  When  메모를 입력한다
  Then  오늘 날짜 파일에 저장된다 (다음 날 파일 X)

Scenario: 폴더 권한 없음
  Given MC-Notes 폴더에 쓰기 권한이 없다
  When  메모를 저장한다
  Then  "폴더 권한을 확인하세요" 안내 + 임시 큐에 보관된다
```

### 테스트 케이스

| TC-ID | 연결 AC | 시나리오 | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|---------|------|---------|
| TC-MEMO-01-01 | AC-1 | 신규 파일 생성 | .md 파일 생성 확인 | E2E | P0 |
| TC-MEMO-01-02 | AC-2 | Append | 파일 크기 증가, 기존 내용 보존 | 통합 | P0 |
| TC-MEMO-01-03 | AC-3 | 자정 경계 | 오늘 파일 저장 | 단위 | P1 |
| TC-MEMO-01-04 | AC-4 | 권한 오류 | 오류 안내 + 큐 보관 | E2E | P1 |

---

## FR-MEMO-02: 자유 명명 .md 생성

**한 줄**: 사용자가 직접 파일명을 지정하는 .md를 생성한다. `[추론]`

### Acceptance Criteria

```gherkin
Scenario: 정상 생성
  Given 사용자가 파일명 "프로젝트-정리"를 입력한다
  When  저장한다
  Then  MC-Notes/inbox/프로젝트-정리.md가 생성된다

Scenario: 동일 파일명 충돌
  Given "프로젝트-정리.md"가 이미 존재한다
  When  동일 이름으로 저장한다
  Then  "프로젝트-정리_1.md"로 자동 저장된다
```

---

## FR-MEMO-03: LocalDocsHub 연결 안내

**한 줄**: Settings에서 MC 노트 폴더 경로를 표시하고 복사 버튼을 제공한다. `[추론]`

### Acceptance Criteria

```gherkin
Scenario: 경로 복사
  Given Settings > LocalDocsHub 연결 항목이 열려 있다
  When  복사 버튼을 클릭한다
  Then  MC-Notes 폴더 경로가 클립보드에 복사된다
```

---

## FR-MEMO-04: 외부 편집 감지

**한 줄**: watchdog로 .md 파일 변경을 감지해 SQLite 인덱스를 자동 갱신한다. `[추론]`

### Acceptance Criteria

```gherkin
Scenario: 외부 편집 감지 및 인덱스 갱신
  Given VS Code에서 오늘 .md 파일을 편집하고 저장한다
  When  1.5초 디바운스 후
  Then  MC의 SQLite 인덱스와 벡터 인덱스가 갱신된다

Scenario: 외부 파일 삭제
  Given LocalDocsHub에서 .md 파일을 삭제한다
  When  watchdog가 감지한다
  Then  SQLite에서 해당 항목이 "결손" 마킹되고 알림이 표시된다

Scenario: 충돌 감지
  Given MC에서 파일 편집 중 외부에서 같은 파일이 변경된다
  When  MC 저장 시
  Then  충돌 알림이 표시되고 3옵션이 제공된다
```

---

## FR-MEMO-05: 메타 다중 매핑

**한 줄**: 하나의 .md 파일을 여러 태그·프로젝트에 동시 연결한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: 다중 태그 매핑
  Given 하나의 .md 파일이 있다
  When  태그 A, B, C를 동시에 매핑한다
  Then  SQLite mapping 테이블에 3개 row가 생성된다
  And   .md 파일 원본은 변경되지 않는다

Scenario: 태그 제거 시 .md 파일 유지
  Given .md 파일이 태그 A에 매핑되어 있다
  When  태그 A 매핑을 삭제한다
  Then  .md 파일은 삭제되지 않는다 (매핑만 제거)
```

---

## FR-MEMO-06: Milkdown 블록형 에디터 (V1.0, v1.5 신규)

**한 줄**: Notion 스타일 블록 에디터로 .md를 편집한다. 슬래시 커맨드, 블록 드래그, 인라인 체크박스 지원. `[iet03]` (D1)
**비즈니스 가치**: 노션 사용자의 손에 익은 편집 경험 + .md 표준 보존(LocalDocsHub 호환).

### 기술 결정 (D1)

| 항목 | 선택 | 이유 |
|------|-----|------|
| 라이브러리 | **Milkdown** (ProseMirror 기반) | 블록형 + .md 양방향 동기, 슬래시 커맨드 native |
| 저장 형식 | 표준 GitHub Flavored Markdown | LocalDocsHub·Drive·외부 도구 호환 |
| 커서·선택 동기화 | watchdog와 mtime 기반 충돌 감지 | FR-CONFLICT-01 재사용 |

### Acceptance Criteria

```gherkin
Scenario: 슬래시 커맨드로 블록 삽입
  Given 메모 편집 화면이 열려 있다
  When  /heading 입력 후 Enter를 누른다
  Then  H2 블록이 삽입되고 커서가 안에 위치한다

Scenario: 블록 드래그 재배치
  Given 메모에 3개 블록(텍스트·체크박스·코드)이 있다
  When  체크박스 블록의 그립을 드래그하여 맨 위로 이동한다
  Then  순서가 변경되고 .md 파일에 즉시 반영된다 (debounce 1.5s)

Scenario: 인라인 체크박스 토글
  Given 메모에 `- [ ] 작업 A` 체크박스 라인이 있다
  When  체크박스를 클릭한다
  Then  `- [x] 작업 A`로 변경되고 파일에 저장된다

Scenario: 표준 .md 보존
  Given Milkdown으로 메모를 편집·저장한다
  When  같은 파일을 LocalDocsHub에서 연다
  Then  표준 GFM 문법으로 정상 렌더된다 (Milkdown 전용 마크 X)
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-MEMO-06-01 | AC-1 | 슬래시 커맨드 작동 | E2E | P0 |
| TC-MEMO-06-02 | AC-2 | 블록 드래그 + .md 저장 | 통합 | P1 |
| TC-MEMO-06-03 | AC-3 | 체크박스 토글 | 단위 | P0 |
| TC-MEMO-06-04 | AC-4 | LocalDocsHub 호환 | E2E | P0 |

---

## FR-MEMO-07: Memo Lifecycle 시각화 + Memo→Task Morphing (V1.0, v1.5 신규)

**한 줄**: 메모의 진화(편집 횟수·시각) 시각화 + 메모를 task로 부드럽게 승격(morphing)한다. `[iet03]` (D6 ①②)
**비즈니스 가치**: 메모는 한 번에 완성되지 않음. 진화 흔적이 보이면 사고의 깊이가 시각화되고, task 승격 시 매끄러운 전환으로 인지 부담 감소.

### 두 가지 동작

**(A) Lifecycle 시각화**
- file_index.sha256 변경 횟수를 evolution_count로 카운트
- evolution_count ≥ 3인 메모는 SC-04 컨텍스트 패널에서 미세한 "숨쉬는" CSS pulse (2s ease-in-out infinite)
- 클릭하면 timeline mini-popup: 변경 시각 N개 + 각 시점 sha256 prefix

**(B) Memo → Task Morphing**
- 메모에 `- [ ]` 체크박스 추가 또는 "프로젝트 연결" 액션 → items.type 자동 'memo' → 'task' 변환
- UI에서 WAAPI로 부드러운 morph (300ms): 메모 카드 → task 카드 변형
- 원본 .md 보존, items 메타만 갱신

### 데이터 필드 (file_index 확장)

| 필드 | 타입 | 비고 |
|------|-----|------|
| evolution_count | integer | sha256 변경 시마다 +1 |
| last_morphed_to | text | NULL or 'task' or 'project_ref' |

### Acceptance Criteria

```gherkin
Scenario: Lifecycle pulse 표시
  Given 메모가 5번 편집되었다 (evolution_count=5)
  When  SC-04 컨텍스트 패널을 연다
  Then  해당 메모 카드가 부드럽게 pulse 한다
  And   클릭 시 timeline popup에 5개 변경 시각이 표시된다

Scenario: 체크박스 추가로 task 승격
  Given 메모 "API 설계 고민"이 있다 (type='memo')
  When  메모 첫 줄에 `- [ ]` 체크박스를 추가한다
  Then  items.type이 'task'로 변경된다
  And   UI에서 메모 카드 → task 카드로 morph 애니메이션이 재생된다 (300ms)
  And   .md 파일은 유지된다

Scenario: Lifecycle 비활성 (evolution_count < 3)
  Given 메모가 1번만 편집되었다
  When  SC-04를 연다
  Then  pulse 효과 없이 정적으로 표시된다
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-MEMO-07-01 | AC-1 | pulse + timeline popup | E2E | P1 |
| TC-MEMO-07-02 | AC-2 | type 변경 + morph | 통합 | P1 |
| TC-MEMO-07-03 | AC-3 | 비활성 정적 표시 | 단위 | P2 |

> **V1.1 확장**: ③ Reflection Constellation, ④ Voice Annotation은 V1.1로 이관 (D6).

---

## FR-PROJ-01: 프로젝트 등록·계층 연결 ⚡ v1.3 전면 재정의

**한 줄**: 프로젝트를 사업(Business) 하위에 등록하고, 시작·마감일과 단계를 관리한다. `[iet03]`
**비즈니스 가치**: 소속→사업→프로젝트 계층으로 복수 컨텍스트를 체계적으로 관리. `[iet03]`

> **v1.3 변경**: 이전 "프로젝트 ⊂ 태그" 모델 폐기. 프로젝트는 독립 엔티티로 business_id 또는 NULL(무소속) 보유.
> 태그는 여전히 메타데이터로 부착 가능하나, 프로젝트의 상위 계층 역할을 하지 않는다.

### 데이터 필드

| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| title | string | Y | 프로젝트명 |
| business_id | integer (FK) | N | NULL = 무소속 |
| start_date | date | N | |
| end_date | date | N | 마감일 |
| status | enum | Y | planning/active/review/done/paused/archived |
| github_repo | string | N | "owner/repo" |
| vision | string | N | |
| folder_path | string | auto | MC-Notes 상대 경로 |

### Acceptance Criteria

```gherkin
Scenario: 사업 하위 프로젝트 등록
  Given 사업 "플링크케어 사업"이 존재한다
  When  프로젝트명 "MC 개발", 시작 2026-05-01, 마감 2026-08-31을 입력하고 저장한다
  Then  projects 테이블에 business_id가 연결된 row가 생성된다
  And   MC-Notes/플링크데이터/플링크케어-사업/MC-개발/ 폴더가 생성된다
  And   SC-14 계층 뷰에서 해당 위치에 표시된다

Scenario: 무소속 프로젝트 등록
  Given 사업을 선택하지 않는다
  When  프로젝트를 저장한다
  Then  business_id = NULL로 저장된다
  And   SC-14 "무소속" 섹션에 표시된다

Scenario: 프로젝트 상태 변경 (planning → active)
  Given 프로젝트가 "planning" 상태다
  When  "시작" 액션을 실행한다
  Then  status = 'active', start_date = 오늘로 업데이트된다
```

### 비즈니스 규칙

| BR-ID | IF | THEN | 출처 |
|-------|-----|------|------|
| BR-PROJ-01 | 프로젝트 생성 | FR-FILES-01에 따라 폴더 자동 생성 | `[iet03]` |
| BR-PROJ-02 | business_id = NULL | "무소속" 섹션에 분류 | `[추론]` |
| BR-PROJ-03 | 프로젝트 삭제 | 연결된 items는 project_id = NULL로 해제 (삭제 안 함) | `[추론]` |
| BR-PROJ-04 | end_date 초과 + status != done | 알림 트리거 (notification_events) | `[추론]` |

---

## FR-PROJ-02: 프로젝트 단계(Stage) 관리

**한 줄**: 프로젝트 하위에 단계(기획·개발·검토·완료 등)를 정의하고 단계별 폴더와 항목을 관리한다. `[iet03]`

### Acceptance Criteria

```gherkin
Scenario: 단계 추가
  Given 프로젝트 "MC 개발"이 존재한다
  When  단계명 "02_개발", 순서 2를 추가한다
  Then  project_stages에 row가 생성된다
  And   MC-Notes/.../MC-개발/02_개발/ 폴더가 생성된다

Scenario: 단계 진행 표시
  Given 단계에 연결된 항목이 10개, 완료 7개다
  When  SC-06 프로젝트 뷰를 열면
  Then  해당 단계의 진척도 70%가 표시된다

Scenario: 단계 순서 변경
  Given 단계 A(1), B(2), C(3)이 존재한다
  When  단계 B를 순서 3으로 변경한다
  Then  order_idx가 업데이트된다
  And   폴더는 유지되고 file_index만 갱신된다
```

---

## FR-PROJ-03: 프로젝트 뷰 (SC-06 개선)

**한 줄**: 프로젝트의 시작-마감 타임라인, 단계별 진척도, 연결 항목을 한 화면에서 조망한다. `[iet03]`

### 화면 레이아웃 (ASCII)

```
┌─────────────────────────────────────────────────────┐
│ MC 개발 프로젝트          [플링크케어 사업 > 플링크데이터]│
│ 2026-05-01 → 2026-08-31   ██████████░░░░ 68% 진행중  │
├─────────────────────────────────────────────────────┤
│ 단계 타임라인                                          │
│ [01_기획 ✅] → [02_개발 ⬤진행중] → [03_검토 ○] → [완료○]│
├─────────────────────────────────────────────────────┤
│ 02_개발 — 현재 단계                                    │
│  ☐ API 설계 문서 작성  [확인 필요🟡]                   │
│  ☑ DB 스키마 확정                                     │
│  ☐ core-api 구현      [블로킹🔴]                      │
├─────────────────────────────────────────────────────┤
│ 연결 파일  02_개발/스펙.md  03_검토/리뷰.md             │
│ GitHub     #42 API 설계 이슈  #38 스키마 PR [열림]     │
└─────────────────────────────────────────────────────┘
```

### Acceptance Criteria

```gherkin
Scenario: 프로젝트 뷰 진입
  Given 프로젝트 "MC 개발"이 존재한다
  When  SC-14 또는 Today's Flow에서 프로젝트를 클릭한다
  Then  SC-06이 열리고 타임라인·단계·항목·파일·GitHub이 표시된다

Scenario: 과거·현재·미래 단계 구분
  Given 3개 단계가 있고 2번째 단계가 active다
  When  SC-06을 열면
  Then  1번째(완료)·2번째(진행중)·3번째(예정)가 시각적으로 구분된다

Scenario: 라벨 필터
  Given SC-06이 열려 있다
  When  "블로킹" 라벨 필터를 적용한다
  Then  해당 라벨이 붙은 항목만 표시된다
```

---

## FR-PROJ-04: GitHub 연동 (기존 유지 + 계층 반영)

**한 줄**: 프로젝트에 GitHub repo를 연결하고 이슈·PR 캐시를 SC-06과 SC-14에 표시한다. `[iet03]`

*(AC는 FR-GIT-01~04와 동일. 변경사항: SC-14 계층 뷰에서도 오픈 이슈 수 표시)*

---

## Change Log

| 버전 | 날짜 | 변경 내용 | 변경자 |
|------|------|----------|--------|
| 1.0 | 2026-04-27 | 최초 작성 | BA Writer v1.0 |
| 1.3 | 2026-05-04 | FR-PROJ-01~04 전면 재정의. 태그 기반 → 소속-사업-프로젝트 계층. 단계·폴더·라벨 연동 추가. | BA Writer v1.0 |
