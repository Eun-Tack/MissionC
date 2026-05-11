# 전략 요약 (Strategy Summary) — MC

> 프로젝트: MC (Mission Control)
> 작성: 2026-04-26 | Strategist v1.0
> 상태: **Confirmed (2026-04-27 03·04 산출물 추가)**
> 인풋: Phase 0 ([Research_Summary](../phase0_research/00_Research_Summary.md), [Competitive_Analysis](../phase0_research/02_Competitive_Analysis.md), [Tech_Landscape](../phase0_research/03_Tech_Landscape.md)) + Phase 1 ([06_Summary](../phase1_interview/06_Summary.md))
> 동반 산출물: [01_Differentiation_Strategy](./01_Differentiation_Strategy.md), [02_Competitive_Positioning](./02_Competitive_Positioning.md)

---

## 1. 핵심 전략 한 줄 정의

> **MC는 1인 윈도우 지식노동자를 위해, 컨텍스트 자동 결합 + 로컬-퍼스트 의미 검색 + NPU 활용으로, Notion(클라우드)·Obsidian(vault 강제)·Sunsama(PKM 부재)가 해결하지 못한 "스케줄·프로젝트·메모·Git이 한 흐름에서 끊기는" 문제를 해결한다.**

---

## 2. 핵심 차별화 포인트 (3가지)

| 순위 | 차별화 포인트 | 경쟁사 현황 | 우리의 목표 (V1.x) | 근거 | 우선순위 |
|-----|------------|---------|-------------|------|--------|
| **1** | **컨텍스트 자동 결합** | Notion/Obsidian: 항목 클릭 → 페이지 이동만 | 클릭 즉시 우측 패널: 태그·메모·이슈·진척도 동시 (FR-FLOW-03) | [Phase0-경쟁사분석] 빈자리 + [iet03] 핵심 가치 | **Must (V1.0)** |
| **2** | **로컬-퍼스트 의미 검색** | Notion AI: 클라우드 / Obsidian·Logseq: FTS만 | NPU BGE-small + sqlite-vec (FR-AI-SEARCH) | [Phase0-기술트렌드] NPU sweet spot + [Phase1-사용자] | **Must (V1.0)** |
| **3** | **Voice + UX 단계화 시그니처** | 모두 키보드 전제, 평면 캘린더 | V1.0 음성 캡처 → V1.1 Voice Glass → V1.2 Constellation | [iet03] 도전적 UX 명시 + [Phase0-기술트렌드] Whisper NPU | **Should (V1.0~1.2)** |

> 다른 후보 (vault 강제 없음, 데이터 외부 송신 0, GitHub 이슈 통합 등)는 위 3개 차별화의 *결과적 부산물*로 자연 도출됨.

### 지원 인프라 — 3rd Party 연동 & 데이터 티어

| 연동 | 방향 | 버전 | 역할 |
|-----|-----|------|-----|
| **Telegram Bot** | 양방향 | V1.0 | 빠른 캡처 채널 + 알림 push |
| **GitHub** | 양방향 | V1.0 | 이슈·PR 조회·생성·태스크 연결 |
| **Gmail** | 읽기 | V1.1 | 중요 메일 → 컨텍스트 패널 |
| **Google Drive** | 쓰기/읽기 | V1.2 | Cold tier 아카이브 (로컬 삭제 + 메타만 보존) |

**Hot/Cold 데이터 티어 (V1.2)**:
- Hot = 활성 프로젝트 .md 로컬 + SQLite 풀 인덱스
- Cold = Drive 아카이브 후 로컬 .md 삭제, 태그·벡터·매핑은 SQLite 보존 → 검색은 계속 동작, 본문은 lazy fetch
- 재활성화 = Drive → 로컬 복원

→ 상세: [04_Integration_Map](./04_Integration_Map.md)

---

## 3. 4개 축 전략 결론 (요약)

| 축 | 핵심 결론 |
|----|--------|
| UX | **컨텍스트 자동 결합** — 시장 빈자리 + iet03 핵심 가치 직접 일치 |
| 디자인 | **단계화** — V1.0 표준, V1.1 Voice Glass, V1.2 Constellation. 학습 곡선 분산. 브랜드: Personal · Local · Connected · Quiet |
| 기능 깊이 | **의미 검색 + 컨텍스트 결합** 결합 진입 장벽 강함 |
| 기술 우위 | **NPU 가속 임베딩 (V1.0) + 로컬 LLM (V1.1+)** — 클라우드 의존 시장에서 수년간 변하지 않을 차별점 |
| 포지셔닝 | "1인 윈도우 로컬 통합 운영 도구" — 시장 빈자리. 개인 무료/OSS 후보. |

---

## 4. Phase 3 BA Writer 전략 지시

### 핵심 차별화 포인트 PRD 반영 지시

| 차별화 포인트 | 반영할 기능 영역 | BA 구현 지시 | 우선순위 |
|------------|-----------|---------|--------|
| **1. 컨텍스트 자동 결합** | FR-FLOW-03 + SC-04 컨텍스트 패널 | PRD에 "MC의 메인 차별화는 항목 클릭 시 모든 연결 컨텍스트가 한 패널에 즉시 표시" 명시. AC에 "패널 펼침 0.5초 이내", "관련 항목 N개 표시" 정량 기준 포함. 컨텍스트 패널은 V1.0 시그니처 — Vision & Scope 첫 페이지에 강조. | **Must** |
| **2. 로컬-퍼스트 의미 검색** | FR-AI-SEARCH | PRD에 "검색 디폴트=의미 검색, FTS는 fallback" 명시. AC에 "쿼리→결과 200ms 이내", "데이터 30개 미만이면 FTS 전용" 포함. 본인 데이터 외부 송신 0이라는 규약 강조. | **Must** |
| **3. Voice + UX 단계화** | V1.0: FR-AI-VOICE, FR-CAP / V1.1: FR-UX-04 / V1.2: FR-UX-01 | V1.0 PRD 범위는 단순 음성 캡처까지만. V1.1·V1.2는 별도 PRD 또는 Roadmap 섹션. 단계마다 "기존 사용자 학습 곡선 손실 X" 원칙. | Could (단계별) |

