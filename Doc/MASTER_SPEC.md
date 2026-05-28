---
project: MC Mission Control
cycle_version: v1.9-rnd
status: Draft
created_at: 2026-05-27
last_confirmed_at: null
locked_at: null
predecessor: Doc/phase7_release/Postmortem.md
backlog_input: Doc/phase6_review/Review_Summary.md
framework: AI_SDLC_Standard v2.0
---

# MASTER_SPEC.md - MC Mission Control

이 문서는 MC의 제품 정의, RnD 가설, 요구사항, 운영 기준을 모으는 단일 진실 원천입니다. 기존 `Doc/phase*` 문서는 상세 근거와 이력으로 유지하고, 앞으로 새 기능과 RnD는 이 문서의 ID를 기준으로 파생 산출물을 갱신합니다.

## 0. Product Essence

### 0.1 Philosophy

MC는 1인 지식노동자가 흩어진 일정, 메모, 프로젝트, 이슈를 한 화면에서 잃어버리지 않고 이어가게 하는 로컬 우선 작업 관제 시스템이다. `[iet03]`

### 0.2 First Principles

| FP-ID | 원칙 | Statement | 출처 |
|-------|------|-----------|------|
| FP-1 | Local-first | 개인 업무 원천 데이터는 기본적으로 로컬 SQLite와 로컬 파일에 남아야 한다. | `[ADR-004]` |
| FP-2 | One operator | 다중 조직용 SaaS보다 1인 운영자의 반복 사용 속도와 회복력을 우선한다. | `[Vision_and_Scope]` |
| FP-3 | Context continuity | 작업, 메모, 일정, GitHub 이슈는 서로 끊긴 카드가 아니라 같은 맥락으로 연결되어야 한다. | `[phase3_ba]` |
| FP-4 | Honest automation | 자동화는 실패를 숨기지 않고 캐시 상태, 동기화 상태, 진단 정보를 사용자에게 보여야 한다. | `[Review_Summary]` |
| FP-5 | RnD before AI promise | AI/NPU 기능은 먼저 측정 가능한 실험으로 검증한 뒤 제품 기능으로 승격한다. | `[추론]` |

### 0.3 Quality Factors

| F-ID | Factor | 정의 | 주요 KPI |
|------|--------|------|---------|
| F-1 | Capture Reliability | 어떤 입력 경로에서도 항목이 유실되지 않고 inbox 또는 items에 도착한다. | capture success rate, duplicate rate |
| F-2 | Context Retrieval | 사용자가 1~2번의 클릭 또는 검색으로 관련 맥락을 회수한다. | context open latency P95, search latency P95 |
| F-3 | Local Trust | 민감한 토큰과 개인 데이터가 평문 저장 또는 불명확한 외부 전송으로 노출되지 않는다. | secret leakage incidents, local-only coverage |
| F-4 | Operational Honesty | 연동/작업자/DB 상태가 진단 화면과 로그로 설명 가능하다. | stale sync count, diagnostic coverage |
| F-5 | RnD Measurability | AI 기능은 모델, 데이터셋, 성공 기준, 실패 기준이 문서화된 실험을 통과해야 한다. | experiment pass rate, rollback rate |

## 1. Project Overview

### 1.1 한 줄 정의

MC는 FastAPI, SQLite, Jinja/HTMX 기반의 로컬 Mission Control 앱으로, 일정/할 일/메모/프로젝트/GitHub/GCal/Telegram 입력을 하나의 운영 화면에 모은다. `[current implementation]`

### 1.2 현재 제품 상태

| 영역 | 현재 상태 | 근거 |
|------|-----------|------|
| Core API | FastAPI 라우터 기반 CRUD, 검색, 캘린더, inbox, hierarchy 구현 | `src/core_api/routers/*` |
| Data | SQLite schema v9, FTS5, settings, caches, inbox, contacts | `Doc/phase4_design/schema/mc_schema.sql`, `migrate.py` |
| Integrations | GitHub/GCal/Telegram 연동 일부 구현, local keyring 사용 | `integrations.py`, `auth.py`, `setup.py` |
| UX | Jinja2/HTMX 화면 중심, 로컬 단독 사용자 흐름 | `templates/*` |
| QA | API/DB smoke test 50개 통과 | `tests/*` |
| RnD | AI worker/NPU/semantic search 고도화는 제품화 전 실험 단계 | `[Impl_Summary]` |

