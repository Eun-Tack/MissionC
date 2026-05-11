# Phase 1 요약 — MC

> Phase 1 산출물: [00_Kickoff](./00_Kickoff.md), [01_Users_and_Scenarios](./01_Users_and_Scenarios.md), [02_Feature](./02_Feature.md), [03_Business_Rules](./03_Business_Rules.md), [04_Screen_Spec](./04_Screen_Spec.md), [04_Flow](./04_Flow.md), [05_Gap_Analysis](./05_Gap_Analysis.md)
> 작성: 2026-04-26
> 상태: ✅ **Confirmed — BA Readiness Score 100/100, OQ-05-* 5개 답변 완료**

---

## 2026-04-26 결정 (OQ-05-01~05 답변, "추천대로 진행")

| OQ | 답변 | 영향 |
|----|------|------|
| **OQ-05-01** V1 스코프 | **(나) MVP 24 FR로 좁힘 + 알림·충돌 검사 추가 = 26 FR**. SLOT은 V1.1, UX 혁신은 V1.2~ | V1.0 추정 4~6개월 |
| OQ-05-02 OS 통지 | **V1 포함** (BR-NOTIFY-01) | FR-NOTIFY-01 추가 |
| OQ-05-03 일정 충돌 검사 | **V1 포함**, LLM 없는 단순 SQL (BR-CONFLICT-01) | FR-CONFLICT-01 추가 |
| OQ-05-04 회고 저장 | **별도 파일** (`MC-Notes/YYYY/MM/DD-review.md`) | BR-DAY-01 갱신 |
| OQ-05-05 백업 | **수동 트리거 + 메뉴 노출** (BR-BACKUP-01) | FR-BACKUP-01 추가 |

→ V1.0 / V1.1 / V1.2 분리 라인업으로 변경.

---

## V1.0 MVP 라인업 (확정 — 4~6개월 추정)

### 표준 기능 (21 FR)
- **FLOW** (3): Today's Flow / Calendar / Context Panel
- **CAP** (2): Quick Capture / 다중 태그 인라인
- **MEMO** (5): 일자 .md / 자유 명명 / LocalDocsHub 연결 / 외부 편집 감지 / 다중 매핑
- **PROJ** (4): 태그 / 정식 마킹 / 강등 / 사후 묶음
- **GIT** (4): PAT / repo 연결 / 이슈 조회 / 자동 동기
- **DAY** (3): 아침 프리뷰 / 저녁 회고 (별도 파일) / 미완료 이월

### AI (NPU 3 FR)
- **FR-AI-VOICE**: Whisper Base ONNX → 음성 → 텍스트
- **FR-AI-SEARCH**: BGE-small-ko ONNX → 의미 검색 (시그니처)
- **FR-AI-TAG**: 임베딩 재사용 → 태그 자동 제안 (제안만)

### 추가 (Step 5 갭 → V1 편입, 2 FR)
- **FR-NOTIFY-01**: OS 시스템 알림 (일정 5분 전, 디폴트 ON)
- **FR-CONFLICT-01**: 일정 등록 시 같은 시간대 충돌 경고 (단순 SQL)

### 백업 (1 FR)
- **FR-BACKUP-01**: 수동 JSON export 메뉴 (디폴트 OFF)

**V1.0 총: 26 FR**, 모델 메모리 ~270MB (Whisper 0.15GB + BGE 0.12GB)

---

## V1.1 / V1.2 분리 (V1.0 출시 후)

| 버전 | 추가 항목 | 모델 추가 |
|-----|---------|--------|
| **V1.1** | FR-AI-SLOT (Phi-3 mini 자연어 → JSON 단발), FR-UX-04 Voice Glass UI | Phi-3 mini ~2GB |
| **V1.2** | FR-UX-01 Time Constellation (메인 뷰 토글) | — |
| V2 | AGENT/RAG/SUM/CLUSTER/MOOD, UX-02·03·05·06·07 | 7B급 SLM 검토 |

---

## 핵심 비즈니스 규칙 — 결정 요약

