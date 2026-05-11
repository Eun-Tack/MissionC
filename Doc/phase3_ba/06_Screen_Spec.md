# 화면 스펙 (Screen Spec) — MC

> 인풋: [04_Screen_Spec.md](../phase1_interview/04_Screen_Spec.md) (Phase 1 ASCII 목업 기반)
> 작성: 2026-04-27 | BA Writer v1.0
> v1.5 개정: 2026-05-06 — SC-09~15 추가 (이전엔 [Screen_Spec_Addendum.md](../phase4_design/Screen_Spec_Addendum.md)에만 존재)
> 픽셀 정확 디자인은 Phase 4 Designer에서. 본 문서는 WHAT 정의.

---

## 화면 목록 (v1.5 — 15개 화면)

### V1.0 코어 (8개)

| Screen ID | 이름 | 관련 FR | 버전 |
|-----------|-----|--------|------|
| SC-01 | Today's Flow | FR-FLOW-01~03, FR-CAP-01~02, FR-INT-GCAL-01/02 | V1.0 |
| SC-02 | Calendar 토글 (간이) | FR-FLOW-02 | V1.0 |
| SC-04 | Context Panel ⭐ | FR-FLOW-03, FR-INT-GH-01/02, FR-MEMO-07 | V1.0 |
| SC-05 | Voice Capture (V1.0 미니멀) | FR-AI-VOICE | V1.0 |
| SC-06 | Project Detail (v1.3 단계 타임라인) | FR-PROJ-01~04, FR-GIT-02~04, FR-LABEL-01 | V1.0 |
| SC-07 | Evening Review / Morning Preview | FR-DAY-01~04 | V1.0 |
| SC-08 | Settings (코어) | FR-BACKUP-01, FR-AI-* | V1.0 |
| SC-08-Cred | Credential Manager (분리) | FR-SET-CRED-01, FR-GIT-01 | V1.0 |

### V1.0 운영·확장 (6개) — v1.1 OPS + v1.3 ORG/CAL

| Screen ID | 이름 | 관련 FR | 버전 |
|-----------|-----|--------|------|
| SC-09 | Capture Inbox (triage) | FR-INBOX-01 | V1.0 |
| SC-10 | Diagnostics / Worker Status | FR-DIAG-01 | V1.0 |
| SC-11 | Notification & Retry Center | FR-NOTIFY-CTR-01, FR-NOTIFY-01 | V1.0 |
| SC-12 | Conflict Resolution | FR-CONFLICT-01 | V1.0 |
| SC-13 | Calendar (전용 일/주/월) | FR-CAL-01, FR-INT-GCAL-01/02 | V1.0 |
| SC-14 | Org-Business-Project 계층 뷰 | FR-ORG-01~03 | V1.0 |

### V1.1 / V1.2 (1개)

| Screen ID | 이름 | 관련 FR | 버전 |
|-----------|-----|--------|------|
| SC-03 | Time Constellation | FR-UX-01 | V1.2 |
| SC-05 (V1.1 Glass) | Voice Glass Overlay | FR-UX-04 | V1.1 |
| SC-15 | Reflection Insights (회고 데이터 시각화) | FR-INSIGHTS-01 | V1.1 |

> **v1.3 변경 적용**: SC-04·SC-06의 데이터 필드 — `item_tag_map` → `item_tags`, "정식 프로젝트" → "프로젝트" (계층 모델). SC-08은 v1.1에서 SC-08-Cred로 토큰 부분이 분리됨.

---

## SC-01: Today's Flow (메인 화면)

### 디자인 차별성 의도

| 항목 | 내용 |
|------|------|
| 목표 인상 키워드 | Connected · Quiet · Operational |
| 경쟁사 대비 차별 포인트 | Notion 사이드바 트리 폭주 X, 컨텍스트 패널이 MC의 시그니처 |
| 핵심 UX 장치 | 항목별 타입 아이콘·상태 배지, Anytime 섹션, Quick Capture 영구 하단 고정 |
| 피해야 할 안티패턴 | 3단 이상 중첩 사이드바, 모달 남발, 알림 배지 과잉 |