### 1.3 In/Out Scope

| 범위 | 항목 | 상태 |
|------|------|------|
| In | 로컬 할 일/메모/일정/프로젝트 운영 | Built |
| In | Google Calendar 읽기 동기화 | Built, needs UX hardening |
| In | GitHub issue cache | Built, needs rate-limit handling |
| In | Telegram capture | Built, needs offset persistence before active use |
| In | RnD: local AI search, voice capture, tag suggestion | Draft |
| Out | 다중 사용자 SaaS, 모바일 앱, 외부 AI API 의존 기능 | Future |

## 2. OKR and Hypotheses

### 2.1 OKR

| OKR-ID | Objective | Key Result | 측정 방법 |
|--------|-----------|------------|-----------|
| OKR-01 | 하루 업무 맥락 회수 시간을 줄인다 | 주요 화면 P95 500ms 이하, 검색 P95 300ms 이하 | pytest/httpx benchmark |
| OKR-02 | 입력 유실을 줄인다 | quick/inbox/tg/gcal capture 실패율 1% 이하 | DB event count + retry log |
| OKR-03 | 로컬 AI 기능의 제품화 가능성을 검증한다 | voice/search/tag RnD 중 2개 이상 pass | RnD experiment report |
| OKR-04 | 개인 데이터 신뢰 기준을 유지한다 | 토큰 평문 저장 0건, 외부 AI 전송 0건 | code review + diagnostics |

### 2.2 Hypotheses

| HYP-ID | 가설 | 검증 방법 | 우선순위 |
|--------|------|-----------|----------|
| HYP-RND-01 | KoE5/ONNX 기반 로컬 임베딩으로 1인 지식 DB에서 충분한 검색 품질을 얻을 수 있다. | 50개 쿼리 gold set, top-5 hit rate | High |
| HYP-RND-02 | Whisper local STT는 빠른 capture에 충분한 정확도와 지연 시간을 제공한다. | 30개 음성 샘플, WER, latency | Medium |
| HYP-RND-03 | GCal/GitHub on-demand sync는 로컬 단독 사용자에게 우선 충분하지만 stale 상태 표시가 필요하다. | UX observation + stale metric | Medium |
| HYP-RND-04 | Telegram polling은 offset persistence 없이는 활성화 시 중복 capture 위험이 있다. | restart simulation | High before TG launch |

## 3. Requirement Catalog

### 3.1 Functional Requirements

| FR-ID | 기능명 | 의도 | 우선순위 | 상태 |
|-------|--------|------|----------|------|
| FR-CORE-01 | Item CRUD and status update | 할 일/메모/일정의 기본 생성, 수정, 완료 처리를 안정화한다. | Must | Built |
| FR-CAP-01 | Unified capture inbox | quick, Telegram, voice 입력을 한 inbox에서 triage한다. | Must | Built |
| FR-CAL-01 | Local calendar view | 내부 일정과 GCal cache를 일/주/월 화면에서 본다. | Must | Built |
| FR-CAL-02 | Google Calendar OAuth sync | Google Calendar readonly OAuth로 primary calendar를 가져온다. | Must | Built |
| FR-INT-01 | Integration health and credentials | GitHub/TG/GCal 토큰 상태와 테스트 결과를 설정/진단에서 확인한다. | Must | Built |
| FR-OPS-01 | Diagnostics and retry visibility | DB, cache, worker, notification 상태를 설명 가능하게 보여준다. | Must | Built |
| FR-RND-01 | Local semantic search experiment | 로컬 임베딩 검색의 품질/성능/운영 비용을 검증한다. | Should | Draft |
| FR-RND-02 | Local voice capture experiment | 로컬 STT capture의 정확도와 UX 지연 시간을 검증한다. | Should | Draft |
| FR-RND-03 | AI tag suggestion experiment | 태그 정규화/추천이 수동 분류 부담을 줄이는지 검증한다. | Could | Draft |
| FR-RND-04 | Sync hardening experiment | 연동을 캐시/stale/수동 갱신 중심으로 개선할지 판단한다. | Should | Draft |

### 3.2 Business Rules

