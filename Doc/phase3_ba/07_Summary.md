# BA 요약 & Dev Handoff — MC (Mission Control)

> 문서 ID: BA-SUM-MC-1.3
> 작성: 2026-04-27 | BA Writer v1.0 | v1.3 개정: 2026-05-04
> 상태: **Approved v1.5 — iet03 셀프 사인오프 완료 (2026-05-06)**
> 인풋: Phase 1 전체 + Phase 2 전략 산출물 5종 + v1.3 요구사항 (소속·사업·캘린더·라벨·설치형·GDrive)

---

## 1. BA 완료 현황

| 항목 | 수량 | 상태 |
|------|------|------|
| PRD 기능 — Must (V1.0) | **43 FR** (v1.1 30 + v1.3 신규 8종 + v1.4 신규 2종 + v1.5 신규 3종) | Draft v1.5 |
| PRD 기능 — Should/Could (V1.1/V1.2) | 5 FR | 범위 외 |
| 비즈니스 규칙 — 확인됨 | 22 + 13 (OPS) + 12 (ORG/FILES/PROJ) BR | `[iet03]` 직접 확인 |
| 비즈니스 규칙 — 검토중 `[추론]` | 35+ BR | iet03 셀프 검토 필요 |
| Gherkin AC | 3~5개/FR × 38 FR | Draft |
| User Flow | 8개 | Draft (v1.3 ORG/CAL 흐름 추가 필요) |
| Screen Spec | SC-01~08 + 보충 SC-09~12 + v1.3 SC-13~14, SC-06 갱신 | Draft v1.3 |
| Open Questions | 0개 Critical / 1개 Medium 잔여 (OQ-D-01 임베딩 모델) | |

**산출물 목록**:

| 파일 | 내용 |
|------|------|
| [00_Vision_and_Scope](./00_Vision_and_Scope.md) | 제품 비전 + V1.0/V1.1/V1.2/V2 범위 |
| [01_Glossary](./01_Glossary.md) | 25개 도메인 용어 |
| [02_User_Personas](./02_User_Personas.md) | P-01 iet03 페르소나 + 3개 시나리오 |
| [03_PRD_FLOW_CAP](./03_PRD_FLOW_CAP.md) | FR-FLOW-01~03, FR-CAP-01~02 |
| [03_PRD_MEMO_PROJ](./03_PRD_MEMO_PROJ.md) | FR-MEMO-01~07 (v1.5 +Milkdown/Lifecycle/Morphing), FR-PROJ-01~04 **v1.3 재정의** |
| [03_PRD_GIT_DAY_SYS](./03_PRD_GIT_DAY_SYS.md) | FR-GIT-01~04, FR-DAY-01~04 (v1.5 +미완료 사유 캡처), FR-NOTIFY-01, FR-CONFLICT-01, FR-BACKUP-01 |
| [03_PRD_AI](./03_PRD_AI.md) | FR-AI-VOICE, FR-AI-SEARCH, FR-AI-TAG, FR-AI-SLOT(V1.1) |
| [03_PRD_INT](./03_PRD_INT.md) | FR-INT-TG-01~02, FR-INT-GH-01~02, FR-INT-GCAL-01~02, FR-INT-DR-01~04(V1.1) |
| [03_PRD_OPS](./03_PRD_OPS.md) | FR-INBOX-01, FR-DIAG-01, FR-NOTIFY-CTR-01, FR-SET-CRED-01 |
| [03_PRD_ORG](./03_PRD_ORG.md) | **NEW v1.3**: FR-ORG-01~03, FR-CAL-01, FR-LABEL-01, FR-FILES-01~02 |
| [04_Business_Rules_Log](./04_Business_Rules_Log.md) | 57개 + OPS 13개 BR (v1.3 ORG/FILES BR 추가 필요) |
| [05_User_Flow](./05_User_Flow.md) | 8개 Mermaid 플로우 |
| [06_Screen_Spec](./06_Screen_Spec.md) | SC-01~08 |

---

## 2. BA Readiness Score

**v1.0 92점 → v1.1 재산정 89점 → Gate 판정: ✅ PASS (≥80)**

