# 경쟁사 분석 — MC

> 작성: Researcher v1.0 / 2026-04-26
> 평가 축: (a) 로컬-퍼스트 / (b) 스케줄·캘린더 / (c) 프로젝트·태스크 / (d) PKM·메모·생각 / (e) Git·외부 연동 / (f) 1인 사용 적합성 / (g) Windows 적합성

---

## 1. 직접 경쟁사 (같은 문제: "스케줄·프로젝트·생각 통합")

| 도구 | 카테고리 | 핵심 강점 | 핵심 약점 (MC 관점) | 비고 |
|------|---------|---------|------------------|------|
| **Notion** | 클라우드 워크스페이스 | 문서·DB·태스크·캘린더 통합. 풍부한 템플릿. 팀 협업 강력. | 클라우드 강제 (로컬-퍼스트 가치 위반). 규모 커지면 성능 저하. iet03 메모(.md)와 분리됨. | 1인 환경에서 과한 도구. |
| **Obsidian + Tasks + Dataview + obsidian-pm** | 로컬 마크다운 + 플러그인 | 로컬-퍼스트 vault. 양방향 링크. 1,000+ 플러그인. Tasks/Dataview로 프로젝트 대시보드 가능. | **조립 부담**, 학습 곡선 가파름. 캘린더·시간 블록 약함. Git 이슈 연동 미약. iet03의 메모가 LocalDocsHub에 이미 있음 → vault 강제 시 충돌. | MC와 가장 가까운 모델. |
| **Logseq** | 로컬 outliner | 로컬-퍼스트 + OSS 무료. 빌트인 태스크 (TODO/DOING/DONE). Daily Journal 진입 강력. | **Outliner 강제** (모든 줄이 블록). 일반 .md 문서·산문 작업과 어색함. 모바일·플러그인 생태계 작음. iet03 메모(LocalDocsHub) 통합 어려움. | "어디 적지?" 마찰 제거 철학은 참고 가치. |
| **Tana** | 클라우드 supertag PKM | Supertag로 모든 줄을 DB 행으로. AI가 그래프 이해. 빠른 입력. | 클라우드 강제. 구독료. 윈도우 앱 미흡. iet03의 .md 자산 사용 불가. | 데이터 모델 패턴은 참고. |
| **Capacities** | 클라우드 객체 PKM | 사람·책·미팅 등 객체 자동 분류. 깔끔한 UI. | 클라우드. 캘린더·태스크 약함. 로컬 .md 비호환. | 객체-우선 사고는 참고. |

---

## 2. 간접 경쟁사 (다른 방식으로 일부만 푸는 도구)

| 도구 | 카테고리 | 푸는 영역 | 안 푸는 영역 |
|------|---------|---------|------------|
| **Sunsama** | 데일리 플래너 | 캘린더 + 외부 태스크 통합 + 주간 계획 + 일과 후 회고 | PKM, 메모, Git 연동, 로컬 |
| **Akiflow** | 데일리 플래너 | Sunsama + 더 많은 통합(Linear/Zapier 3,000+), 시간 블록 강력 | PKM, 메모, 로컬, 모바일 |
| **TickTick / Todoist** | 태스크 매니저 | 태스크 + 알림 + 캘린더 뷰 | PKM, 프로젝트 그래프, Git |
| **Heptabase** | 비주얼 PKM | 화이트보드 + 카드 + 마인드맵 | 캘린더, 태스크, 시간 흐름 |
| **NotePlan** | .md + 캘린더 (Mac 위주) | 마크다운 + 캘린더 통합 | Windows 미흡, 1인용 가격 부담 |

---

## 3. 통합 매트릭스

| 도구 | 로컬 | 캘린더 | 프로젝트 | 메모/.md | Git | 1인 적합 | Windows |
|------|------|--------|---------|---------|-----|--------|--------|
| Notion | ✗ | △ | ◯ | △ | ✗ | △ | ◯ |
| Obsidian + 플러그인 | ◯ | △ (캘린더 플러그인) | △ (조립) | ◯ | ✗ | △ (조립) | ◯ |
| Logseq | ◯ | △ | △ | △ (outliner) | ✗ | ◯ | ◯ |
| Tana | ✗ | △ | ◯ | △ | ✗ | △ | △ |
| Capacities | ✗ | ✗ | △ | △ | ✗ | △ | △ |
| Sunsama | ✗ | ◯ | △ | ✗ | ✗ | ◯ | ◯ |
| Akiflow | ✗ | ◯ | △ | ✗ | ✗ | ◯ | ◯ |
| **MC (목표)** | **◯** | **◯** | **◯** | **◯ (LocalDocsHub 연결)** | **◯** | **◯** | **◯** |