| BR-ID | IF | THEN | 연결 FR | 우선순위 |
|-------|----|------|---------|----------|
| BR-SEC-01 | 토큰/refresh token을 저장해야 한다면 | `.env`가 아니라 keyring/secret bridge에 저장한다. | FR-INT-01 | Must |
| BR-CAP-01 | 외부 입력 처리가 실패하면 | 사용자 데이터는 버리지 않고 retry 또는 inbox pending 상태로 남긴다. | FR-CAP-01 | Must |
| BR-CAL-01 | GCal API가 실패하면 | 화면은 마지막 cache를 보여주고 실패 상태를 기록한다. | FR-CAL-02 | Should |
| BR-RND-01 | AI 기능이 pass 기준을 충족하지 못하면 | 제품 기본 흐름에 넣지 않고 fallback/manual flow를 유지한다. | FR-RND-* | Must |
| BR-RND-02 | AI 모델이 외부 API 전송을 요구하면 | V1 로컬 AI 기능 범위에서 제외한다. | FR-RND-* | Must |

### 3.3 UI Catalog

| UI-ID | 화면 | 주요 요소 | 연결 FR |
|-------|------|-----------|---------|
| UI-FLOW-01 | Today's Flow | item list, context panel, quick capture | FR-CORE-01, FR-CAP-01 |
| UI-INBOX-01 | Capture Inbox | pending/processed list, accept/reject | FR-CAP-01 |
| UI-CAL-01 | Calendar | day/week/month grid, gcal cache | FR-CAL-01, FR-CAL-02 |
| UI-SET-01 | Settings | credentials, folders, orgs, tags/labels | FR-INT-01 |
| UI-DIAG-01 | Diagnostics | DB stats, credential status, last sync | FR-OPS-01 |
| UI-RND-01 | RnD Console | experiment status, dataset, results | FR-RND-* |

## 4. Operations Catalog

### 4.1 SLO

| SLO-ID | 지표 | 목표 | 연결 FR |
|--------|------|------|---------|
| SLO-01 | Core page P95 latency | 500ms 이하 | FR-CORE-01 |
| SLO-02 | Search P95 latency | 300ms 이하 for local FTS, 800ms 이하 for semantic | FR-RND-01 |
| SLO-03 | Capture loss rate | 1% 이하 | FR-CAP-01 |
| SLO-04 | Secret plaintext incidents | 0건 | FR-INT-01 |

### 4.2 Incident Severity

| Severity | 정의 | 예시 |
|----------|------|------|
| SEV1 | 앱 시작 불가 또는 DB 손상 | migration failure, startup crash |
| SEV2 | 주요 workflow 실패 | item update 422, GCal token mismatch |
| SEV3 | 특정 연동/화면 기능 실패 | Telegram 중복, stale sync |
| SEV4 | 문구/로그/문서 불일치 | 자동 갱신 문구 불일치 |

## 5. Dependency Graph

| Source ID | Target Artifact | Sync Mode |
|-----------|-----------------|-----------|
| FR-RND-01 | Doc/phase3_ba/features/FR-RND-01_Local_AI_Search.md | Auto |
| FR-RND-02 | Doc/phase3_ba/features/FR-RND-02_Local_Voice_Capture.md | Auto |
| FR-RND-* | Doc/phase4_design/RnD_Architecture_and_Experiment_Plan.md | Auto |
| BR-SEC-01 | Doc/phase4_design/ADR/ADR-005_Secret_Storage_Policy.md | Watch |
| BR-CAL-01 | src/core_api/integrations.py, src/core_api/routers/calendar.py | Manual |

## 6. Change Log

| 날짜 | 변경 ID | 분류 | 내용 |
|------|---------|------|------|
| 2026-05-27 | CHG-MASTER-001 | Class B | AI_SDLC v2.0 형식의 Master Spec 추가 |
| 2026-05-27 | CHG-RND-001 | Class B | Local AI/Search/Voice/Tag/Sync hardening RnD track 정의 |

## 7. Open Questions

| OQ-ID | 질문 | 심각도 | 상태 |
|-------|------|--------|------|
| OQ-RND-01 | semantic search gold set을 어떤 실제 메모/업무 데이터로 구성할 것인가? | High | Open |
| OQ-RND-02 | voice capture의 최소 허용 WER와 latency 기준은 얼마인가? | Medium | Open |
| OQ-RND-03 | GCal/GitHub sync를 언제 background job으로 되돌릴 것인가? | Medium | Open |
| OQ-RND-04 | Telegram 활성화 전 offset을 DB에 저장할 테이블/setting key는 무엇으로 할 것인가? | High | Open |