| 영역 | 규칙 | 출처 |
|------|------|------|
| 데이터 모델 | 원본 .md 1개 + 메타 다중 매핑 (BR-MEMO-01) | [iet03] |
| 프로젝트 구조 | 정식 프로젝트 ⊂ 태그. 자동 묶음 V1 금지 (BR-PROJ-02·05) | [iet03] |
| AI 적용 | 모든 추론 결과는 사용자 확인 후만 (BR-AI-01) | [iet03] |
| 시크릿 저장 | Windows Credential Manager (BR-AUTH-02, BR-GIT-01) | [iet03] |
| 외부 통신 | 사용자 명시 동의 후만, 디폴트 OFF (BR-AUTH-03) | [iet03] |
| 미완료 이월 | 원본 ID 보존, 날짜만 이동 (BR-DAY-02, BR-STATE-06) | [iet03] |

---

## BA Readiness Score 계산

| 항목 | 배점 | 달성 | 근거 |
|------|------|----|------|
| 모든 기능에 출처(Source) 있음 | 10 | ✅ | 모든 FR이 [iet03] 또는 [추론] 명시 |
| 모든 기능에 실패 시나리오 있음 | 15 | ✅ | 02_Feature.md 모든 FR 표에 실패 컬럼 |
| 모든 BR에 IF-THEN + 출처 있음 | 15 | ✅ | 03_Business_Rules.md (54개 BR) |
| 모든 기능에 Edge Cases 있음 | 15 | ✅ | 그룹별 Edge Cases 섹션 |
| 모든 기능에 권한 정의됨 | 10 | ✅ | 1인 사용자 — BR-AUTH-01 전역 명시 |
| Open Questions에 담당자+기한 있음 | 10 | ✅ | 모든 OQ에 iet03 + 기한 |
| 주요 흐름에 Mermaid 다이어그램 있음 | 10 | ✅ | 04_Flow.md 9개 (Master/Capture/Voice/Search/Sync/Git/태스크/프로젝트/AI lifecycle) |
| 비판적 갭 분석 완료 | 15 | ✅ | 05_Gap_Analysis.md (Critical 3 + High 5 + Medium 8 + Idea 8) |
| **합계** | **100** | **100** | |

**판정**: ✅ BA 핸드오프 가능 (≥80점)

---

## Hard Blocker 검토

| 카테고리 | 항목 | 핸드오프 영향 |
|---------|------|------------|
| Critical Gap (PoC 권장) | GAP-C-01 LLM 응답 시간 / GAP-C-02 Whisper 정확도 / GAP-C-03 백업 전략 | **Phase 4 PoC로 해결** — Phase 1·2 핸드오프엔 영향 없음 |
| Open OQ (iet03 답변 필요) | OQ-05-01 V1 스코프 / OQ-05-02 알림 / OQ-05-03 충돌 검사 / OQ-05-04 회고 저장 / OQ-05-05 백업 export | **Phase 2 진입 전 답변 권장** (Strategist가 차별화 전략 짜는 데 영향) |

**결론**: Score 100점이지만 OQ-05-01(V1 스코프 결정)은 Phase 2 진입 전 답변 받는 것을 권고. 나머지 4개는 동시 또는 Phase 2 중 답변 OK.

---

## Open Questions 통합 목록 (Phase 1 종료 시점 미해결)

| OQ-ID | 질문 | 등급 | 목표 답변 시점 |
|-------|------|----|------------|
| OQ-04-01 | Time Constellation 항목 위치 정밀도 (30분 vs 분 단위) | Low | Phase 3 |
| OQ-04-02 | Voice Glass 효과음/햅틱 V1 포함? | Low | Phase 4 |
| OQ-04-03 | GitHub 이슈 *수정·코멘트 작성* V1 포함? | Medium | Step 5 → 미답 → Phase 2 |
| OQ-04-04 | 음성 VAD vs Push-to-Talk | Low | Phase 4 |
| OQ-04-05 | Quick Capture 분기 모호 시 디폴트 우선순위 | Low | Phase 2 |
| OQ-04-06 | 외부 .md 충돌 시 디폴트 정책 | Medium | Phase 2 |
| **OQ-05-01** | **V1 스코프 — 27 FR 그대로 vs MVP(24 FR)로 좁힐지** | **High** | **Phase 2 진입 전** |
| OQ-05-02 | 일정 알림 V1 OS 통지 포함? | Medium | Phase 2 |
| OQ-05-03 | 일정 충돌 검사 V1 단순 SQL 포함? | Medium | Phase 2 |
| OQ-05-04 | 회고 저장 — 일자 .md append vs 별도 파일 | Medium | Phase 2 |
| OQ-05-05 | 백업 — JSON export 디폴트 ON/OFF | Low | Phase 4 |