> 모든 셀이 ◯인 도구는 현재 시장에 없음.

---

## 4. 경쟁사가 해결 못한 것 — MC의 기회

1. **로컬-퍼스트 + 스케줄/캘린더 + Git 이슈가 한 화면**
   - Obsidian/Logseq는 캘린더가 약하고 Git 이슈 연동이 거의 없음.
   - Sunsama/Akiflow는 클라우드만, .md 메모 연동 없음.
   - **빈자리 명확.**

2. **본인 메모를 외부에 두면서도 연결되는 모델**
   - Obsidian은 vault에 다 넣어야 함 (LocalDocsHub 별도 운영자에게 마찰).
   - MC는 LocalDocsHub의 .md를 **참조·링크**하는 모델 → 시장에 거의 없는 패턴.

3. **1인 윈도우 사용자의 GPU/NPU 활용**
   - 모든 비교 대상이 클라우드 LLM에 의존 (Notion AI, Tana AI 등) — 데이터 외부 송신.
   - 로컬 GPU/NPU + 본인 데이터로 요약·태깅·음성-노트는 시장에서 누구도 본격적으로 안 함.

4. **스케줄 발생 = 컨텍스트 진입점**
   - 데일리 플래너는 "오늘 할 일"만, PKM은 "지식 그래프"만.
   - "스케줄을 클릭하면 관련 프로젝트·메모·Git 이슈가 같이 뜬다" 패턴은 [iet03]가 직접 원한 것이며, 어떤 도구도 본격 구현 안 함.

---

## 5. 차별화 포인트 가설 (Phase 2 Strategist 검증 대상)

| 가설 | 근거 | Phase 2 검증 방향 |
|------|------|---------------|
| H1: "로컬-퍼스트 + Windows + 1인" 조건에서 (a)~(g) 7축을 모두 만족하는 도구가 없다 | 통합 매트릭스 | 다른 도구 조합으로 이미 풀고 있는 사용자는 어떻게 푸는지 |
| H2: LocalDocsHub와 외부 연결 모델은 vault 강제 모델보다 1인 사용자 마찰이 적다 | iet03 사용 패턴 + Obsidian 학습 곡선 보고 | 다른 사람도 이 패턴을 원하는지(검증은 Phase 1에서 본인 시나리오 기반) |
| H3: 스케줄 = 컨텍스트 진입점 패턴은 데일리 플래너와 PKM 어느 진영에도 없는 자리다 | 시장 매트릭스 | Phase 3 BA에서 화면 흐름 검증 |
| H4: Git 이슈 통합은 1인 개발자/연구자 PKM에서 미충족 욕구다 | 모든 비교 대상에서 약점 | Phase 4 기술 설계에서 GitHub/로컬 git 통합 비용 평가 |

---

## Sources

- [Sugggest — Best Notion Alternatives in 2026 (1)](https://sugggest.com/blog/best-notion-alternatives-2026-1)
- [Sugggest — Best Notion Alternatives in 2026 (2)](https://sugggest.com/blog/best-notion-alternatives-2026-2)
- [G2 — Obsidian vs Notion](https://learn.g2.com/obsidian-vs-notion)
- [Glukhov — Obsidian vs Logseq](https://www.glukhov.org/post/2025/11/obsidian-vs-logseq-comparison/)
- [SoftPicker — Obsidian vs Logseq 2026](https://softpicker.com/obsidian-vs-logseq/)
- [Capacities — Compare](https://capacities.io/compare/)
- [Efficient.app — Sunsama vs Akiflow](https://efficient.app/compare/sunsama-vs-akiflow)
- [Toolfinder — Akiflow vs Sunsama 2026](https://toolfinder.co/comparisons/akiflow-vs-sunsama)
- [GitHub — obsidian-pm (StepanKropachev)](https://github.com/StepanKropachev/obsidian-pm)
- [Obsidian Stats — Project Management Plugins](https://www.obsidianstats.com/tags/project-management)
- [Akiflow — Calendar Task Integration Productivity](https://akiflow.com/blog/calendar-task-management-integration-productivity)
- [Atlasworkspace — Best Second Brain Apps](https://www.atlasworkspace.ai/blog/best-second-brain-apps)
