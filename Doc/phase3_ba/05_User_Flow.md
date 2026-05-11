# 유저 플로우 — MC

> 인풋: [04_Flow.md](../phase1_interview/04_Flow.md) (Phase 1 Mermaid 9종 기반 확장)
> 작성: 2026-04-27 | BA Writer v1.0
> 대상 페르소나: P-01 (iet03)

---

## FLOW-01: 아침 루틴 (Morning Routine)

**관련 FR**: FR-DAY-01, FR-FLOW-01, FR-CAP-01, FR-AI-VOICE

```mermaid
flowchart TD
    A[앱 실행] --> B{당일 첫 실행?}
    B -->|Yes| C[SC-07 아침 프리뷰 표시]
    B -->|No| D[SC-01 Today's Flow 표시]
    C --> E[오늘 일정 + 이월 태스크 + 어제 메모 로드]
    E --> F{항목 존재?}
    F -->|No| G[빈 상태 인사 메시지]
    F -->|Yes| H[항목 시간순 표시]
    G --> I[Quick Capture 대기]
    H --> I
    I --> J{입력 방식?}
    J -->|텍스트| K[FR-CAP-01: 타입 분류 + 미리보기]
    J -->|음성| L[FR-AI-VOICE: Whisper 변환]
    L --> K
    K --> M[사용자 확인 → 저장]
    M --> D
```

| 단계 | 화면 | 사용자 행동 | 시스템 응답 | 적용 BR |
|------|------|-----------|-----------|--------|
| 1 | SC-01 | 앱 실행 | 당일 첫 실행 판단 | — |
| 2 | SC-07 | 프리뷰 확인 | 오늘 일정·이월 태스크·어제 메모 표시 | BR-DAY-04 |
| 3 | SC-01 | Quick Capture 입력 | 타입 분류 미리보기 | BR-CAP-01~04 |
| 4 | SC-01 | Enter 확인 | 저장 + 뷰 반영 | BR-AI-01 |

---

## FLOW-02: 항목 클릭 → 컨텍스트 패널 (Context Assembly)

**관련 FR**: FR-FLOW-03, FR-GIT-03
**MC 핵심 차별화 플로우**

```mermaid
flowchart TD
    A[SC-01: 항목 클릭] --> B[SC-04 컨텍스트 패널 쿼리]
    B --> C{연결된 컨텍스트?}
    C -->|태그 있음| D[태그 칩 표시]
    C -->|정식 프로젝트 있음| E[프로젝트 + 진척도 바 표시]
    C -->|.md 메모 있음| F[메모 미리보기 3줄 표시]
    C -->|GitHub repo 연결됨| G[이슈 목록 조회 from 캐시]
    C -->|아무것도 없음| H[빈 상태 메시지]
    D & E & F & G --> I[패널 렌더 완료 ≤ 0.5초]
    H --> I
    I --> J{사용자 액션}
    J -->|이슈 생성| K[FR-INT-GH-02: 이슈 생성 폼]
    J -->|태그 추가| L[FR-CAP-02: 태그 인라인 추가]
    J -->|다른 항목 클릭| M[패널 갱신 - BR-FLOW-02]
    J -->|패널 닫기| N[SC-01 복귀]
```

| 단계 | 화면 | 사용자 행동 | 시스템 응답 | 시간 목표 |
|------|------|-----------|-----------|---------|
| 1 | SC-01 | 항목 클릭 | 컨텍스트 쿼리 시작 | — |
| 2 | SC-04 | 패널 열림 확인 | 태그·메모·이슈 동시 로드 | ≤ 0.5초 |
| 3 | SC-04 | 이슈 생성 버튼 클릭 | 이슈 생성 폼 오버레이 | — |

---

## FLOW-03: 음성 캡처 → 저장 (Voice Capture)

**관련 FR**: FR-AI-VOICE, FR-CAP-01

```mermaid
sequenceDiagram
    participant User as iet03
    participant UI as MC UI
    participant VAD as silero-vad
    participant ASR as Whisper NPU

    User->>UI: Ctrl+Space (글로벌 단축키)
    UI->>VAD: 마이크 활성화
    User->>VAD: 발화 시작
    VAD->>VAD: 음성 구간 감지 (VAD ON)
    User->>VAD: 묵음 2초
    VAD->>ASR: 음성 데이터 전달
    ASR->>UI: 텍스트 + confidence 반환
    alt confidence >= 0.6
        UI->>User: Quick Capture에 텍스트 표시
        User->>UI: Enter (확인)
        UI->>UI: 저장 + 뷰 반영
    else confidence < 0.6
        UI->>User: 텍스트 표시 + "다시 말하기" 버튼
        User->>UI: 다시 말하기 or 수동 편집 후 확인
    end
```

---

## FLOW-04: 저녁 회고 (Evening Review)

**관련 FR**: FR-DAY-02, FR-DAY-03, FR-MEMO-01

