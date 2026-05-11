# MC V1.0 Release Notes

**릴리즈일**: 2026-05-10  
**프로젝트**: MC (Mission Control)  
**대상**: iet03 (단일 사용자)

---

## 핵심 가치

> 일이 많아 단순 일정 관리로는 정리되지 않는 1인 지식노동자를 위한,  
> **스케줄·프로젝트·문서·생각이 한 컨텍스트 안에서 연결되는** 로컬 운영 도구.

---

## 신규 기능 (V1.0)

### 흐름·캡처
- **Today's Flow** (FR-FLOW-01): 시간순 항목 + Anytime 묶음 메인 뷰
- **컨텍스트 자동 결합 패널** (FR-FLOW-03) ⭐: 항목 클릭 시 ≤500ms 로 프로젝트·태그·메모·이슈 일괄 표시
- **Quick Capture** (FR-CAP-01~02): 한 줄 입력 + 다중 태그 인라인

### AI / NPU
- **음성 캡처** (FR-AI-VOICE): Whisper NPU, ≤3초 응답
- **로컬 의미 검색** (FR-AI-SEARCH): BGE-small NPU, ≤200ms
- **태그 제안** (FR-AI-TAG): 30개 이상 항목에서 활성

### 메모 시스템
- **일자 .md 자동 생성** (FR-MEMO-01): inbox/YYYY/MM/DD.md
- **자유 명명 .md** (FR-MEMO-02), **외부 편집 감지** (FR-MEMO-04)
- **LocalDocsHub 연계** (FR-MEMO-03): 별도 프로세스로 .md 뷰어 위임

### 프로젝트·계층
- **소속·사업·프로젝트 3단 계층** (FR-ORG-01~03, FR-PROJ-01)
- **프로젝트 단계(Stage) 관리** (FR-PROJ-02)
- **GitHub 연동** (FR-PROJ-04, FR-GIT-01~04): 15분 자동 동기
- **Telegram 캡처/알림** (FR-INT-TG-01~02)
- **Google Calendar 연동** (FR-INT-GCAL-01~02)
- **MC-Notes 폴더 자동 생성** (FR-FILES-01): org/biz/project 계층 그대로 디스크에

### 일별 의식
- **아침 프리뷰** (FR-DAY-01), **저녁 회고** (FR-DAY-02), **미완료 이월** (FR-DAY-03)

### 시스템
- **Capture Inbox** (FR-INBOX-01): 통합 미확정 큐, 14일 후 자동 만료
- **Diagnostics & Alerts** (FR-DIAG-01, FR-NOTIFY-CTR-01)
- **JSON Export 백업** (FR-BACKUP-01): Content-Disposition 헤더로 다운로드
- **Credential Manager** (FR-SET-CRED-01): Windows Credential Manager 통합

---

## V1.0 에서 V2 로 이관된 항목

| FR | 내용 | 사유 |
|----|------|------|
| FR-AI-SLOT | 자유 텍스트 구조화 추출 | Phi-3-mini 추가 학습 필요 |
| FR-MEMO-06 | Milkdown 블록 에디터 | UX 차별화 — V1.5 신규였으나 우선순위 조정 |
| FR-MEMO-07 | Lifecycle 시각화 | morphing 애니메이션 — V1.5 신규였으나 후행 |
| FR-DAY-04 | 미완료 사유 7종 | 데이터 수집 후 재평가 |
| FR-INT-DR-* | Google Drive Cold tier | V1.2 |

---

## 알려진 제약

- **단일 사용자 전용**: 인증 시스템 없음 (의도된 NFR)
- **로컬 전용**: 데이터는 SQLite + .md 로컬 보관, 외부 SaaS 미사용
- **Windows 11 데스크톱 전용**: Whisper/BGE NPU 가속 의존

---

## 아키텍처

```
Host (Windows 11)
├── ai-worker  (Python 8001) — Whisper / BGE NPU
└── Docker
    ├── core-api    (FastAPI + htmx + SQLite, 8000)
    └── integrations (Telegram + GitHub + GCal, 8002)
```

---

## V1.0 → V2 권고 우선순위

1. **모바일 캡처 모듈** — Telegram 인프라 재활용
2. **Milkdown 에디터** (FR-MEMO-06)
3. **Memo Lifecycle 시각화** (FR-MEMO-07)
4. **N+1 쿼리 개선** (`_load_biz_projects` 등)
5. **GitHub rate-limit header 처리**

---

## 게이트 통과 증빙

- Phase 0~6 KPI 모두 충족 (`Doc/phase7_release/Postmortem.md` § 4)
- P0/P1 버그 0건 (`Doc/phase7_release/issues.md`)
- Phase 6 Review CONDITIONAL PASS → 2026-05-10 P1 5건 모두 fix 후 PASS 전환
