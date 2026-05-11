# 흐름 다이어그램 (Flow Diagrams) — MC

> 관련: [02_Feature.md](./02_Feature.md), [03_Business_Rules.md](./03_Business_Rules.md), [04_Screen_Spec.md](./04_Screen_Spec.md)
> 작성: 2026-04-26
> 상태: **Draft — [추론] 기반. iet03 검토 후 Confirmed**

---

## 1. 일일 사용 흐름 (Master Flow)

```mermaid
flowchart TD
    A[MC 실행 / 첫 진입] --> B{오늘 첫 실행?}
    B -- 예 --> C[아침 프리뷰 자동 표시<br/>SC-01 + 강조]
    B -- 아니오 --> D[Today's Flow 진입]
    C --> D
    D --> E{사용자 액션}
    E -- Quick Capture 입력 --> F[BR-CAP-01 자동 분류]
    E -- 항목 클릭 --> G[SC-04 컨텍스트 패널]
    E -- 음성 단축키 --> H[SC-05 Voice Glass]
    E -- 사이드바 정식 프로젝트 --> I[SC-06 Project Detail]
    E -- 뷰 토글 --> J[Calendar / Constellation 전환]
    F --> K[미리보기 표시]
    K --> L{사용자 확인?}
    L -- OK --> M[등록 + 흐름 갱신]
    L -- 취소 --> D
    H --> N[Whisper STT NPU]
    N --> O[Phi-3 슬롯 추출 NPU]
    O --> K
    G --> P{패널 액션}
    P -- 편집/완료/삭제 --> M
    P -- 닫기 --> D
    M --> D
    D --> Q{시간 = 저녁?}
    Q -- 예, 사용자 회고 진입 --> R[SC-07 Evening Review]
    Q -- 아니오 --> D
    R --> S[미완료 이월/보류 처리]
    S --> T[회고 메모 .md 저장 BR-DAY-01]
    T --> U[종료 또는 D로 복귀]
```

---

## 2. Quick Capture 자동 분류 흐름 (FR-CAP-01)

```mermaid
flowchart LR
    A[자유 텍스트 입력] --> B{시간 패턴 포함?<br/>14:00 / 오전 10시 / 내일}
    B -- 예 --> C[event 후보]
    B -- 아니오 --> D{체크박스 패턴?<br/>todo / 할 일}
    D -- 예 --> E[task 후보]
    D -- 아니오 --> F[memo 후보]
    C --> G[#태그 추출]
    E --> G
    F --> G
    G --> H[Phi-3 슬롯 추출 NPU<br/>JSON 변환]
    H --> I[미리보기 카드 표시]
    I --> J{사용자 확인}
    J -- 등록 --> K[DB 저장 + .md 추가]
    J -- 수정 --> L[수정 폼 표시]
    L --> J
    J -- 취소 --> M[입력 보존, Capture 닫음]
```

---

## 3. 음성 입력 흐름 (FR-AI-VOICE + UX-04)

```mermaid
sequenceDiagram
    actor 사용자
    participant UI as Voice Glass UI
    participant Whisper as Whisper Base (NPU)
    participant Phi as Phi-3 mini (NPU)
    participant DB

    사용자->>UI: Ctrl+Space 또는 마이크 클릭
    UI->>UI: 반투명 오버레이 + 음파 시각화
    사용자->>UI: 발화
    UI->>Whisper: 오디오 스트림
    Whisper-->>UI: 받아쓰기 텍스트 (1초 내)
    UI->>Phi: "텍스트 → JSON 슬롯 추출"
    Phi-->>UI: {time, title, tags, type} (1~2초)
    UI-->>사용자: 미리보기 카드
    사용자->>UI: [등록] 클릭
    UI->>DB: 항목 저장
    UI->>UI: 오버레이 닫음, 흐름 갱신
    Note over UI: BR-AI-01: 자동 적용 금지 — 항상 사용자 확인
```

---

## 4. 의미 검색 흐름 (FR-AI-SEARCH)

```mermaid
flowchart LR
    A[검색창 쿼리 입력] --> B[BGE-small NPU<br/>쿼리 임베딩 50ms]
    B --> C[sqlite-vec 벡터 검색<br/>50ms]
    C --> D{결과 수}
    D -- 1+ --> E[관련 항목 정렬 표시]
    D -- 0 --> F[FTS5 키워드 fallback<br/>BR-AI-04]
    F --> G{결과 수}
    G -- 1+ --> H["키워드 매칭 결과" 라벨로 표시]
    G -- 0 --> I["검색 결과 없음" 안내]
```