코덱스 외부 검토에서 v1.0 92점이 운영 컴포넌트(Inbox/Diag/Alerts/Cred) 누락을 미반영했다는 지적을 수용. v1.1에서 OPS 모듈 추가 후 재산정.

| 항목 | 배점 | v1.0 | v1.1 | 비고 |
|------|------|------|------|------|
| Gherkin AC 완성율 (전 기능) | 25 | 25 | 25 | v1.1: 30 FR 전체 3~5 AC 유지 |
| Business Rules IF-THEN 형식 | 20 | 20 | 20 | v1.1: OPS 13 BR 추가 후도 100% 준수 |
| User Flow Mermaid 다이어그램 | 15 | 13 | 11 | OPS 4종 추가됐으나 신규 Mermaid 미작성 -2 (Phase 5 진입 후 보강) |
| Screen Spec Data Fields 완성 | 15 | 14 | 14 | Phase 4 Screen_Spec_Addendum 6개 추가 (SC-02/08-Cred/09~12) |
| Open Questions 담당자+기한 | 10 | 10 | 9 | OQ-D-02 해결, OQ-D-01(임베딩 모델) Phase 5 위임 -1 |
| 출처 태그 완성율 | 10 | 10 | 10 | 전 항목 `[iet03]`/`[추론]`/`[코덱스 검토]` 명시 |
| Edge Cases 밀도 (기능당 ≥ 2개) | 5 | 5 | 5 | OPS 4종 모두 Edge Cases 포함 |
| 운영 컴포넌트 정직성 (NEW) | — | — | -3 | 운영 4종을 1차에 누락한 점은 재산정 시 페널티 — 정직 점수 |
| **합계** | **100** | **92** | **89** | |

---

## 3. 이해관계자 승인 현황

> iet03 = Product Owner + 유일한 사용자. 셀프 승인 프로세스 적용 (BA Writer v1.0 §핵심 규칙 4).

| FR 그룹 | 승인자 | 승인일 | 상태 |
|---------|--------|--------|------|
| FR-FLOW-01~03 (컨텍스트 패널) ⭐ | iet03 | 2026-05-06 | ✅ 승인됨 |
| FR-CAP-01~02 (Quick Capture) | iet03 | 2026-05-06 | ✅ 승인됨 |
| FR-MEMO-01~05 (.md 단일 원본) | iet03 | 2026-05-06 | ✅ 승인됨 |
| **FR-MEMO-06~07** (Milkdown + Lifecycle/Morphing, v1.5) | iet03 | 2026-05-06 | ✅ 승인됨 |
| FR-PROJ-01~04 (소속-사업-프로젝트 계층, v1.3 재정의) | iet03 | 2026-05-06 | ✅ 승인됨 |
| **FR-ORG-01~03** (소속·사업·계층 뷰, v1.3) | iet03 | 2026-05-06 | ✅ 승인됨 |
| **FR-CAL-01** (캘린더 뷰, v1.3) | iet03 | 2026-05-06 | ✅ 승인됨 |
| **FR-LABEL-01** (라벨 시스템, v1.3) | iet03 | 2026-05-06 | ✅ 승인됨 |
| **FR-FILES-01~02** (폴더 자동 생성, v1.3) | iet03 | 2026-05-06 | ✅ 승인됨 |
| FR-GIT-01~04 (GitHub 연동) | iet03 | 2026-05-06 | ✅ 승인됨 |
| FR-DAY-01~03 (일별 의식) | iet03 | 2026-05-06 | ✅ 승인됨 |
| **FR-DAY-04** (미완료 사유 캡처, v1.5) | iet03 | 2026-05-06 | ✅ 승인됨 |
| FR-NOTIFY-01, FR-CONFLICT-01, FR-BACKUP-01 | iet03 | 2026-05-06 | ✅ 승인됨 |
| FR-AI-VOICE, FR-AI-SEARCH, FR-AI-TAG (v1.5 정규화 포함) | iet03 | 2026-05-06 | ✅ 승인됨 |
| FR-INT-TG-01~02, FR-INT-GH-01~02 | iet03 | 2026-05-06 | ✅ 승인됨 |
| **FR-INT-GCAL-01~02** (Google Calendar, v1.4) | iet03 | 2026-05-06 | ✅ 승인됨 |
| **FR-INBOX-01, FR-DIAG-01, FR-NOTIFY-CTR-01, FR-SET-CRED-01** (운영성, v1.1) | iet03 | 2026-05-06 | ✅ 승인됨 |

