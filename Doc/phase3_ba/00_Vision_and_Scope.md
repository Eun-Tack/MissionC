# Vision and Scope — MC (Mission Control) V1.0

> 문서 ID: VS-MC-1.0
> 작성: 2026-04-27 | BA Writer v1.0
> v1.5 개정: 2026-05-06 — V1.0 범위 30 → 43 FR (v1.1 OPS 4종 + v1.3 ORG/CAL/LABEL/FILES 7종 + v1.4 GCAL 2종 + v1.5 MEMO/DAY 3종)
> 상태: Draft v1.5
> 인풋: [00_Kickoff](../phase1_interview/00_Kickoff.md), [06_Summary](../phase1_interview/06_Summary.md), [00_Strategy_Summary](../phase2_strategy/00_Strategy_Summary.md)

---

## 1. 제품 비전

### 한 줄 정의

> 1인 윈도우 지식노동자가 스케줄·프로젝트·메모·Git 이슈를 한 화면에서 끊김 없이 관리한다. `[iet03]`

### 목표 사용자

iet03 — 1인 윈도우 지식노동자. 복수의 도구 사이를 오가며 컨텍스트를 잃는 문제를 겪고 있으며, 항상 켜놓고 쓸 수 있는 로컬-퍼스트 통합 운영 도구가 필요하다.

### 핵심 가치 제안

| 사용자 | Pain Point | Value | 출처 |
|--------|-----------|-------|------|
| 1인 지식노동자 | 도구 단절 — Notion·Obsidian·GitHub·캘린더 사이를 1,200번 토글 | 항목 클릭 한 번에 연결 컨텍스트(태그·메모·이슈·진척도)가 한 패널에 | `[iet03]` |
| 1인 지식노동자 | 검색이 단어 일치만 — 다른 표현으로 쓴 메모를 못 찾음 | 로컬 NPU 의미 검색 — 뜻이 같은 표현도 찾아냄 | `[iet03]` |
| 1인 지식노동자 | 클라우드 AI 도구 — 본인 데이터가 외부로 송신됨 | 모든 AI 처리가 로컬 NPU — 데이터 외부 송신 0 | `[iet03]` |

---

## 2. 버전별 범위

### V1.0 MVP — In-Scope (43 FR)

#### 핵심 흐름·캡처 (5)
| 기능 영역 | 우선순위 | 관련 FR | 출처 |
|----------|---------|--------|------|
| Today's Flow 메인 뷰 + 캘린더 토글 | Must | FR-FLOW-01/02 | `[iet03]` |
| 컨텍스트 자동 결합 패널 ⭐ | Must | FR-FLOW-03 | `[iet03]` |
| Quick Capture (텍스트 + 태그) | Must | FR-CAP-01/02 | `[iet03]` |

#### 메모·프로젝트 (11) — v1.3 재정의 + v1.5 보강
| 기능 영역 | 우선순위 | 관련 FR | 출처 |
|----------|---------|--------|------|
| .md 단일 원본 + 메타 다중 매핑 | Must | FR-MEMO-01~05 | `[iet03]` |
| **Milkdown 블록 에디터 (v1.5)** | Must | FR-MEMO-06 | `[iet03]` D1 |
| **Memo Lifecycle + Morphing (v1.5)** | Must | FR-MEMO-07 | `[iet03]` D6 |
| 소속-사업-프로젝트 계층 (v1.3) | Must | FR-PROJ-01~04 (재정의), FR-ORG-01~03 | `[iet03]` |

#### 조직·캘린더·라벨·파일 (5) — v1.3 신설
| 기능 영역 | 우선순위 | 관련 FR | 출처 |
|----------|---------|--------|------|
| 일/주/월 캘린더 뷰 (v1.3) | Must | FR-CAL-01 | `[iet03]` |
| 라벨 시스템 (확인필요/블로킹 등) (v1.3) | Must | FR-LABEL-01 | `[iet03]` |
| 폴더 자동 생성 + 파일-단계 매핑 (v1.3) | Must | FR-FILES-01/02 | `[iet03]` |

#### Git·일별 의식 (5) — v1.5 보강
| 기능 영역 | 우선순위 | 관련 FR | 출처 |
|----------|---------|--------|------|
| GitHub PAT + 이슈·PR 조회·생성 | Must | FR-GIT-01~04 | `[iet03]` |
| 아침 프리뷰 / 저녁 회고 / 이월 | Must | FR-DAY-01~03 | `[iet03]` |
| **미완료 사유 캡처 (v1.5)** | Must | FR-DAY-04 | `[iet03]` D4 |

#### 시스템·알림·백업 (3)
| 기능 영역 | 우선순위 | 관련 FR | 출처 |
|----------|---------|--------|------|
| 일정 5분 전 OS Toast 알림 | Must | FR-NOTIFY-01 | `[iet03]` |
| 일정 충돌 경고 | Must | FR-CONFLICT-01 | `[iet03]` |
| JSON export 백업 | Must | FR-BACKUP-01 | `[iet03]` |

#### AI / NPU (3)
| 기능 영역 | 우선순위 | 관련 FR | 출처 |
|----------|---------|--------|------|
| 음성 캡처 (Whisper NPU) | Must | FR-AI-VOICE | `[iet03]` |
| 로컬 의미 검색 (KoE5 NPU) | Must | FR-AI-SEARCH | `[iet03]` |
| 태그 제안 + 자동 정규화 (sim≥0.85) (v1.5) | Should | FR-AI-TAG | `[iet03]` D2 |

