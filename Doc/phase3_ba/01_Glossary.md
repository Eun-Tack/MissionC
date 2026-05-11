# 용어 정의 (Glossary) — MC

> 작성: 2026-04-27 | BA Writer v1.0
> 모든 BA 문서·설계 문서·코드의 용어는 이 Glossary를 따른다.

---

## 비즈니스 용어

| 용어 | 정의 | 동의어/혼용어 | 출처 | 비고 |
|------|------|------------|------|------|
| **항목 (Item)** | MC가 관리하는 최소 단위. 일정·태스크·메모 중 하나의 타입을 가진다. | 할 일, 노트, 일정 | `[iet03]` | 타입은 생성 시 결정되며 변경 가능 |
| **일정 (Schedule)** | 특정 날짜+시간이 지정된 항목. 마감 없이 시간만 있는 경우도 포함. | 이벤트, 약속 | `[iet03]` | |
| **태스크 (Task)** | 완료 여부(done/undone)를 추적하는 항목. 날짜 지정 선택. | 할 일, 체크리스트 | `[iet03]` | |
| **메모 (Memo)** | .md 파일로 저장되는 자유 형식 텍스트 항목. | 노트, 기록 | `[iet03]` | 단일 원본 원칙 |
| **태그 (Tag)** | 항목에 붙이는 분류 레이블. 0~N개 자유 추가. 정식 프로젝트를 포함하는 상위 개념. | 해시태그, 카테고리 | `[iet03]` | `#` 접두어로 인라인 입력 |
| **정식 프로젝트 (Project)** | 메타데이터(비전·우선순위·진척도·상태)가 추가된 특별 태그. 태그의 슈퍼셋. | 프로젝트, 사업 | `[iet03]` | BR-PROJ-02 참조 |
| **컨텍스트 패널 (Context Panel)** | 항목 클릭 시 우측에 펼쳐지는 패널. 연결 태그·.md 메모·GitHub 이슈·진척도를 동시 표시. | 사이드 패널, 인스펙터 | `[iet03]` | MC 핵심 UX 차별화 |
| **Quick Capture** | 앱 어디서든 접근 가능한 단일 입력 창. 텍스트 입력 → 자동 타입 분류 → DB 저장. | 빠른 입력, 인박스 | `[iet03]` | |
| **Inbox** | 타입 분류·태그 미지정 항목의 임시 보관소. | 미분류 | `[추론]` | |
| **Anytime** | 날짜·시간 미지정 항목 묶음. Today's Flow 하단에 표시. | 언제든지, 날짜 없음 | `[추론]` | |
| **Today's Flow** | 오늘의 항목을 시간순으로 나열한 메인 뷰. MC의 기본 시작 화면. | 오늘 뷰, 메인 뷰 | `[iet03]` | SC-01 |
| **Evening Review** | 저녁 회고 화면. 오늘 완료/미완료 항목 복기 + 반성 메모 입력. | 데일리 회고, 리뷰 | `[iet03]` | SC-07 |
| **이월 (Carry-over)** | 미완료 태스크를 다음 날로 넘기는 행위. 원본 row 날짜 변경, 복사본 미생성. | 연기, 미룸 | `[iet03]` | BR-DAY-02 |
| **Hot tier** | 활성 프로젝트의 .md 파일이 로컬에 존재하는 상태. | 활성, 로컬 | `[iet03]` | |
| **Cold tier** | 아카이브된 프로젝트. .md는 Drive에 보존, 로컬 삭제. 메타/태그/벡터는 SQLite에 유지. | 아카이브, 콜드 | `[iet03]` | V1.2 |
| **BA Readiness Score** | Phase 3 완료 품질 게이트 점수. 100점 만점, ≥80점이 Phase 4 착수 조건. | — | `[AI_SDLC]` | |

---

## 기술 용어

| 용어 | 정의 | 관련 FR | 출처 |
|------|------|--------|------|
| **sqlite-vec** | SQLite extension. 벡터(임베딩) 저장·코사인 유사도 검색. MC의 의미 검색 엔진. | FR-AI-SEARCH | `[추론]` |
| **FTS5** | SQLite 내장 전체텍스트 검색. 단어 일치 기반. 의미 검색 비활성(데이터 30개 미만) 시 fallback. | FR-AI-SEARCH | `[추론]` |
| **BGE-small-ko** | 한국어 특화 문장 임베딩 모델 (~120M). ONNX 변환 후 Intel NPU에서 추론. | FR-AI-SEARCH, FR-AI-TAG | `[추론]` |
| **Whisper Base ONNX** | OpenAI Whisper Base 모델 (~74M). 음성 → 텍스트. Intel NPU 가속. | FR-AI-VOICE | `[추론]` |
| **silero-vad** | 음성 활성 구간 탐지 모델. 묵음 구간 자동 커팅. CPU 경량 추론. | FR-AI-VOICE | `[추론]` |
| **Phi-3 mini INT4** | Microsoft Phi-3 mini (~2GB). 자유 텍스트 → JSON 슬롯 단발 추출. V1.1. | FR-AI-SLOT | `[추론]` |
| **NPU (Intel AI Boost)** | Intel Core Ultra 7 355 내장 Neural Processing Unit. 저전력 AI 추론 전용. | FR-AI-* | `[iet03]` |
| **htmx** | HTML에 HTTP 속성을 추가해 서버-사이드 부분 갱신을 구현하는 JS 라이브러리. SPA 없이 인터랙티브 UI 구현. | 전역 | `[추론]` |
| **watchdog** | 파일시스템 변경 감지 Python 라이브러리. 외부 .md 편집 감지 → 인덱스 갱신. | FR-MEMO-04 | `[추론]` |
| **단일 원본 원칙** | .md 파일은 단 하나. MC가 유일한 writer. LocalDocsHub는 read-only viewer. | FR-MEMO-* | `[iet03]` |

---

## 상태값

| 엔티티 | 상태값 | 의미 | 전이 조건 |
|--------|--------|------|---------|
| 태스크 | `todo` | 미완료 대기 | 생성 시 기본값 |
| 태스크 | `done` | 완료 | 체크 클릭 |
| 태스크 | `deferred` | 보류 | 회고에서 "보류" 선택 |
| 태스크 | `cancelled` | 취소 | 삭제 대신 소프트 취소 |
| 정식 프로젝트 | `active` | 진행 중 | 마킹 시 기본값 |
| 정식 프로젝트 | `paused` | 일시 중단 | 수동 변경 |
| 정식 프로젝트 | `completed` | 완료 | 수동 변경 |
| 정식 프로젝트 | `archived` | 아카이브 (Cold tier 전환 가능) | 수동 변경 |
| 파일 위치 | `hot` | 로컬 .md 존재 | 기본값 |
| 파일 위치 | `cold` | Drive 아카이브됨, 로컬 없음 | 아카이브 완료 시 (V1.2) |

---

## 외부 시스템 용어

| 용어 | 시스템 | 정의 |
|------|--------|------|
| **PAT** | GitHub | Personal Access Token. GitHub API 인증에 사용. Windows Credential Manager에 저장. |
| **Bot** | Telegram | iet03가 생성한 Telegram Bot. MC와 메시지를 주고받는 창구. |
| **drive.file scope** | Google Drive | MC가 직접 생성한 파일에만 접근 가능한 OAuth 스코프. Drive 전체 접근 금지. |

---

## Change Log

| 버전 | 날짜 | 변경 내용 | 변경자 |
|------|------|----------|--------|
| 1.0 | 2026-04-27 | 최초 작성 | BA Writer v1.0 |