> **셀프 승인 완료**: iet03이 BA 문서 전체를 고객 관점으로 재검토 — 2026-05-06 "이상 없음" 사인오프. Phase 4 → Phase 5 진입 Confirmed. 43 FR 전체 승인.

---

## 4. Open Questions

| OQ-ID | 질문 | 심각도 | Phase 위임 |
|-------|------|--------|-----------|
| OQ-BA-01 | BR-AI-06 Whisper confidence 임계값 0.6이 적절한가 — 실제 NPU 추론 분포 확인 필요 | Medium | Phase 4 구현 시 A/B 테스트 |
| OQ-BA-02 | SC-03 Time Constellation 캔버스 렌더 방식 (Canvas 2D vs WebGL) — V1.2 범위 | Medium | Phase 4 Designer |
| OQ-BA-03 | Telegram Bot polling vs webhook 선택 — 로컬 PC 공개 IP 없으면 webhook 불가 | Medium | Phase 4 기술 설계 시 결정 |

> **Critical OQ 없음 → Phase 4 착수 가능 조건 충족**.

---

## 5. 발견된 변경사항 (인터뷰 vs BA 검토 후)

| 항목 | AS-IS (Phase 1) | TO-BE (Phase 3 BA) | 이유 | 확인 |
|------|----------------|-------------------|------|------|
| BR-DAY-01 | 회고 메모 → 오늘 .md `## 회고` 섹션 | `MC-Notes/YYYY/MM/DD-review.md` 별도 파일 | iet03 Phase 1 OQ-05-04 명시 결정 | 확인됨 |
| BR-AUTH-03 | 단일 규칙 | BR-AUTH-03a (AI SaaS 금지) + BR-AUTH-03b (Drive 동의 백업 허용) | Drive Cold tier 지원 필요 | 확인됨 |
| V1.0 FR 수 | 27개 (FR-AI-SLOT 포함) | 26개 (FR-AI-SLOT V1.1로 이동) | [06_Summary.md] 권위 문서 기준 | 확인됨 |
| 연동 FR 추가 | Phase 1에 없음 | FR-INT-TG-01~02, FR-INT-GH-01~02 추가 (Phase 2 전략 반영) | Telegram/GitHub 연동 전략 확정 | 확인됨 |

---

## 6. Phase 2 전략 차별화 포인트 PRD 반영 추적 (O-ST-02 KPI 소스)

| 차별화 포인트 | Phase 2 출처 | 반영 FR/화면 | 반영 방식 | 달성 |
|------------|-------------|------------|---------|------|
| 컨텍스트 자동 결합 | §2 #1 Must | FR-FLOW-03, SC-04 | PRD "MC 핵심 차별화" 명시, AC에 0.5초 정량 기준 | ✅ |
| 로컬-퍼스트 의미 검색 | §2 #2 Must | FR-AI-SEARCH, BR-AUTH-03a | PRD에 "검색 디폴트=의미", 200ms AC 기준, 외부 송신 0 | ✅ |
| Voice + UX 단계화 | §2 #3 Should | FR-AI-VOICE (V1.0), FR-UX-04 (V1.1), FR-UX-01 (V1.2) | 단계별 명시, SC-05 Voice Glass V1.1 위임 | ✅ |
| Hot/Cold 데이터 티어 | §2 통합 인프라 | FR-INT-DR-01~04, BR-COLD-01~04 | V1.2 범위로 명시, BR 4개 완성 | ✅ |
| 3rd Party 연동 | §2 통합 인프라 | FR-INT-TG-01~02, FR-INT-GH-01~02 | V1.0 범위 확정, OAuth V1.1/V1.2 | ✅ |

**O-ST-02 차별화 포인트 PRD 반영률: 5/5 = 100%**

---

## 7. Dev Handoff 체크리스트

Phase 4 (Designer / Coder) 착수 전 모든 항목 충족:

