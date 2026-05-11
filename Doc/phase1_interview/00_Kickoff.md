# 킥오프: MC (Mission Control)

> 인터뷰 일시: 2026-04-26
> 인터뷰 대상: 내부 기획 (1인 사용자)
> 참석자: iet03 (Owner / 단독 사용자 / 단독 운영자)
> 상태: Confirmed (Phase 0 결과 반영, 신규 결정 없음)

> Phase 0 산출물 인계: [00_Research_Summary.md](../phase0_research/00_Research_Summary.md), [02_Competitive_Analysis.md](../phase0_research/02_Competitive_Analysis.md), [03_Tech_Landscape.md](../phase0_research/03_Tech_Landscape.md)

---

## 문제 정의

**해결하려는 문제**: 스케줄·프로젝트·문서·본인 생각이 도구 사이에서 단절되어, 단순 일정 관리에서 끝나고 작업 컨텍스트가 깨짐. [iet03]

**AS-IS**:
- 일정은 캘린더에, 프로젝트는 별도 도구에, 메모(.md)는 LocalDocsHub에 흩어져 있음 [iet03]
- 도구 사이 이동·검색 비용으로 흐름이 끊김 [iet03 + [Asrify](https://asrify.com/blog/context-switching-costs)]

**TO-BE**:
- 한 화면에서 스케줄·프로젝트 진척도·.md 메모·Git 이슈가 같은 흐름으로 보임 [iet03]
- 스케줄을 클릭하면 관련 프로젝트·문서·이슈가 같이 떠 컨텍스트가 즉시 복원됨 [iet03]

---

## 범위 (V1 가설 — Step 1~5 인터뷰로 확정)

### In-Scope (V1 후보)

| # | 기능 | 우선순위 | 출처 |
|---|------|--------|------|
| 1 | 스케줄·태스크·프로젝트 통합 관리 | Must | [iet03] |
| 2 | LocalDocsHub의 .md 참조/링크 (vault 흡수 X) | Must | [iet03] |
| 3 | Git 이슈/진척도 모니터링 | Should | [iet03] |
| 4 | Quick Capture (한 입력으로 다양한 객체 추가) | Should | [추론 — 시장 패턴, OQ-00-01] |
| 5 | 스케줄·프로젝트 클릭 시 관련 컨텍스트 동시 표시 | Must | [iet03 — 핵심 가치 직접 언급] |

### Out-of-Scope (V1 제외)

| # | 제외 항목 | 제외 이유 | 출처 |
|---|---------|---------|------|
| 1 | 멀티유저 / 팀 협업 | 1인용 도구로 명시 | [iet03] |
| 2 | 클라우드 저장·동기화 | 로컬-퍼스트 가치 | [iet03] |
| 3 | 마크다운 뷰어 직접 구현 | LocalDocsHub로 위임 | [iet03] |
| 4 | 모바일 앱 | Windows 데스크톱만 | [iet03] |

### Next Phase (V2 후보)

| # | 항목 | 비고 |
|---|------|------|
| 1 | GPU/NPU 활용 (Whisper 음성-노트, SLM 요약·태깅) | "활용 방법 제안 환영" — V2 옵션 모듈 [iet03] |
| 2 | 메일/외부 채널 알림 | "최우선은" 표현으로 후순위 명시 [iet03] |
| 3 | 의미 검색 (sqlite-vec 하이브리드) | FTS5만으로 V1 충분 [추론] |

---

## 제약조건

| 구분 | 내용 | 출처 |
|------|------|------|
| 플랫폼 | Windows 10/11 로컬 | [iet03] |
| 사용자 | 단일 사용자 (인증 시스템 금지) | [iet03] |
| 데이터 위치 | 로컬만. 외부 SaaS 저장 금지 | [iet03] |
| 기존 시스템 | LocalDocsHub (외부 도구로 유지, MC가 흡수 X) | [iet03] |
| 일정 | TBD — 1인 프로젝트, 외부 데드라인 없음 | [iet03] |
| 예산/인력 | 1인 (iet03 단독 개발·운영) | [iet03] |
| 규제 | 개인용 — N/A. 단, 본인 메모 외부 송신 금지 | [iet03] |

---

## 성공 기준 (가설)

- [ ] 스케줄을 클릭한 뒤 N초 이내에 관련 프로젝트·메모·이슈가 같은 화면에 뜬다 (N은 [iet03] 인터뷰에서 결정)
- [ ] LocalDocsHub의 .md 폴더를 그대로 둔 채 MC에서 검색·참조 가능하다
- [ ] V1 기능 전체가 외부 네트워크 없이 동작한다 (Git 연동만 예외)

> 정량 기준은 Step 1~2 인터뷰 결과 후 확정.

---

## 이해관계자 목록

| 이름 | 역할 | 의사결정 권한 | 관심사 |
|------|------|------------|--------|
| iet03 | Owner / 단독 사용자 / 단독 운영자 | 높음 (단독 결정) | 연결성, 1인 컨텍스트 통합, 외부 도구 호환 |

---

## 용어 정의 (초기 Glossary)

| 용어 | 정의 |
|------|------|
| MC | Mission Control. 이 프로젝트의 제품명. |
| LocalDocsHub | 사용자가 운영 중인 외부 마크다운 뷰어 (Node.js+Express). MC가 흡수하지 않고 연결만. |
| vault | Obsidian 용어 차용. "모든 .md를 한 폴더에 넣음" — MC는 강제 안 함. |
| FR / BR / AC / OQ | AI_SDLC 표준 ID (Functional Requirement / Business Rule / Acceptance Criteria / Open Question) |

---

## Open Questions

| OQ-ID | 질문 | 담당 | 기한 | 상태 |
|-------|------|------|------|------|
| OQ-00-01 | "연결"의 구체 단위 — 한 화면 구성 형태 (캘린더 중심? 프로젝트 중심? 타임라인 중심? 그래프?) | iet03 | Phase 1 Step 1 | Open |
| OQ-00-02 | 데이터 소유권 — LocalDocsHub 폴더 직접 가리킴 vs MC가 복사 인덱싱 | iet03 | Phase 1 Step 1 | Open |
| OQ-00-03 | "프로젝트"의 한계선 — 모든 일을 프로젝트로 vs 일정 분량 이상만 vs 명시적 승격 | iet03 | Phase 1 Step 1 | Open |
| OQ-00-04 | GPU/NPU V1 포함 여부 (현재 가정: V2 분리) | iet03 | Phase 1 Step 5 | Open |
| OQ-00-05 | Git 인증 방식 — Windows Credential Manager OK? | iet03 | Phase 1 Step 2 | Open |