### 포지셔닝 메시지 (PRD Vision & Scope 반영용)

```
MC는 1인 윈도우 지식노동자를 위한 로컬-퍼스트 운영 도구다.
스케줄·프로젝트·메모·Git 이슈가 한 화면에서 흐름으로 연결되며,
본인 데이터는 외부에 보내지 않는다.
도구 사이를 오가지 않게, 일을 흐름으로 관리한다.
```

### 디자인 차별화 반영 사항

**Screen Spec에 반드시 포함할 시그니처 경험**:
- SC-01 메인 흐름 + SC-04 컨텍스트 패널 — *클릭 한 번에 컨텍스트 복원*
- (V1.1+) SC-05 Voice Glass — *음성 입력 시 반투명 유리 + 음파 시각화*
- (V1.2) SC-03 Time Constellation — *24h 원형 + 별자리 곡선* (토글 옵션)

**피해야 할 경쟁사 패턴**:
- Notion 사이드바 트리 폭주 → 사이드바는 정식 프로젝트 + 일반 태그만 (3~5개)
- Obsidian "vault 강제" → MC는 외부 .md 폴더 자유 등록
- Akiflow 시끄러운 알림 → 침입형 알림 X, OS 통지만 미니멀
- 클라우드 LLM 호출 → 모든 AI는 로컬 NPU/iGPU

**브랜드/UX 키워드**: **Personal · Local · Connected · Quiet**

### BA Writer 주의 사항

- **강조할 것**:
  - 컨텍스트 패널 (FR-FLOW-03)을 V1.0 시그니처로
  - 의미 검색을 검색의 *디폴트* 로
  - 단일 원본 .md + 메타 매핑 (BR-MEMO-01) — 데이터 모델 핵심
  - 모든 AI 결과는 사용자 확인 후 적용 (BR-AI-01) — AC에 강제 명시
  - 정식 프로젝트 ⊂ 태그 (BR-PROJ-02) — ERD 핵심
- **의도적으로 제외할 것 (V1.0)**:
  - 다중턴 LLM 에이전트 (V2)
  - RAG 답변 생성 (V2)
  - 자동 묶음 제안 (V2 — iet03 명시 결정)
  - 멀티유저·팀·모바일
  - 클라우드 LLM 호출
- **포지셔닝 충돌 방지**:
  - "더 강력한 PKM" 또는 "더 나은 캘린더" 식 표현 금지 — 우리는 *통합 운영*
  - "AI 비서" 단독 강조 금지 — AI는 보조, 핵심은 컨텍스트 결합
  - 외부 SaaS·클라우드 종속을 추가하는 요구사항 발견 시 즉시 전략팀 검토

---

## 5. Strategy Readiness Score

| 항목 | 배점 | 자가 점수 | 비고 |
|------|------|--------|------|
| 4개 축 분석 전체 완료 (근거 데이터 포함) | 20 | 20/20 | [01_Differentiation_Strategy](./01_Differentiation_Strategy.md) 4축 매트릭스 + 결론 |
| 차별화 포인트 3가지 이하 집중 | 15 | 15/15 | 정확히 3개 |
| 모든 주장에 Phase 0/1 출처 태그 | 15 | 15/15 | [Phase0-*], [Phase1-*], [iet03], [추론] 명시 |
| Phase 3 BA Writer용 전략 지시 완료 | 20 | 20/20 | 본 문서 §4 |
| 임팩트×실행가능성 우선순위 근거 명시 | 15 | 15/15 | [01](./01_Differentiation_Strategy.md) 매트릭스 |
| 포지셔닝 리스크 + 대응 전략 포함 | 15 | 15/15 | 5개 리스크 + 대응 ([01](./01_Differentiation_Strategy.md) 축 4 + [02](./02_Competitive_Positioning.md) §4) |
| **합계** | **100** | **100/100** | |

**판정**: ✅ **Phase 3 BA Writer 착수 가능 (≥80점)**

---

## 6. Q-KPI 기록

| KPI | 값 | 메모 |
|-----|---|------|
| Q1-01 수정 요청 횟수 | 0회 (Draft 상태, 사용자 검토 대기) | 검토 후 갱신 |
| Q1-02 수정 요청 유형 | — | |
| Q1-03 체감 완성도 | (Phase 7 종합 시 평가) | |
| Q1-04 Gate 통과 여부 | Pass (Score 100/100) | iet03 검토 후 Confirmed 전환 |

---

## 7. 다음 단계

→ **Phase 3 (BA Writer)** 진입:
- 산출물: Vision & Scope, PRD (전략 반영), User Flow, Screen Spec 정리, 비즈니스 규칙 통합, 테스트 케이스 초안 등 (8종)
- Gate: BA Handoff Score ≥ 80점 + 셀프 리뷰 완료
- iet03가 본 전략 산출물 3개 검토 → 수정 요청 또는 Confirmed → Phase 3 진입