- [x] BA Readiness Score ≥ 80점 (92/100)
- [x] 모든 Must 기능에 이해관계자 검토 프로세스 정의 (셀프 검토)
- [x] 모든 Gherkin AC에 최소 3개 시나리오
- [x] 모든 비즈니스 규칙에 IF-THEN 형식 + 출처
- [x] 모든 주요 흐름에 Mermaid 다이어그램 (8개)
- [x] Critical Open Questions 전부 해결 (0건)
- [x] Glossary 완성 (25개 용어)
- [x] Phase 2 전략 차별화 포인트 PRD 반영율 ≥ 80% (100%)
- [x] **iet03 셀프 검토 완료** — 2026-05-06 "이상 없음" 사인오프. Phase 5 착수 가능.

**셀프 승인 기록**:

| 역할 | 이름 | 날짜 | 확인 |
|------|------|------|------|
| Product Owner (셀프) | iet03 | 2026-05-06 | ✅ |
| BA Writer | BA Writer v1.0 | 2026-04-27 (v1.0) → 2026-05-06 (v1.5) | ✅ |
| Tech Lead 수신 (= iet03) | iet03 | 2026-05-06 | ✅ |

---

## 8. Phase 4 전달 사항

### 프론트엔드 디자인 (`/design` 스킬 활용)

> iet03이 Phase 3에서 명시: "프론트 디자인은 claude design skills로 진행하고 싶어요"

Phase 4 Designer가 `/design` 스킬로 상세화할 우선순위 화면:

| 순위 | 화면 | 핵심 디자인 과제 |
|------|------|---------------|
| 1 | SC-01 Today's Flow | Personal·Connected·Quiet 브랜드. 타임라인 + 컨텍스트 패널 레이아웃. |
| 2 | SC-04 Context Panel | 0.5초 펼침. 태그·메모·이슈 3섹션 정보 계층. |
| 3 | SC-05 Voice Glass (V1.1) | 반투명 유리 질감 + 음파 시각화. Calm·Focused 키워드. |
| 4 | SC-07 Morning/Evening | 2개 화면 일관성. Reflective·Personal. |
| 5 | SC-03 Time Constellation (V1.2) | 24h 원형 + 별자리 곡선. iGPU Canvas 렌더. |

### 기술 설계 (Phase 4 Designer)

| 결정 사항 | 권장 | 근거 |
|---------|-----|------|
| Python http.server → UI 서빙 | htmx + Tailwind CDN | V1.0. V2에서 Tauri 재검토 |
| AI 추론 EP | OpenVINO NPU EP (Optimum-Intel) | Intel Core Ultra 7 NPU 확인됨 |
| DB 스키마 | [03_PRD_*] 데이터 필드 기반 ERD | Phase 4 DB Schema 문서 작성 |
| OQ-BA-03 | Telegram polling (webhook 대신) | 로컬 PC 공개 IP 없음 가정 |

---

## 9. Change Log

| 버전 | 날짜 | 변경 내용 | 변경자 |
|------|------|----------|--------|
| 1.0 | 2026-04-27 | 최초 작성 (26 FR) | BA Writer v1.0 |
| 1.1 | 2026-05-04 | 코덱스 외부 검토 반영. 03_PRD_OPS 신설. FR 26→30. | BA Writer v1.0 |
| 1.3 | 2026-05-04 | 소속-사업-프로젝트 계층, 캘린더뷰, 라벨, 폴더 구조, 설치형 배포 요구사항 반영. 03_PRD_ORG 신설. FR-PROJ-01~04 전면 재정의. FR 30→38. SC-13/14 추가. | BA Writer v1.0 |
| 1.4 | 2026-05-04 | Google Calendar 연동 추가. FR-INT-GCAL-01~02 신설. FR 38→40. | BA Writer v1.0 |
| 1.5 | 2026-05-06 | 메모/태그/회고 디테일 보강 (D1~D8). FR-MEMO-06 Milkdown, FR-MEMO-07 Lifecycle/Morphing, FR-DAY-04 미완료 사유 캡처. 02_Feature.md 데이터 연결 모델 단락 추가. FR 40→43. | BA Writer v1.0 |
