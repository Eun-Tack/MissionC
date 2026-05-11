# 시장 & 사용자 분석 — MC

> 작성: Researcher v1.0 / 2026-04-26
> 범위: 1인 지식노동자가 스케줄·프로젝트·문서·생각을 통합 관리하는 도구 영역.
> 공식 TAM/시장 규모 분석은 1인용 로컬 도구라 생략. 사용자 행동 패턴과 Pain Point에 집중.

---

## 1. 사용자 행동 패턴 (도메인 전반)

| 지표 | 값 | 출처 |
|------|----|------|
| 지식노동자 일일 도구 토글 횟수 | **1,200회+** | [Asrify — Context Switching Costs](https://asrify.com/blog/context-switching-costs) |
| 도구 전환으로 잃는 생산 시간 | 최대 **40%** | [Asrify](https://asrify.com/blog/context-switching-costs) |
| 코디네이션·커뮤니케이션 오버헤드 비율 | 60% | [The Work Times](https://theworktimes.com/the-hidden-cost-of-tech-overload-how-fragmented-digital-tools-are-eroding-worker-productivity/) |
| 일일 인터럽션 횟수 (메일/메시지/회의) | ~275회 | [Speakwise Blog](https://speakwiseapp.com/blog/knowledge-worker-productivity-statistics) |
| 도구 통합 시 생산성 향상 보고 비율 (2026 예측) | 60% | [Hubstaff / Gartner 인용](https://hubstaff.com/blog/how-many-work-tools-are-too-many/) |

> 위 지표는 팀/조직 환경 통계이지만, **원리는 1인에게도 동일**: 도구 분절 = 컨텍스트 분절. iet03의 핵심 불만 ("정보가 연결 안 됨")은 시장 전반의 검증된 패턴.

---

## 2. 사용자 세그먼트와 Pain Point (검증된 패턴)

### 세그먼트: "조립형 PKM 사용자" (Obsidian/Logseq 사용자가 자주 호소)
- 로컬-퍼스트 + 마크다운 + 양방향 링크의 가치는 인정
- 그러나 **태스크/캘린더/프로젝트 추적**이 약해 플러그인을 직접 조립해야 함
- "Real time investment in setup", "steeper learning curve" — 진입 장벽 [출처: [G2 Obsidian vs Notion](https://learn.g2.com/obsidian-vs-notion), [Sugggest](https://sugggest.com/blog/best-notion-alternatives-2026-1)]
- → **iet03 부합도: 높음** (1인 사용자 + 본인 메모 .md 보유 + 일정/프로젝트 통합 욕구)

### 세그먼트: "Notion 피로감" 사용자
- 모든 게 한 곳에 있다는 약속이 **규모가 커지면 성능 저하**, 클라우드 종속, 검색·DB 한계로 무너짐
- "Notion's all-in-one promise is also its weakness" [출처: [Sugggest](https://sugggest.com/blog/best-notion-alternatives-2026-1), [Sugggest 2](https://sugggest.com/blog/best-notion-alternatives-2026-2)]
- → 로컬-퍼스트로 이동하는 동기 강함. iet03가 직접 언급한 "데이터, 프로젝트, 스케줄 연결"의 클라우드형 답이 Notion이지만 한계 명확.

### 세그먼트: "데일리 플래너 단독 사용자" (Sunsama/Akiflow)
- 캘린더 + 외부 태스크 통합은 잘 됨 (3,000+ 통합 / Linear / Todoist / Gmail)
- 그러나 **PKM·문서·생각과의 연결 부재** — Sunsama/Akiflow는 "오늘 무엇을 할지"에 집중, "왜/맥락/관련 생각" 영역은 비어있음 [출처: [Efficient.app](https://efficient.app/compare/sunsama-vs-akiflow), [Akiflow blog](https://akiflow.com/blog/akiflow-vs-sunsama-comparison)]
- → **MC가 이 영역과 명확히 다른 위치를 잡을 수 있는 지점**: 스케줄을 일정 단독이 아니라 *프로젝트·문서·생각의 진입점*으로 설계.

### iet03 직접 Pain Point (재확인)
1. 스케줄·프로젝트·정보가 도구 사이에서 **단절** [iet03 — 킥오프]
2. 단순 일정 관리에서 끝나 진행 중 프로젝트의 **흐름이 안 보임** [iet03]
3. 본인 생각/아이디어(.md)와 일정/프로젝트가 **같이 안 떠서** 작업 컨텍스트가 깨짐 [iet03]

→ 시장 데이터와 일치. 1인 사용자도 같은 분절 문제를 더 작은 스케일로 겪음.

---

## 3. 사용 시나리오 패턴 (실제 사용자 흐름에서 자주 보이는 패턴)

| 패턴 | 설명 | 출처 |
|------|------|------|
| **Daily Journal 진입** | "어디 적어야 하지?" 마찰을 없앰. 오늘 페이지가 모든 입력의 기본값 | [Logseq 철학](https://www.glukhov.org/post/2025/11/obsidian-vs-logseq-comparison/) |
| **Tasks/Dataview Dashboard** | 마크다운 안에 흩어진 태스크를 쿼리로 모아 대시보드화 | [Sweet Setup](https://thesweetsetup.com/mikes-obsidian-task-management-dashboard-workflow/), [Obsidian Forum](https://forum.obsidian.md/t/20210608-update-my-project-management-workflow-using-obsidian-dataview/18932) |
| **Time-blocking + Triage** | 캘린더에 태스크를 직접 배치하고 일과 후 회고 | [Sunsama](https://efficient.app/compare/sunsama-vs-akiflow) |
| **Object-based 자동 분류** | 사람·책·미팅 등 타입별로 자동 정리 | [Capacities](https://capacities.io/compare/) |
| **Supertag 스키마** | 어떤 줄이든 태그로 DB 행으로 변환 | [Tana via Sugggest](https://sugggest.com/blog/best-notion-alternatives-2026-1) |

→ MC에 시사: **Daily Journal 진입 + Tasks 대시보드 + Time-blocking 일부 + Git/메모 연결**의 조합이 1인용 윈도우 로컬 환경에서 비어있는 자리.

---

## 4. 규제/컴플라이언스

개인용 로컬 도구. 외부 규제 N/A. (외부 SaaS·LLM 호출 시 사용자 명시 동의 — Phase 4에서 결정)

---

## 5. Phase 1 인터뷰어로 가져갈 핵심 발견

1. 시장은 "all-in-one" vs "조립형 로컬-퍼스트" 두 진영으로 분리 — 사용자는 후자에 가까움. **MC는 후자 진영에 위치하되 조립 부담을 줄이는 자리**.
2. Sunsama/Akiflow류가 푸는 "오늘 단위 통합"과 Obsidian/Logseq류가 푸는 "지식 그래프"는 **같은 화면에 같이 있지 않음** — MC의 차별화 후보.
3. Git 이슈/진척도 연동은 **거의 모든 비교 대상에서 1순위 약점**. iet03가 명시적으로 원한 영역과 정확히 겹침 → 차별화 강한 후보.
4. 본인 .md 메모가 LocalDocsHub로 이미 운영 중 → MC는 마크다운 뷰어를 만들지 않고 **연결만** 하는 게 시장 학습과도 일치 (Obsidian처럼 "vault 안에 모든 걸 담는다"는 강요를 피함).

---

## Sources

- [Asrify — Context Switching Costs & Tool Fragmentation](https://asrify.com/blog/context-switching-costs)
- [Asrify — Tool Consolidation in 2026](https://asrify.com/blog/tool-consolidation-trend-2026)
- [Hubstaff — How Many Work Tools Are Too Many?](https://hubstaff.com/blog/how-many-work-tools-are-too-many/)
- [The Work Times — The Hidden Cost Of Tech Overload](https://theworktimes.com/the-hidden-cost-of-tech-overload-how-fragmented-digital-tools-are-eroding-worker-productivity/)
- [Speakwise — Knowledge Worker Productivity Statistics 2026](https://speakwiseapp.com/blog/knowledge-worker-productivity-statistics)
- [Sugggest — Best Notion Alternatives in 2026 (1)](https://sugggest.com/blog/best-notion-alternatives-2026-1)
- [Sugggest — Best Notion Alternatives in 2026 (2)](https://sugggest.com/blog/best-notion-alternatives-2026-2)
- [G2 — Obsidian vs Notion](https://learn.g2.com/obsidian-vs-notion)
- [Glukhov — Obsidian vs Logseq](https://www.glukhov.org/post/2025/11/obsidian-vs-logseq-comparison/)
- [Efficient.app — Sunsama vs Akiflow](https://efficient.app/compare/sunsama-vs-akiflow)
- [Akiflow — Sunsama vs Akiflow Blog](https://akiflow.com/blog/akiflow-vs-sunsama-comparison)
- [Capacities — Compare](https://capacities.io/compare/)
- [Sweet Setup — Obsidian Task Management Dashboard](https://thesweetsetup.com/mikes-obsidian-task-management-dashboard-workflow/)
- [Obsidian Forum — Project Management with Dataview](https://forum.obsidian.md/t/20210608-update-my-project-management-workflow-using-obsidian-dataview/18932)