### ASCII 목업

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ MC              [Flow*] [Calendar] [Constellation]      🔍 검색     ⚙ 설정   │
├─────────┬────────────────────────────────────────────┬──────────────────────┤
│ 📂 PROJ │  Today — 2026-04-27 (월)                   │  [컨텍스트 패널]      │
│ #mc-dev │  ─────────────────────────────────────     │  항목 클릭 시 펼침   │
│ #ops    │                                             │  ↳ SC-04 참조        │
│ #idea   │  09:00  ★ 팀 조회 미팅     #mc-dev ●todo   │                      │
│         │  11:00  ☐ PR 리뷰          #mc-dev          │                      │
│ ────    │  14:00  📝 아이디어 메모    #idea            │                      │
│ 🏷 TAG  │  15:30  ★ 설계 리뷰        #mc-dev ●doing  │                      │
│ #call   │                                             │                      │
│ #doc    │  ANYTIME ──────────────────────────         │                      │
│         │  ☐ GitHub 이슈 #42 확인    #mc-dev          │                      │
│ ────    │  📝 V1.1 아이디어           #idea            │                      │
│ ➕ 태그  │                                             │                      │
├─────────┴────────────────────────────────────────────┴──────────────────────┤
│ 🎤  ┃  Quick Capture: 무엇이든 입력 — Ctrl+Space로 음성                     │
└──────────────────────────────────────────────────────────────────────────────┘
아이콘 키: ★=일정  ☐=태스크  📝=메모  ●=상태(todo/doing/done)
```

### 데이터 필드

| 필드명 | 타입 | BA PRD 참조 |
|--------|------|-----------|
| items.scheduled_at | datetime nullable | FR-FLOW-01 |
| items.type | enum(schedule/task/memo) | FR-CAP-01 |
| items.status | enum(todo/doing/done/waiting/cancelled) | BR-STATE-01~05 |
| item_tag_map.tag_id | FK | FR-CAP-02 |
| projects.name | string | FR-PROJ-02 |

### 상태별 화면

| 상태 | 표시 |
|------|------|
| 로딩 | 스켈레톤 카드 (타임라인 영역) |
| 빈 상태 | "좋은 아침입니다" + Quick Capture 강조 |
| 에러 | "(오프라인) 마지막 캐시 표시" + 재시도 버튼 |

---

## SC-04: Context Panel (컨텍스트 패널) ⭐ 핵심

### 디자인 차별성 의도

| 항목 | 내용 |
|------|------|
| 목표 인상 키워드 | Instant · Connected · Complete |
| 경쟁사 대비 차별 포인트 | Notion/Obsidian은 클릭 → 별도 페이지 이동. MC는 0.5초 내 같은 화면에 모든 연결 컨텍스트. |
| 핵심 UX 장치 | 섹션 우선순위 — 태그 > 정식 프로젝트 > .md 미리보기 > GitHub 이슈 |
| 피해야 할 안티패턴 | 너무 많은 정보로 패널이 스크롤 지옥이 되는 것 |

### ASCII 목업

```
┌────────────────────────────────────────────────┐
│ ★ 팀 조회 미팅   09:00~09:30   ●todo      [×] │
├────────────────────────────────────────────────┤
│ 태그                                           │
│  [#mc-dev] [#ops]  [+ 태그 추가]              │
├────────────────────────────────────────────────┤
│ 정식 프로젝트                                  │
│  📂 mc-dev — P0  ████████░░ 80%  active       │
├────────────────────────────────────────────────┤
│ .md 메모                                       │
│  📝 2026-04-27.md                              │
│  "조회 미팅 안건: NPU 벤치마크 결과..."        │
│                              [전체 보기 →]     │
├────────────────────────────────────────────────┤
│ GitHub 이슈 (mc-dev)                           │
│  #42 NPU 성능 프로파일링      [open]           │
│  #38 sqlite-vec 연동          [closed]         │
│                  [→ 새 이슈 생성] [모두 보기]  │
└────────────────────────────────────────────────┘
```

### 데이터 필드

| 필드명 | 타입 | BA PRD 참조 |
|--------|------|-----------|
| item_tag_map.tag_id | FK[] | FR-FLOW-03 §3.2 |
| projects.name, priority, progress, status | — | FR-PROJ-02 |
| memos.file_path | string | FR-MEMO-01 |
| github_items.number, title, state | — | FR-GIT-03 |

### 상태별 화면

| 상태 | 표시 |
|------|------|
| 연결 0개 | "아직 연결된 컨텍스트가 없습니다. 태그를 추가해보세요." |
| GitHub API 실패 | "(캐시) 마지막 동기: {시각}" 표시 |
| .md 파일 결손 | "📝 파일 없음 — 외부에서 삭제됨?" |

---

## SC-05: Voice Glass Overlay

### 디자인 차별성 의도

| 항목 | 내용 |
|------|------|
| 목표 인상 키워드 | Calm · Focused · Modern |
| 경쟁사 대비 차별 포인트 | 모든 경쟁사 키보드 전제. MC는 음성 입력이 1등 시민. |
| 핵심 UX 장치 | V1.0: 미니멀 녹음 UI. V1.1: 반투명 유리 패널 + 음파 시각화 (FR-UX-04) |
| 피해야 할 안티패턴 | 전체 화면 블로킹, 알림음, 과도한 애니메이션 |

### ASCII 목업 (V1.0 — 미니멀)

```
┌──────────────────────────────────┐
│  🎤 듣고 있습니다... ──────────  │
│      [●●●●●○○○○○] 음파           │
│                                  │
│  "내일 오전 10시 병원 예약"       │
│                                  │
│  [확인 Enter]  [다시 말하기]      │
│  [텍스트로 입력]                  │
└──────────────────────────────────┘
(SC-01 위에 모달/오버레이로 표시)
```

> V1.1: 반투명 유리 질감 패널 + 실시간 음파 시각화 → Phase 4 Designer에서 `/design` 스킬로 상세화.

### 데이터 필드

| 필드명 | 타입 | BA PRD 참조 |
|--------|------|-----------|
| asr_result.text | string | FR-AI-VOICE §3.2 |
| asr_result.confidence | float | BR-AI-06 |

---

## SC-06: Project Detail (정식 프로젝트 상세)

### 디자인 차별성 의도

| 항목 | 내용 |
|------|------|
| 목표 인상 키워드 | Overview · Controlled · Calm |
| 핵심 UX 장치 | 진척도 바, GitHub 이슈 요약, 연결 항목 타임라인 |
| 피해야 할 안티패턴 | 서브페이지 무한 드릴다운 |

### ASCII 목업

```
┌──────────────────────────────────────────────────────┐
│ ← 뒤로       📂 mc-dev                               │
├──────────────────────────────────────────────────────┤
│ 비전: 1인 Windows 로컬-퍼스트 운영 도구              │
│ 우선순위: P0   상태: active   진척: ██████░░░░ 60%   │
├──────────────────────────────────────────────────────┤
│ GitHub: Eun-Tack/MC                                  │
│  #42 NPU 프로파일링 [open]                           │
│  #39 sqlite-vec 연동 [open]                          │
│  #38 FTS5 fallback   [closed]      [모두 보기]       │
├──────────────────────────────────────────────────────┤
│ 연결 항목 (26개)                                     │
│  ⏰ 2026-04-27 15:30 설계 리뷰      ●doing           │
│  ☐  PR 리뷰                         ●todo            │
│  📝 아키텍처 결정 노트               (메모)          │
│                          [더 보기] [+ 항목 추가]      │
└──────────────────────────────────────────────────────┘
```

### 데이터 필드

| 필드명 | 타입 | BA PRD 참조 |
|--------|------|-----------|
| projects.name, vision, priority, progress, status | — | FR-PROJ-02 |
| projects.github_repo | string | FR-GIT-02 |
| github_items.* | — | FR-GIT-03 |
| items (project 연결) | FK[] | FR-PROJ-02 |

---

## SC-07: Morning Preview / Evening Review

### 디자인 차별성 의도

| 항목 | 내용 |
|------|------|
| 목표 인상 키워드 | Reflective · Personal · Quiet |
| 핵심 UX 장치 | 아침: 오늘 일정 + 이월 항목 한눈에. 저녁: 완료/미완료 구분 + 반성 메모 |
| 피해야 할 안티패턴 | 저녁 회고를 "부담"으로 느끼게 하는 복잡한 폼 |

### ASCII 목업 (아침 프리뷰)

```
┌──────────────────────────────────────────────┐
│  ☀ 좋은 아침입니다, iet03       2026-04-27   │
├──────────────────────────────────────────────┤
│  오늘 일정 (3)                               │
│  09:00 ★ 팀 조회 미팅   #mc-dev             │
│  14:00 ★ 설계 리뷰      #mc-dev             │
│  17:00 ★ 1on1           #ops                │
├──────────────────────────────────────────────┤
│  이월 태스크 (2)                             │
│  ☐ PR 리뷰              #mc-dev  (어제)      │
│  ☐ 문서 업데이트         #doc    (2일 전)    │
├──────────────────────────────────────────────┤
│  어제 마지막 메모                            │
│  "NPU 벤치마크: Whisper Base ≈ 2.1초"       │
├──────────────────────────────────────────────┤
│  Quick Capture: 오늘 할 일 추가...           │
│                              [오늘 시작하기] │
└──────────────────────────────────────────────┘
```

### ASCII 목업 (저녁 회고)

```
┌──────────────────────────────────────────────┐
│  🌙 오늘 회고             2026-04-27 저녁     │
├──────────────────────────────────────────────┤
│  완료 (3)                                    │
│  ✅ 팀 조회 미팅                              │
│  ✅ PR 리뷰                                  │
│  ✅ 문서 업데이트                            │
├──────────────────────────────────────────────┤
│  미완료 (1)                                  │
│  ☐ 설계 리뷰     [내일로↗] [보류⏸] [취소×] │
├──────────────────────────────────────────────┤
│  반성 메모                                   │
│  ┌─────────────────────────────────────┐    │
│  │ 오늘 잘 한 것 / 개선할 것...        │    │
│  └─────────────────────────────────────┘    │
│              [저장] [건너뜀]                 │
└──────────────────────────────────────────────┘
```

### 데이터 필드

| 필드명 | 타입 | BA PRD 참조 |
|--------|------|-----------|
| items (오늘 기준) | date filter | FR-DAY-01 |
| items.status = done/todo | enum | BR-STATE-02/06 |
| review_memo.content | string | BR-DAY-01 |
| review_memo.file_path | string (MC-Notes/YYYY/MM/DD-review.md) | BR-DAY-01 |

---

## SC-08: Settings

### 디자인 차별성 의도

| 항목 | 내용 |
|------|------|
| 목표 인상 키워드 | Trustworthy · Simple · Local |
| 핵심 UX 장치 | 민감 데이터(PAT/토큰)는 저장 버튼 전 마스킹, 연결 상태 실시간 표시 |
| 피해야 할 안티패턴 | 옵션 과잉, 클라우드 연동을 기본값으로 강조 |

### ASCII 목업

```
┌──────────────────────────────────────────────┐
│ ⚙ 설정                               [← 닫기]│
├──────────────────────────────────────────────┤
│ 📁 데이터                                    │
│   MC Notes 폴더: C:\Users\iet03\MC-Notes     │
│   [변경]  [탐색기에서 열기]                  │
├──────────────────────────────────────────────┤
│ 🔗 LocalDocsHub 연결                         │
│   root 경로: [위와 동일 / 직접 입력]         │
│   [경로 복사]                                │
├──────────────────────────────────────────────┤
│ 🐙 GitHub                                    │
│   PAT: ••••••••••••••••  [수정] [검증]       │
│   동기 주기: [5분] [15분*] [30분]            │
│   연결 상태: ✅ 연결됨                        │
├──────────────────────────────────────────────┤
│ 📱 Telegram Bot                              │
│   Bot Token: ••••••••••  [설정]              │
│   연결 상태: ✅ 연결됨                        │
├──────────────────────────────────────────────┤
│ 🤖 AI 모델                                   │
│   Whisper: Base ✅  [NPU 사용 여부: ON]      │
│   임베딩: BGE-small-ko ✅                    │
│   (V1.1) Phi-3 mini: [다운로드]              │
│   백그라운드 인덱싱: ████████░░ 80%          │
├──────────────────────────────────────────────┤
│ 🔔 알림                                      │
│   일정 5분 전 알림: [ON*] [OFF]              │
├──────────────────────────────────────────────┤
│ 💾 백업                                      │
│   [JSON export]  마지막 export: 없음         │
│   (V1.2) Google Drive: [연결]                │
└──────────────────────────────────────────────┘
```

### 데이터 필드

| 필드명 | 타입 | BA PRD 참조 |
|--------|------|-----------|
| settings.notes_root | path | FR-MEMO-01 |
| settings.github_sync_interval | int (minutes) | BR-GIT-02 |
| settings.notification_enabled | bool | BR-NOTIFY-01 |
| credentials.github_pat | masked, Credential Manager | BR-AUTH-02 |
| credentials.telegram_token | masked, Credential Manager | FR-INT-TG-01 |
| ai_models.whisper_status | enum(loaded/loading/not_installed) | BR-AI-08 |
| ai_models.embedding_index_progress | float 0~1 | BR-AI-03 |

### 액션 버튼

| 버튼 | 동작 | 관련 BR |
|------|------|--------|
| PAT 검증 | GitHub API 인증 테스트 | BR-AUTH-02 |
| JSON export | DB 전체 export | BR-BACKUP-01, FR-BACKUP-01 |
| Google Drive 연결 | OAuth 동의 화면 (V1.2) | BR-AUTH-03b |

---

## SC-02, SC-03 요약 (상세는 Phase 4 Designer)

| 화면 | 핵심 요구사항 | 버전 |
|------|------------|------|
| SC-02 Calendar | 같은 SQLite 데이터, 월/주/일 그리드. 항목 클릭 → SC-04 연동. | V1.0 |
| SC-03 Time Constellation | 24시간 원형 + 별자리 곡선. 메인 뷰 토글 (디폴트 OFF). iGPU Canvas 렌더. | V1.2 |

---

## 화면 공통 규칙

| 규칙 | 내용 |
|------|------|
| 응답 시간 | 모든 화면 전환 ≤ 500ms (서버 데이터 없을 시 스켈레톤 우선) |
| 브랜드 톤 | Personal · Local · Connected · Quiet |
| 레이아웃 밀도 | Balanced (과밀 배치 금지 — SC-01 최대 5~7개 태그 사이드바) |
| 강조 방식 | 구조·위계 우선, 색 강조 최소화. 위험 행동(삭제·아카이브)만 경고색. |
| 데이터 가독성 | 상태 배지 일관성 (todo=회색·doing=파란·done=초록·waiting=노란·cancelled=취소선) |

---

## Change Log

| 버전 | 날짜 | 변경 내용 | 변경자 |
|------|------|----------|--------|
| 1.0 | 2026-04-27 | Phase 1 Screen Spec 기반 BA 형식화 + 디자인 의도 섹션 추가 | BA Writer v1.0 |
