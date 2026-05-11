# 리서치 요약 — MC (Mission Control)

> 작성: Researcher v1.0 / 2026-04-26
> Research Readiness Score: **100 / 100점** → Gate 통과 (≥80점)
> 상태: **Phase 0 완료**, Phase 1 Interviewer 인계 준비

---

## 프로젝트 개요

**프로젝트명**: MC (Mission Control)

**한 줄 정의**: 1인 사용자가 스케줄·프로젝트·문서·본인 생각을 한 컨텍스트에 연결해 일을 흐름으로 관리하는 윈도우 로컬 운영 도구. [iet03]

**핵심 가치**: **연결성(Connectedness)** — 스케줄·프로젝트 진척도·메모/.md·Git 이슈가 한 흐름 안에서 보임. [iet03]

---

## 킥오프 기록 (Researcher v1.0 / Step 0)

### 사용자 답변 요약 [iet03]

| 항목 | 답변 |
|------|------|
| 만들고자 하는 것 | 일을 단순 스케줄이 아닌 프로젝트처럼 관리. 문서·정보 연계 가능. 스케줄 알림은 보너스. |
| 해결하려는 문제 | 기존 도구에서 정보 단절, 단순 일정 관리로 끝남. |
| 핵심 가치 | 연결성 — 데이터·프로젝트·스케줄·생각이 연결되면 AI도 자연스럽게 붙일 수 있음. |
| 사용 시나리오 | 스케줄 발생 시 컨텍스트 진입. 프로젝트 진행 시 이슈/진척도. Git 연동(이슈/진척도 모니터링). 본인 메모는 LocalDocsHub의 .md. |
| 제약 | Windows 로컬, 단일 사용자, GPU/NPU 활용은 보너스. |
| 리서치 방향 | 기술·벤치마크·중요 포인트. |

### 리서치 집중 방향 (확정)

1. 연결형 개인 운영 도구의 시장·경쟁사 → `02_Competitive_Analysis.md`
2. 로컬-퍼스트 데이터 모델 & 외부 연동 아키텍처 → `03_Tech_Landscape.md`
3. Windows GPU/NPU 활용 가능 영역 (1인용 시나리오) → `03_Tech_Landscape.md` §5

---

## 핵심 리서치 인사이트

