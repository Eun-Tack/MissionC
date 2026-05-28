---
source: ../../MASTER_SPEC.md
source_ids: [FP-1, FP-2, FP-3, FR-RND-01, FR-RND-02, FR-RND-03, FR-RND-04]
generated_at: 2026-05-27
master_version: v1.9-rnd
master_status: Draft
generator: ba-writer
editable: true
sync_mode: Watch
standard_compat: ai-friendly-doc-standard-v1.0
standard_path: 00_Overview/01_Project_Context.md
---

# Project Context - MC Mission Control

## 1. Stakeholders

| 이름 | 역할 | 관심사 | 의사결정 권한 |
|------|------|--------|---------------|
| iet03 | Product Owner, primary user, developer | 로컬 업무 운영, 데이터 신뢰, RnD 검증 | 최종 결정 |
| Codex | AI pair engineer/reviewer | 요구사항 정리, 구현, 리뷰, 테스트 | 제안/구현 보조 |

## 2. Product Context

MC는 개인 업무를 SaaS 도구에 흩뿌리는 대신, 로컬 앱 하나에서 오늘의 흐름, 메모, 일정, 프로젝트, 외부 연동 cache를 운영하려는 제품이다. 현재 코드는 이미 FastAPI + SQLite 기반의 동작 가능한 앱이며, 앞으로의 핵심은 단순 기능 추가가 아니라 “로컬 신뢰성과 AI/RnD 검증 가능성”을 체계화하는 것이다.

## 3. Technical Context

| 항목 | 현재 결정 |
|------|-----------|
| App framework | FastAPI, Jinja2, HTMX |
| Data | SQLite WAL, FTS5, schema migration |
| Secrets | Windows Credential Manager via keyring, optional secret bridge |
| Integrations | GitHub REST, Google Calendar OAuth readonly, Telegram Bot polling |
| AI/RnD | Local embedding, local STT, tag suggestion 후보 |
| Target OS | Windows-first local app |

## 4. Constraints

| 분류 | 내용 |
|------|------|
| Privacy | 개인 업무 데이터와 AI 처리 원천은 기본 로컬이어야 한다. |
| Budget | OSS와 로컬 실행을 우선한다. |
| UX | 단독 사용자 반복 업무에 맞춰 조작 단계를 줄인다. |
| Reliability | 외부 API 실패가 core workflow를 막으면 안 된다. |
| RnD | AI 기능은 실험 기준을 통과하기 전 “제품 기능”으로 약속하지 않는다. |

## 5. Current Risks

| Risk ID | 내용 | 대응 |
|---------|------|------|
| RISK-01 | 외부 sync가 화면 요청에 결합되어 네트워크 지연을 만들 수 있음 | stale cache + manual refresh 설계 검토 |
| RISK-02 | Telegram offset이 메모리 변수라 재시작 후 중복 가능 | DB/settings persistence 필요 |
| RISK-03 | 기존 문서와 구현이 일부 어긋남 | Master Spec 중심으로 추적성 재정렬 |
| RISK-04 | AI 기능의 품질 기준이 아직 정량화되지 않음 | RnD experiment plan 추가 |