```mermaid
flowchart TD
    A[회고 진입 - 수동 또는 시간 트리거] --> B[SC-07: 오늘 항목 로드]
    B --> C[완료 항목 / 미완료 항목 구분 표시]
    C --> D{미완료 항목 처리}
    D -->|이월| E[scheduled_at = 내일 - BR-DAY-02]
    D -->|보류| F[status = waiting - BR-STATE-03]
    D -->|취소| G[status = cancelled]
    D -->|그대로 유지| H[변경 없음]
    E & F & G & H --> I[반성 메모 입력 폼]
    I -->|저장| J[MC-Notes/YYYY/MM/DD-review.md 저장 - BR-DAY-01]
    I -->|건너뜀| K[회고 완료]
    J --> K
    K --> L[SC-01 복귀]
```

---

## FLOW-05: 의미 검색 (Semantic Search)

**관련 FR**: FR-AI-SEARCH

```mermaid
flowchart TD
    A[검색 쿼리 입력] --> B{인덱스 항목 수?}
    B -->|30개 이상| C[BGE-small NPU 임베딩 생성]
    B -->|30개 미만| D[FTS5 키워드 검색만]
    C --> E[sqlite-vec 코사인 유사도 검색]
    E --> F{결과 존재?}
    F -->|있음| G[결과 목록 표시 ≤ 200ms]
    F -->|없음| H[FTS5 fallback 자동 실행 - BR-AI-04]
    D --> G
    H --> G
    G --> I{결과 클릭}
    I -->|Hot 항목| J[컨텍스트 패널 - FLOW-02]
    I -->|Cold 항목 V1.2| K["Drive에서 불러오기" 버튼]
```

---

## FLOW-06: GitHub 이슈 동기 + 생성

**관련 FR**: FR-GIT-03, FR-GIT-04, FR-INT-GH-02

```mermaid
flowchart TD
    A[15분 타이머 만료 - BR-GIT-02] --> B[백그라운드 API 호출]
    B --> C{응답?}
    C -->|성공| D[SQLite github_items 갱신]
    C -->|실패/Rate Limit| E[캐시 유지 + 알림]
    D --> F[컨텍스트 패널 자동 갱신]

    G[이슈 생성 버튼 클릭] --> H[이슈 생성 폼 오버레이]
    H --> I[제목·본문·라벨 입력]
    I --> J[GitHub API POST /issues]
    J --> K{성공?}
    K -->|Yes| L[이슈 번호 태스크 메타에 연결]
    K -->|No| M[draft 로컬 보존 + 오류 알림]
```

---

## FLOW-07: 외부 .md 편집 감지 → 인덱스 갱신

**관련 FR**: FR-MEMO-04

```mermaid
sequenceDiagram
    participant Ext as 외부 도구 (VS Code 등)
    participant WD as watchdog
    participant IDX as SQLite 인덱스

    Ext->>Ext: .md 파일 편집 + 저장
    WD->>WD: FS 이벤트 감지
    WD->>WD: 1.5초 디바운스 대기
    alt 추가 변경 없음
        WD->>IDX: 변경된 .md 재파싱 + FTS5 갱신
        WD->>IDX: 임베딩 재생성 + sqlite-vec 갱신
        IDX->>IDX: 갱신 완료
    else 파일 삭제
        WD->>IDX: file_location = 'missing' 마킹
        IDX-->>User: 알림: "{파일명} 외부 삭제됨 — 인덱스에서 제거할까요?"
    end
```

---

## FLOW-08: Telegram → MC 빠른 캡처

**관련 FR**: FR-INT-TG-01

```mermaid
sequenceDiagram
    participant User as iet03
    participant TG as Telegram Bot
    participant MC as MC 서버

    User->>TG: "내일 오전 9시 미팅" 메시지 전송
    TG->>MC: Webhook / polling 수신
    MC->>MC: dateutil 날짜 파싱
    alt 파싱 성공
        MC->>MC: type=schedule, scheduled_at=내일 09:00
    else 파싱 실패
        MC->>MC: type=memo, Inbox 저장
    end
    MC->>MC: SQLite 저장
    MC->>User: "캡처됨: {제목}" (옵션: Bot reply)
```

---

## 예외 흐름 요약

| 예외 상황 | 발생 플로우 | 처리 | 복귀 지점 |
|---------|---------|------|---------|
| DB 읽기 실패 | FLOW-01, 02 | 마지막 캐시 표시 + 재시도 버튼 | 정상 시 자동 복귀 |
| 음성 인식 실패 | FLOW-03 | 텍스트 입력 fallback + 안내 | QC 텍스트 입력 |
| GitHub API 실패 | FLOW-06 | 캐시 유지 + 알림 | 다음 동기 주기 |
| 파일 충돌 | FLOW-07 | 3옵션 다이얼로그 (BR-MEMO-07) | 사용자 선택 후 |
| 네트워크 단절 (TG) | FLOW-08 | 재시도 큐 → 복구 시 처리 | 자동 |

---

## Change Log

| 버전 | 날짜 | 변경 내용 | 변경자 |
|------|------|----------|--------|
| 1.0 | 2026-04-27 | Phase 1 Flow 기반 BA 형식화 + 4개 신규 플로우 추가 | BA Writer v1.0 |