### 이 도메인의 경쟁 구도
시장은 **"all-in-one 클라우드"(Notion/Tana/Capacities)** vs **"조립형 로컬-퍼스트"(Obsidian/Logseq)** vs **"오늘 단위 데일리 플래너"(Sunsama/Akiflow)** 세 진영으로 분리. 각자 다른 슬라이스를 풂. 1인 윈도우 사용자가 (a) 로컬-퍼스트 + (b) 캘린더/스케줄 + (c) 프로젝트 + (d) 외부 .md 메모 + (e) Git 이슈를 한 화면에 두는 도구는 **현재 없음**. (상세: [`02_Competitive_Analysis.md` 통합 매트릭스](./02_Competitive_Analysis.md#3-통합-매트릭스))

### 경쟁사가 해결 못한 것 (MC의 기회)
1. 로컬-퍼스트 + 캘린더 + Git 이슈 동시 만족
2. vault 강제 없이 외부 .md(LocalDocsHub) 그대로 연결
3. 1인 Windows GPU/NPU 활용 시나리오 (다른 도구는 다 클라우드 LLM)
4. 스케줄을 "컨텍스트 진입점"으로 — 클릭 시 관련 프로젝트·메모·이슈가 같이 뜸

### 사용자 Pain Point Top 3
1. 도구 분절로 인한 컨텍스트 단절 (지식노동자 일일 도구 토글 1,200회+, 생산성 손실 40%) [출처: [Asrify](https://asrify.com/blog/context-switching-costs)]
2. 단순 일정 관리에서 끝나 프로젝트 흐름이 안 보임 [iet03 + Sunsama/Akiflow 비교 검증](https://efficient.app/compare/sunsama-vs-akiflow)
3. 본인 생각·아이디어 .md가 일정·프로젝트와 같이 안 떠 컨텍스트 깨짐 [iet03]

---

## Phase 1 Interviewer 브리핑

### 핵심 경쟁 포인트
- **연결성의 깊이**: 같은 화면에 어떤 객체가 같이 뜨는가
- **vault 강제 vs 외부 참조**: Obsidian의 마찰을 어떻게 피하는가
- **Git 통합의 최소 가치**: 시장 누구도 본격 구현 안 했음 → 정의 필요
- **로컬 LLM의 V1 포함 여부**: GPU/NPU는 보너스로 명시 분리

### 반드시 확인해야 할 인터뷰 질문 (10개)

1. **"연결"의 구체 단위** — 스케줄·프로젝트·메모·Git 이슈가 어떤 형태로 한 화면에 떠야 만족스러운가? (사이드바 / 타임라인 / 그래프 / 인박스)
2. **읽기 vs 쓰기 빈도** — Quick Capture 위주인가, 컨텍스트 조회 위주인가?
3. **데이터 소유권 경계** — LocalDocsHub의 .md를 직접 가리키는가, 따로 복사/인덱싱하는가?
4. **Git 연동의 최소 가치** — 이슈 목록만? PR/커밋 활동? 자동 이슈 생성?
5. **알림 임계값** — 어떤 이벤트가 알림 가치 있는가? 모든 일정 vs P0/P1만?
6. **"프로젝트처럼 관리"의 한계선** — 단순 한 가지 일도 프로젝트로? 분량 이상만 승격?
7. **로컬 LLM 의존도** — GPU/NPU 의존 기능이 V1에 들어가도 되는가, V2 분리?
8. **검색 깊이** — V1에서 .md 본문 풀텍스트 검색 필요한가, 메타데이터(제목·태그·링크)만으로 충분한가?
9. **데이터 손실 시나리오** — .md 원본만 살아있으면 OK인가, MC 인덱스 복구도 자동?
10. **Git 인증** — GitHub PAT를 Windows Credential Manager에 저장 OK?

### [추론] — Phase 1에서 검증 필요

| 추론 | 근거 | 확인 질문 |
|-----|------|---------|
| LocalDocsHub의 .md가 사용자의 주 사고 저장소다 | iet03가 직접 언급 | "다른 메모 위치도 있나요?" |
| 사용자는 GitHub 위주이며 로컬 git 레포도 있다 | "Git 등 연동" 언급 | "현재 어떤 Git 호스팅? 로컬 git만 쓰는 레포 있나요?" |
| 메일 알림은 V1 필수 아님 | "최우선은" 표현 | "메일 알림 없이도 V1이 가치 있나요?" |
| GPU/NPU는 V2 보너스 | "활용 방법 제안해주면 땡큐" | "V1에 포함 가치 있는 시나리오?" |

---

## Phase 3 Designer 브리핑

### 업계 표준 기술 스택
- **저장소**: Markdown(source of truth) + SQLite(derived index, FTS5) — 2026 로컬-퍼스트 PKM 지배 패턴
- **그래프 데이터**: Logseq 모델 (DataScript in-memory + SQLite 영속 + Main/Worker 분리)
- **Git API**: Octokit.js(Node) 또는 PyGithub
- **GPU/NPU 경로**: ONNX Runtime + DirectML/QNN (Snapdragon NPU는 Ollama 미지원, ONNX 변환 필수)

### 성능/규모 기준
- 로컬-퍼스트 도구는 vault 규모 수만 노트에서 그래프 뷰가 무거워짐 — UI 워커 분리로 회피
- chokidar 디바운스 1.5초 (커뮤니티 디폴트)
- 하이브리드 검색: textWeight 0.3 + vectorWeight 0.7 (V2)

### 레퍼런스 아키텍처
- Logseq: ClojureScript + DataScript + SQLite + Main/Worker 분리 ([deepwiki](https://deepwiki.com/logseq/logseq))
- MarkdownDB / sqlite-memory / QMD: md + SQLite + 인덱스 패턴
- 자세한 결정 항목 8개: [`03_Tech_Landscape.md` §7](./03_Tech_Landscape.md#7-phase-4-designer용-결정-항목-참고)

### 피해야 할 것 (실패 사례 기반)
- vault 강제 (Obsidian) → 외부 .md 사용자 마찰
- Outliner 강제 (Logseq) → 산문 작업 어색
- Electron + Python sidecar → 패키징·업데이트 복잡 (직접 보고된 안티패턴)
- 클라우드 LLM 강제 (Notion AI) → 본인 메모 외부 송신
- 자세한 실패 사례·안티패턴: [`04_Reference_Cases.md`](./04_Reference_Cases.md)

---

## Research Readiness Score

| 항목 | 배점 | 달성 | 근거 |
|------|------|----|------|
| 시장 규모/트렌드 데이터 출처 | 10 | ✓ | 1,200토글/40%손실/Gartner 60% |
| 경쟁사 3개 이상 심층 분석 | 20 | ✓ | 직접 5 + 간접 5 = 10개 |
| 각 경쟁사의 약점/기회 명시 | 15 | ✓ | 통합 매트릭스 + 기회 4가지 |
| 레퍼런스 아키텍처 2개 이상 | 15 | ✓ | Logseq, MarkdownDB, sqlite-memory, QMD, obsidian-pm |
| 실패 사례 & 교훈 | 10 | ✓ | Dendron/Roam/Bear + 안티패턴 7개 |
| Phase 1 인터뷰어용 핵심 질문 5개 이상 | 15 | ✓ | 10개 |
| Phase 3 Designer용 기술 결정 사항 목록화 | 15 | ✓ | 결정 항목 8개 표 |
| **합계** | **100** | **100** | |

**판정**: ✅ Phase 1 착수 가능 (≥80점)

---

## Phase 1 Interviewer 인계 산출물

- [x] `00_Research_Summary.md` (이 파일)
- [x] `01_Market_Analysis.md`
- [x] `02_Competitive_Analysis.md`
- [x] `03_Tech_Landscape.md`
- [x] `04_Reference_Cases.md`

다음 단계: Interviewer v1.0 로드 → `Doc/phase1_interview/` 산출물 작성. Gate = BA Readiness Score ≥ 80점.
