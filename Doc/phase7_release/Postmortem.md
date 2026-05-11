# MC V1.0 Postmortem

**Release**: V1.0  
**작성일**: 2026-05-10  
**기간**: 2026-04-26 ~ 2026-05-10 (14일)  
**작성자**: iet03 (1인 프로젝트)

---

## 1. 결과 요약

| 항목 | 결과 |
|------|------|
| Phase 6 게이트 | **PASS** (P0=0, P1 백로그 5개 모두 해결, AC Pass Rate ≥ 95%) |
| FR 구현률 | 38/43 = 88% (V1.0 스코프) |
| Phase 0~5 KPI 게이트 | 5개 모두 통과 (점수 87~100) |
| 라우터 / 템플릿 | 13개 / 21개 |
| 발견된 P0 버그 | 2건 (B-001 XSS, B-002 XSS) — 모두 fix |
| 발견된 P1 버그 | 5건 (B-003~007) — 모두 fix |

---

## 2. 잘된 점

- **AI_SDLC 정석 진행** — Phase 0~6 게이트 메트릭 모두 충족, 산출물 완비
- **데이터 무결성 우선** — 단일 사용자 도구 NFR 에 맞춰 인증 시스템 회피, 백업·내보내기 우선
- **계층 모델 정합성** — org → biz → project → item → subtask 가 코드와 스키마에서 일관되게 구현
- **하이브리드 컨테이너 (ADR-001)** — core-api/integrations/ai-worker 분리 결정이 코드 구조에 반영됨
- **PRD 핵심 가치 ("컨텍스트 자동 결합") 구현** — context_panel.html + 프로젝트 슬라이드 드로어로 ≤500ms 응답

---

## 3. 못된 점 / 학습

### 3.1 Phase 5 종료 시점에 백로그 5건 잔존
- 모두 P1 (release blocker 가 아닌 quality issue) 이었음
- **원인**: 1인 프로젝트 특성상 unit test 자동화가 약해 회귀 검증이 수동 워크스루 의존
- **개선**: V1.1 부터 주요 데이터 변경 경로(POST/PATCH/DELETE) 에 대해 smoke test 자동화 도입

### 3.2 문서-코드 동기화 lag
- Phase 5 의 `Impl_Summary.md` 가 실제 13 라우터 / 21 템플릿 구현을 반영하지 못한 채 선언적 요약에 머물렀음
- CLAUDE.md 의 변경 이력이 Phase 0 한 줄만 기록됨 (실제 6 phase 진행)
- KPI_HISTORY.md 에 MC 항목 0건 (Phase 0~6 후행 기록 필요)
- **개선**: Phase 게이트 통과 시점에 KPI_HISTORY + CLAUDE.md 변경이력 commit 을 게이트 조건으로 강제

### 3.3 데이터 연결성 갭 발견 (Phase 6 → 즉시 해결)
- B-005 (org 폴더 자동 생성 누락) — PRD 핵심 가치였으나 Phase 5 구현 시 org INSERT 단순 실행에 그침
- B-006 (project archive → item_projects 잔존) — UPDATE status 만 하고 cascade 누락 → flow/export 에 false positive
- B-004 (14일 inbox 만료 부재) — APScheduler 에 미등록
- **공통 원인**: BR-* 표 (IF-THEN 비즈니스 규칙) 의 negative case (실패/만료/cascade) 가 PRD AC 에 포함되었으나 구현 시 happy path 우선
- **개선**: V2 부터 PRD 의 BR 별 acceptance test 한 줄씩 강제 매핑

---

## 4. KPI 결과 (Phase 0~6 후행 기록)

| 날짜 | Phase | KPI | 목표 | 실측 | 결과 |
|------|-------|-----|------|------|------|
| 2026-04-26 | 0 | Research Score | ≥80 | 100 | ✓ |
| 2026-04-26 | 1 | BA Readiness | ≥80 | 100 | ✓ |
| 2026-04-27 | 2 | Strategy Score | ≥80 | 100 | ✓ |
| 2026-05-04 | 3 | BA Handoff | ≥80 | 89 | ✓ |
| 2026-05-04 | 4 | Design Score | ≥80 | 87 | ✓ |
| 2026-05-08 | 5 | Test Coverage (재정의) | 핵심 모듈 smoke | 통과 | ✓ |
| 2026-05-10 | 6 | AC Pass Rate | ≥95% | 95%+ (P1 5건 fix 후) | ✓ |
| 2026-05-10 | 6 | P0/P1 잔존 | 0건 | 0건 | ✓ |

---

## 5. KPI 조정 결정 (V2 적용)

1인 프로젝트 특성 반영:

| KPI ID | 기존 | 신규 (V2 적용) | 사유 |
|--------|------|----------------|------|
| I1-01 단위 테스트 커버리지 | ≥80% | **핵심 모듈 smoke + 데이터 무결성 회귀 100%** | 자동화 인프라 비용 대비 효용 |
| I1-02 PR 크기 평균 | ≤400 lines | **문서-코드 동기화 commit 분리율 ≥80%** | 1인 직선 개발은 PR 개념 약함 |
| L1-03 Postmortem 이슈 등록 | GitHub 이슈 100% | **로컬 `Doc/phase7_release/issues.md` 100%** | GitHub 미사용 시 측정 불가 |
| R1-01 AC Pass Rate | ≥95% (정의 모호) | **"Gherkin AC × Phase 6 수동 워크스루 통과" 명시** | 측정 방식 명확화 |

---

## 6. V2 권고 사항

1. **모바일 캡처 모듈** (V2 우선) — Telegram Bot 채널 재사용
2. **Milkdown 블록 에디터** (FR-MEMO-06) — V1.5 신규 미구현분
3. **Memo Lifecycle 시각화** (FR-MEMO-07) — evolution_count 활용
4. **GitHub rate-limit header 처리** — silently 멈춤 방지
5. **N+1 쿼리 개선** — `_load_biz_projects()` 단일 JOIN 으로 통합

---

## 7. 학습된 원칙 (1인 프로젝트)

- **백로그를 두려워 말 것** — P0=0 만 확보되면 P1 은 V1.1 백로그로 이관 가능
- **문서-코드 동기화는 게이트 조건** — Phase 통과 = KPI 기록 + 변경이력 commit 까지
- **BR 표의 negative case 우선 구현** — happy path 만 구현하면 archive/expire/cascade 가 누락됨
- **V1 은 빠르게 닫고 V2 에서 모듈 추가** — 스코프 인플레이션 방지