#### 외부 연동 (6) — v1.4 GCal 추가
| 기능 영역 | 우선순위 | 관련 FR | 출처 |
|----------|---------|--------|------|
| Telegram Bot 빠른 캡처·알림 | Must | FR-INT-TG-01/02 | `[iet03]` |
| GitHub 이슈 조회·생성 | Must | FR-INT-GH-01/02 | `[iet03]` |
| **Google Calendar 연동 (v1.4)** | Must | FR-INT-GCAL-01/02 | `[iet03]` |

#### 운영성 (4) — v1.1 OPS 모듈 (코덱스 검토 보강)
| 기능 영역 | 우선순위 | 관련 FR | 출처 |
|----------|---------|--------|------|
| Capture Inbox (통합 미확정 큐) | Must | FR-INBOX-01 | `[코덱스 검토]` |
| Diagnostics / Worker Status | Must | FR-DIAG-01 | `[코덱스 검토]` |
| Notification & Retry Center | Must | FR-NOTIFY-CTR-01 | `[코덱스 검토]` |
| Credential Manager (UI) | Must | FR-SET-CRED-01 | `[ADR-005]` |

> **합계: 43 FR** (Phase 4 v1.5 Traceability_Matrix.md 기준)

### V1.1 — 예정

| 기능 | 관련 FR |
|-----|--------|
| Phi-3 mini 슬롯 추출 (자유 텍스트 → 구조화) | FR-AI-SLOT |
| Voice Glass UI 오버레이 | FR-UX-04 |
| Gmail 연동 | FR-INT-GMAIL |
| **Google Drive Cold tier 아카이브** (v1.3 V1.2→V1.1 이관) | FR-INT-DR-01~04 |
| **Reflection Insights / Constellation** (v1.5 D5) | FR-INSIGHTS-01 |
| **Voice Annotation on Memo** (v1.5 D6 ④) | FR-AI-VOICE-02 |

### V1.2 — 예정

| 기능 | 관련 FR |
|-----|--------|
| Time Constellation 뷰 (24h 원형) | FR-UX-01 |

### Out-of-Scope (V1.0)

| 기능 | 제외 이유 | 예정 버전 | 출처 |
|------|----------|----------|------|
| 다중턴 LLM 에이전트 | iGPU 7B 응답 30초+ 위험 | V2 | `[iet03]` |
| RAG 답변 생성 | 의미 검색으로 V1 가치 충족 | V2 | `[추론]` |
| 일일 자동 요약 | 누적 데이터 복잡도·토큰 부담 | 제외 | `[iet03]` |
| 자동 프로젝트 묶음 제안 | 데이터 누적 후·신뢰 위험 | V2 | `[iet03]` |
| 멀티유저·팀 기능 | 1인 도구 | — | `[iet03]` |
| 모바일 지원 | Windows 단독 | — | `[iet03]` |
| WhatsApp 연동 | ToS·비용 문제 | — | `[iet03]` |

---

## 3. 성공 지표

| 지표 | AS-IS | TO-BE | 측정 방법 | 출처 |
|------|-------|-------|---------|------|
| 도구 전환 횟수/일 | ~수십 회 토글 | 주 도구로 수렴 | 주관 체감 (Phase 7 Postmortem) | `[iet03]` |
| 컨텍스트 패널 클릭 응답 | 해당 없음 | ≤ 0.5초 | AC 검증 | `[추론]` |
| 의미 검색 응답 | 해당 없음 | ≤ 200ms (데이터 30개↑) | 성능 테스트 | `[추론]` |

---

## 4. 제약조건

### 기술 제약
- Python 단일 스택 (htmx + Tailwind CDN UI, http.server). Electron 금지. `[iet03]`
- AI 추론 로컬 NPU/iGPU 전용. 외부 SaaS AI API 금지. `[iet03]` (BR-AUTH-03a)
- Windows 11 단독 지원 (V1.0). `[iet03]`

### 비즈니스 제약
- 1인 개발. 예산 없음. OSS 전용.
- 출시 목표: V1.0 MVP 4~6개월 이내 (2026년 하반기 목표). `[추론]`

---

## 5. 가정 및 의존성

### 가정
- iet03의 .md 노트는 로컬 폴더에 저장되어 있으며, LocalDocsHub와 같은 경로를 공유. `[iet03]`
- Intel NPU Driver ≥ 1.5 + OpenVINO ≥ 2024.1 설치 가능. `[추론]`
- Whisper Base ONNX + BGE-small-ko ONNX + Phi-3 mini INT4 합산 ≈ 2.3GB — 32GB 내 여유. `[추론]`

### 외부 의존성

| 의존성 | 제공자 | 리스크 | 출처 |
|--------|--------|--------|------|
| GitHub REST API | GitHub | Rate limit (5000 req/hr, PAT) — 15분 캐시로 완화 | `[추론]` |
| Telegram Bot API | Telegram | 일반적으로 안정적. 국가별 차단 위험 낮음 | `[추론]` |
| Google OAuth (V1.1~) | Google | API 정책 변경. `drive.file` 최소 스코프로 완화 | `[추론]` |

---

## 6. 이해관계자

| 이름 | 역할 | 의사결정 권한 |
|------|------|------------|
| iet03 | Product Owner + 유일한 사용자 + 개발자 | 모든 결정 |

---

## 7. Change Log

| 버전 | 날짜 | 변경 내용 | 변경자 |
|------|------|----------|--------|
| 1.0 | 2026-04-27 | 최초 작성 (15 영역, 30 FR) | BA Writer v1.0 |
| 1.5 | 2026-05-06 | V1.0 범위 13 FR 추가 (OPS/ORG/CAL/LABEL/FILES/GCAL/MEMO-06,07/DAY-04). 30→43 FR. V1.1에 INSIGHTS·Voice Annotation 추가, Drive를 V1.2→V1.1 이관. | BA Writer v1.0 |