---

## 5. 외부 .md 변경 감지·반영 흐름 (BR-MEMO-02, BR-MEMO-07)

```mermaid
flowchart TD
    A[외부 도구가 .md 편집] --> B[chokidar/watchdog 감지]
    B --> C[1.5초 디바운스]
    C --> D{MC도 같은 파일을 편집 중?}
    D -- 아니오 --> E[인덱스 자동 갱신<br/>임베딩 재계산<br/>FTS5 재인덱싱]
    D -- 예 (충돌) --> F[충돌 알림 표시]
    F --> G{사용자 선택}
    G -- 외부 변경 수용 --> E
    G -- MC 변경 유지 --> H[외부 변경 무시, MC 변경 저장]
    G -- 수동 병합 --> I[Diff 뷰 표시 → 사용자 편집]
    I --> E
    E --> J[흐름·검색 결과에 즉시 반영]
```

---

## 6. Git 이슈 동기 흐름 (FR-GIT-03·04)

```mermaid
flowchart LR
    A[자동 동기 타이머<br/>디폴트 15분] --> B{토큰 유효?}
    B -- 아니오 --> C[BR-GIT-06<br/>인증 안내]
    B -- 예 --> D[GraphQL 일괄 호출<br/>연결된 모든 정식 프로젝트]
    D --> E{Rate Limit?}
    E -- 도달 --> F[BR-GIT-04<br/>다음 재시도 시각 표시]
    E -- OK --> G[로컬 캐시 갱신]
    G --> H[관련 프로젝트 페이지·컨텍스트 패널 갱신]
    F --> A
    C --> I[사용자 PAT 재등록 후 A로]
```

---

## 7. 태스크 상태 전이

```mermaid
stateDiagram-v2
    [*] --> todo
    todo --> doing : 시작 클릭 (BR-STATE-01)
    doing --> done : 완료 (BR-STATE-02)
    todo --> waiting : 보류 (BR-STATE-03)
    doing --> waiting : 보류 (BR-STATE-03)
    waiting --> doing : 재시작 (BR-STATE-04)
    todo --> cancelled : 취소 (BR-STATE-05)
    doing --> cancelled : 취소
    waiting --> cancelled : 취소
    todo --> todo_next_day : 저녁 회고 "내일로"<br/>(BR-STATE-06, 원본 ID 보존)
    cancelled --> [*] : hidden
    done --> [*]
```

---

## 8. 정식 프로젝트 상태 전이

```mermaid
stateDiagram-v2
    [*] --> idea : 정식 프로젝트로 마킹
    idea --> active : 활성화 (BR-STATE-07)
    active --> archived : 보관 (BR-STATE-08)
    archived --> active : 재활성 (BR-STATE-09, 메타 복원)
    active --> tag : 일반 태그로 강등<br/>(BR-STATE-10, 메타 hidden 보존)
    idea --> tag : 강등
    archived --> tag : 강등
    tag --> active : 재승격 (메타 복원)
```

---

## 9. AI 모델 로드·언로드 라이프사이클 (BR-AI-08·09)

```mermaid
flowchart TD
    A[MC 시작] --> B[백그라운드 모델 로드<br/>Whisper + BGE + Phi-3]
    B --> C[로드 진행률 표시 사이드바 하단]
    C --> D[로드 완료]
    D --> E[Idle — 사용자 호출 대기]
    E --> F{사용자 음성/검색/슬롯 호출}
    F --> G[추론]
    G --> E
    E --> H{시스템 RAM &lt; 1GB free?}
    H -- 예 --> I[BR-AI-09 모델 unload]
    I --> J[다음 호출 시 lazy reload]
    H -- 아니오 --> E
    J --> G
```

---

## Open Questions

| OQ-ID | 질문 | 기한 |
|-------|------|------|
| OQ-04-04 | 음성 입력 중 발화 끝 자동 감지(VAD) 방식 vs Push-to-Talk(누른 동안만) | Phase 4 |
| OQ-04-05 | Quick Capture 자동 분류가 모호할 때 (BR-CAP의 분기가 둘 다 해당) 디폴트 우선순위 — 일정 > 태스크 > 메모? | Step 5 |
| OQ-04-06 | 외부 .md 충돌 시 디폴트 (BR-MEMO-07) — 묻기 vs 외부 우선 vs MC 우선 | Step 5 |

---

## 다음

→ Step 5 ([05_Gap_Analysis.md](./05_Gap_Analysis.md)): 비판적 갭 분석 — 누락 기능, 리스크, 새 아이디어.
