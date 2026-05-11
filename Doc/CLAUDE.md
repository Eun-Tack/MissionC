# CLAUDE.md — MC (Mission Control) 프로젝트 진입점

> 이 파일은 MC 프로젝트의 Claude 에이전트 진입점입니다.
> AI_SDLC_Standard 프레임워크(`C:\Users\iet03\Documents\Hub\agents\AI_SDLC\`)의 에이전트를 참조합니다.

---

## 프로젝트 기본 정보

| 항목 | 값 |
|------|---|
| 프로젝트명 | MC (Mission Control) |
| 프로젝트 코드 | MC-001 |
| 시작일 | 2026-04-26 |
| 목표 릴리즈일 | TBD (Phase 0 종료 시점에 가설 설정) |
| 현재 Phase | Phase 0: 리서치 & 벤치마킹 |
| 산출물 위치 | `C:\Users\iet03\Documents\Hub\agents\schedule\Doc\` |
| 코드 위치 (예정) | `C:\Users\iet03\Documents\Hub\agents\schedule\` 루트 (Phase 4 이후 결정) |

---

## 에이전트 참조 경로

이 프로젝트에서 사용하는 에이전트 지시문 (절대 경로):

| Phase | 에이전트 | 현재 버전 파일 |
|-------|---------|-------------|
| Phase 0 | Researcher | `C:\Users\iet03\Documents\Hub\agents\AI_SDLC\framework\agents\researcher\current.md` |
| Phase 1 | Interviewer | `C:\Users\iet03\Documents\Hub\agents\AI_SDLC\framework\agents\interviewer\current.md` |
| Phase 2 | Strategist | `C:\Users\iet03\Documents\Hub\agents\AI_SDLC\framework\agents\strategist\current.md` |
| Phase 3 | BA Writer | `C:\Users\iet03\Documents\Hub\agents\AI_SDLC\framework\agents\ba-writer\current.md` |
| Phase 4 | Designer | `C:\Users\iet03\Documents\Hub\agents\AI_SDLC\framework\agents\designer\current.md` |
| Phase 5 | Coder | `C:\Users\iet03\Documents\Hub\agents\AI_SDLC\framework\agents\coder\current.md` |
| Phase 6 | Reviewer | `C:\Users\iet03\Documents\Hub\agents\AI_SDLC\framework\agents\reviewer\current.md` |
| Phase 7 | Analyst | `C:\Users\iet03\Documents\Hub\agents\AI_SDLC\framework\agents\analyst\current.md` |

**에이전트 로드 방법**: `current.md` 열어 현재 버전 확인 → 해당 버전 파일(예: `v1.0.md`) 로드 → 지시문에 따라 Phase 진행.

---

## 프로젝트 컨텍스트

### 이해관계자

```
- iet03 (사용자 본인): Owner / 단독 사용자 / 단독 운영자
  - 주요 관심사: 일이 많아 단순 일정 관리로는 정리되지 않음.
    스케줄·프로젝트·문서·본인 생각이 한 컨텍스트 안에서 연결되길 원함.
  - 배경: 대표/연구/개발 업무를 병행하는 1인 지식노동 환경.
```

> 단일 사용자 프로젝트. 외부 이해관계자 없음.
> 일반화/멀티유저/팀 협업 기능 제안 금지.

### 기술 스택 (가설 — Phase 4에서 확정)

```
- 플랫폼: Windows 10/11 데스크톱 로컬                          [확정]
- Backend / Frontend / DB: 미정                                  [Phase 4]
- 후보 (참고용):
  * Python + SQLite + http.server (기존 프로토타입 패턴)         [추론]
  * Node.js + Express + 마크다운 파일 시스템 (LocalDocsHub 패턴) [추론]
  * Electron 또는 브라우저 단일 페이지                            [추론]
- GPU/NPU 활용 후보: Whisper, Ollama, ONNX Runtime (DirectML/QNN) [추론]
- 외부 연동 후보: Git/GitHub (이슈/진척도), 메일 알림              [추론]
```

### 아키텍처 결정권과 금지 범위

```
- 사람(사용자)이 확정한 결정:
  * 데이터 위치는 로컬만. 외부 SaaS 저장 금지.
  * 단일 사용자. 인증/권한 시스템 금지.
  * LocalDocsHub는 외부 도구로 유지 — MC가 흡수하지 않음 (연결만).
  * 폴더명 schedule는 그대로 두고, 제품/UI/문서에서는 MC로 호칭.

- AI가 임의 결정하면 안 되는 항목:
  * 데이터 저장소 종류 (SQLite vs 파일 vs 둘 다)
  * 외부 SaaS 도입 여부
  * LocalDocsHub 코드 수정 여부
  * 기존 schedule/project_hub.py 재사용 여부
  * 메일/알림 채널 도입 여부

- 변경 시 반드시 ADR이 필요한 항목:
  * 데이터 모델 변경
  * 외부 통합 추가/제거 (Git, 메일, LocalDocsHub 등)
  * GPU/NPU 의존성 도입
```

### 비기능 요구사항 (가설 — Phase 1/3에서 확정)

```
- Reliability/SLO: 로컬 단일 사용자 도구 — 가용성보다 데이터 무결성 우선.
  * 데이터 손실 방지 (백업/내보내기 필수)
  * 의도치 않은 덮어쓰기 방지

- Security: 단일 사용자 → 인증 불요.
  * 단, 외부 연동 시 비밀(GitHub 토큰, 메일 SMTP 등) 평문 저장 금지.
  * 로컬 시크릿 보관 방식은 Phase 4에서 결정.

- Maintainability: 1인 개발/운영.
  * 단순 우선. 외부 의존성 최소화 선호.
  * 모듈 경계 명확. 문서-코드 동기화는 AI_SDLC 글로벌 규칙 따름.

- Compliance: 개인용 — N/A.
  * 단, 본인 메모/아이디어 데이터는 사용자 외 어떠한 외부 전송도 금지.
```

### 테스트 전략 (가설)

```
- 필수 테스트 수준: unit + 핵심 시나리오 smoke
- 커버리지/게이트: 1인 프로젝트 — AI_SDLC 표준 80%는 Phase 4에서 재평가 가능
- 회귀 테스트: 데이터 손실/무결성 관련 버그는 재현 테스트 필수
```

### AI 프롬프트 공통 규칙

```
- 구현 요청 시 반드시 FR/AC/BR ID 포함
- AI는 승인된 설계 문서 범위를 넘는 결정을 내리지 않음
- 모든 코드 변경은 관련 테스트 + 문서 갱신 대상까지 함께 제시
- 보안 영향이 있는 변경은 비밀정보·로그·입력 검증을 함께 검토
- "기존 코드를 살려야 한다"는 가정 금지 (project_hub.py는 참고만)
- 일반화/멀티유저/팀 기능 제안 금지
```

### 기존 시스템 / 연동 대상

```
- LocalDocsHub (외부 도구, 유지)
  * 위치: C:\Users\iet03\Documents\Hub\project\LocalDocsHub
  * 정체: Node.js + Express 기반 로컬 마크다운 뷰어 (marked + mermaid + chokidar)
  * 기능: 로컬 폴더 트리 탐색, MD 렌더, 표/이미지/Mermaid, 상대 링크, PDF 출력
  * MC와의 관계: 사용자의 "생각/아이디어 md" 영역 — MC는 링크/임베드/연계로 통합.
    LocalDocsHub 자체 코드는 MC가 수정하지 않음.

- schedule\project_hub.py (이전 프로토타입, 참고만)
  * 정체: Python + SQLite + vanilla JS, Founder OS 컨셉
  * 처분: 폐기 가능. 영감 자료(에너지 필드, Quick Capture, Vision 등) 추출만.

- Git/GitHub (희망 연동, Phase 1에서 우선순위 확인)
  * 사용자 관리 프로젝트의 이슈/진척도 모니터링이 이상적 시나리오.

- 메일/알림 (희망 연동, P2 가능성)
  * 스케줄 발생 시 알림. 우선순위는 핵심 가치(연결성) 다음.
```

### 핵심 아키텍처 결정 (기존)

```
- LocalDocsHub는 별도 프로세스/포트로 유지. MC가 마크다운 뷰어를 직접 구현하지 않고 LocalDocsHub로 위임 또는 링크.
- MC 데이터 = 본인 생각/메모(.md)는 외부에 두고, MC는 메타데이터/연결만 관리하는 가능성을 Phase 4에서 검토.
```

### 규제 / 컴플라이언스 주의사항

```
- 개인용. 외부 규제 없음.
- 본인 메모/아이디어 데이터는 외부 전송 금지 (LLM 호출 시에도 사용자 명시 동의 필요 — Phase 4 결정).
```

---

## 글로벌 규칙 (모든 Phase 적용)

AI_SDLC_Standard 글로벌 규칙 준수 (`C:\Users\iet03\Documents\Hub\agents\AI_SDLC\CLAUDE.md` 참조):

- 모든 비즈니스 규칙은 IF-THEN 테이블
- 모든 AC는 Gherkin 형식 (최소 3개 시나리오: 정상/예외/경계)
- 모든 Flow는 Mermaid 다이어그램, 화면 목업은 ASCII
- 출처 태깅 필수 (`[iet03]` / `[문서명]` / `[추론]`)
- FR-{모듈}-{번호} ID 전 Phase 추적성 보장
- B2B Vibe Coding 원칙 — 사람이 결정한 범위 안에서 AI 구현
- 문서-코드 동기화 — Class A-D 변경 분류, Co-location, Simultaneous Change, Supersede

---

## Phase별 산출물 경로

| Phase | 산출물 폴더 | Gate |
|-------|-----------|------|
| Phase 0 | `Doc/phase0_research/` | Research Readiness Score ≥ 80점 |
| Phase 1 | `Doc/phase1_interview/` | BA Readiness Score ≥ 80점 |
| Phase 2 | `Doc/phase2_strategy/` | Strategy Readiness Score ≥ 80점 |
| Phase 3 | `Doc/phase3_ba/` | BA Handoff Score ≥ 80점 + 셀프 리뷰 완료 |
| Phase 4 | `Doc/phase4_design/` | Design Readiness Score ≥ 80점 |
| Phase 5 | `Doc/phase5_impl/` | CI 통과 + 커버리지 ≥ 80% (1인 프로젝트 — 재평가 가능) |
| Phase 6 | `Doc/phase6_review/` | AC Pass Rate ≥ 95% + P0/P1 버그 0건 |
| Phase 7 | `Doc/phase7_release/` | 이슈 등록 완료율 100% |

---

## KPI 기록 알림

각 Phase 완료 후 반드시:
1. `C:\Users\iet03\Documents\Hub\agents\AI_SDLC\framework\kpi\KPI_HISTORY.md`에 실측값 기록
2. KPI 미달 항목 GitHub 이슈 등록 (또는 1인 프로젝트라면 로컬 이슈 트래커)
3. Phase 7 완료 후 프레임워크 개선 이슈를 AI_SDLC 레포에 등록

---

## 변경 이력

| 날짜 | Phase | 변경 내용 |
|------|-------|---------|
| 2026-04-26 | Phase 0 시작 | 프로젝트 초기 설정. 킥오프 인터뷰 완료. |
| 2026-04-26 | Phase 0 → 1 | Research Score 100점. 벤치마킹 5개 도구 분석. |
| 2026-04-26 | Phase 1 → 2 | BA Readiness 100점. 출처 태깅 100%, Edge Case 3개/FR. |
| 2026-04-27 | Phase 2 → 3 | Strategy Score 100점. ADR-001 하이브리드 컨테이너 확정. |
| 2026-05-04 | Phase 3 → 4 | BA Handoff 89점. v1.1 OPS PRD 보충. Gherkin AC 100%. |
| 2026-05-04 | Phase 4 → 5 | Design Score 87점. 10 ADR + 3 TS 완성, API 계약 정의. |
| 2026-05-07 | Phase 5 시작 | 12개 모듈 구현 시작. core-api FastAPI + htmx + SQLite. |
| 2026-05-08 | Phase 5 → 6 | 13 라우터 / 21 템플릿 구현. P0 XSS 2건 발견 즉시 fix. |
| 2026-05-08 | Phase 6 | CONDITIONAL PASS — AC ~91%, P0=0, P1 백로그 5건. |
| 2026-05-10 | Phase 6 → 7 | P1 backlog 5건 (B-003~007) 일괄 fix. AC ≥95% 달성, 게이트 PASS. |
| 2026-05-10 | Phase 7 | Postmortem.md / Release_Notes_v1.0.md / issues.md 작성. V1.0 release. |