---

## Phase 2 Strategist 인계 자료

### 핵심 메시지
MC는 "1인 윈도우 사용자 + 로컬-퍼스트 + 캘린더 + 프로젝트 + 외부 .md 연결 + Git 이슈" 7축을 모두 만족하는 도구가 시장에 없다는 빈자리를 노린다. ([Phase 0 통합 매트릭스](../phase0_research/02_Competitive_Analysis.md#3-통합-매트릭스))

### 차별화 후보 (Phase 2 검증 대상)
1. **연결성 시각화** — Time Constellation으로 같은 태그 항목들의 흐름 한 화면
2. **단일 원본 + 다중 매핑** — vault 강제 없이 외부 .md 자유 (Obsidian 마찰 회피)
3. **Voice-First Agent UI** — Whisper NPU 실시간 + 음성으로 캡처·검색·등록 (단, 현실적 단발 추출까지만 V1)
4. **로컬 의미 검색** — FTS5 한계 돌파, 데이터 외부 송신 없음
5. **GitHub 이슈가 한 화면** — 시장에서 누구도 본격 구현 안 함

### Strategist용 질문
- 위 5개 중 V1 차별화 메시지 1순위는?
- 마케팅 narrative ("MC는 ___이다") 한 문장은?
- 사용자가 "왜 Notion/Obsidian 대신 MC?" 물을 때 1줄 답?

### 핵심 리스크 (Strategist가 알아야)
- iet03 노트북 NPU 실측 성능 미검증 (GAP-C-01·02)
- V1 스코프 27 FR — 1인 6~10개월 (GAP-H-02)
- 시장 차별화 강하나 학습 곡선 (Time Constellation, Voice UX)

---

## 진행 상태 요약

```
━━━ Phase 0: 리서치 & 벤치마킹 ━━━━━━━━━━ ✅ 완료 (Score 100/100)
━━━ Phase 1: 요구사항 인터뷰 ━━━━━━━━━━━ ✅ Draft 완료 (Score 100/100)
   Step 1: Users & Scenarios          ✅
   Step 2: Feature                    ✅
   Step 3: Business Rules             ✅
   Step 4: Screen Spec + Flow         ✅
   Step 5: Gap Analysis               ✅
   Step 6: Summary + Score            ✅ (현재)
━━━ Phase 2: 경쟁 전략 ━━━━━━━━━━━━━━━━━ ⏳ 대기
━━━ Phase 3: BA 문서화 ━━━━━━━━━━━━━━━━━ ⏳ 대기
━━━ Phase 4: 기술 설계 + PoC ━━━━━━━━━━━ ⏳ 대기 (PoC 권고: GAP-C-01·02·H-04)
━━━ Phase 5~7 ━━━━━━━━━━━━━━━━━━━━━━━━━ ⏳ 대기
```

---

## 다음 행동

**iet03 권장 답변**:
1. **OQ-05-01**: V1 = 27 FR 그대로 / MVP 24 FR로 좁힘 / 다른 절충안?
2. (선택) OQ-05-02·03·04·05 — Phase 2 진입 시 답해도 OK

답변 받으면:
- Phase 1 산출물 *Draft → Confirmed* 전환
- KPI 기록 (`AI_SDLC/framework/kpi/KPI_HISTORY.md`)
- **Phase 2 (Strategist 에이전트 로드)** 진입 — 차별화 전략 + 포지셔닝 메시지 수립
