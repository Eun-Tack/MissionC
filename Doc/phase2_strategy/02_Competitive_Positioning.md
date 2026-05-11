# 경쟁 포지셔닝 — MC

> 프로젝트: MC (Mission Control)
> 작성: 2026-04-26 | Strategist v1.0
> 인풋: [Phase 0 Competitive_Analysis](../phase0_research/02_Competitive_Analysis.md), [01_Differentiation_Strategy](./01_Differentiation_Strategy.md)

---

## 1. 경쟁사 포지셔닝 비교

| 경쟁사 | 포지셔닝 | 핵심 강점 | 핵심 약점 | 주요 타겟 | 출처 |
|-------|--------|---------|---------|--------|------|
| **Notion** | All-in-one 클라우드 워크스페이스 | 문서·DB·태스크 통합, 풍부한 템플릿, 팀 협업 | 클라우드 강제, 규모 시 성능 ↓, .md 미지원, AI는 클라우드 | 팀 / 중소기업 | [Phase0-경쟁사분석] |
| **Obsidian + Plugins** | 로컬-퍼스트 PKM (조립형) | vault, 양방향 링크, 1,000+ 플러그인 | 조립 부담, 학습 곡선 가파름, 캘린더·Git 약함, vault 강제 | 개인 PKM 매니아 | [Phase0-경쟁사분석] |
| **Logseq** | 로컬 outliner PKM | 무료 OSS, 빌트인 태스크, Daily Journal | Outliner 강제, 산문 어색, 모바일/플러그인 작음, .md 외부 통합 어려움 | 개인 (블록 사고형) | [Phase0-경쟁사분석] |
| **Tana / Capacities** | 클라우드 supertag/object PKM | Supertag 스키마 (Tana), 자동 분류 (Capacities) | 클라우드 강제, 캘린더·Git 약함, .md 비호환 | 신규 PKM 사용자 | [Phase0-경쟁사분석] |
| **Sunsama / Akiflow** | 데일리 플래너 (캘린더+태스크) | 외부 도구 통합, 시간 블록, 일과 후 회고 | PKM·메모 부재, 클라우드, Git 미지원 | 1인 일정 관리자 | [Phase0-경쟁사분석] |
| **★ MC** | **1인 윈도우 로컬 통합 운영 도구** | 컨텍스트 자동 결합, 로컬 의미 검색, NPU 활용, 단일 .md + 메타 매핑 | 1인 사용자만, 학습 곡선(V1.2 별자리), 1인 개발 속도, 모바일 X | **1인 윈도우 지식노동자** (대표·연구자·개발자·창업가) | [추론] |

---

## 2. 포지셔닝 갭 분석 (시장 공백)

```
공백 1: 1인 윈도우 로컬 + (스케줄 + 프로젝트 + 외부 .md + Git 이슈) 한 화면
  - 노리는 경쟁사: 없음
  - 우리 접근: V1.0 — 컨텍스트 패널이 전부 한 화면에 결합
  - 근거: [Phase0-경쟁사분석] 통합 매트릭스 — 모든 셀 ◯ 채우는 도구 부재

공백 2: 로컬-퍼스트 + 의미 검색 (FTS 한계 돌파)
  - 노리는 경쟁사: 없음 (Notion AI는 클라우드, Obsidian/Logseq는 FTS만)
  - 우리 접근: V1.0 — BGE-small NPU + sqlite-vec
  - 근거: [Phase0-기술트렌드] NPU sweet spot

공백 3: vault 강제 없는 외부 .md 통합 (LocalDocsHub 패턴)
  - 노리는 경쟁사: 없음
  - 우리 접근: V1.0 — 단일 원본 + 메타 매핑 (BR-MEMO-01)
  - 근거: [iet03] 명시 결정 + [Phase1-갭분석]

공백 4: 1인 윈도우 PKM에서 음성 = 1등 시민
  - 노리는 경쟁사: 없음 (모두 키보드 전제)
  - 우리 접근: V1.0 단순 음성 캡처 → V1.1 Voice Glass UI
  - 근거: [iet03] 도전적 UX + [Phase0-기술트렌드] Whisper NPU
```

---

## 3. 핵심 메시지 (Positioning Statement)

```
MC는 1인 윈도우 지식노동자를 위한 로컬-퍼스트 운영 도구입니다.

Notion(클라우드 종속)·Obsidian(vault 강제)·Sunsama(PKM 부재)와 달리,
스케줄·프로젝트·메모·Git 이슈가 한 화면에서 흐름으로 연결되며,
본인 데이터는 외부에 보내지 않습니다.
```

**풀어쓰기 (Phase 3 PRD Vision 후보, [추론])**:
> 일이 많은 1인 사용자가 도구 사이를 1,200번 토글하는 대신, 한 화면에서 일을 흐름으로 본다. 항목을 클릭하면 관련 프로젝트·.md 메모·GitHub 이슈가 즉시 같은 패널에 펼쳐진다. 본인 메모(.md)는 LocalDocsHub 같은 외부 도구로 자유롭게 운영하면서, MC는 메타데이터로 연결만 한다. AI 기능(음성 캡처·의미 검색)은 모두 노트북 NPU에서 작동해 데이터가 외부로 송신되지 않는다.

---

## 4. 경쟁 대응 시나리오

| 시나리오 | 가능성 | 우리의 대응 | 사전 준비 |
|---------|------|---------|---------|
| **Obsidian이 캘린더·Git 통합 플러그인 강화** | 높음 (이미 일부 플러그인 존재) | (1) 컨텍스트 패널 깊이 ↑ — 단순 통합 이상 (2) 의미 검색은 Obsidian 진입 어려움 (vault 안만) | Phase 4 ADR에서 컨텍스트 패널 확장성 설계 |
| **Logseq가 의미 검색 추가** | 중간 (커뮤니티 요청 누적) | Outliner 강제는 안 변함 — 산문 메모 사용자에 우리가 자연 | Brand keyword "Personal·Connected" 강화 |
| **Notion이 로컬 모드 출시** | 낮음 (수익 모델 충돌) | 출시되면 검토. 단 클라우드 동기 우선 + .md 미지원 약점은 유지 | 즉시 대응 X |
| **Tana/Capacities가 windows 강화 + 가격 낮춤** | 중간 | 클라우드 종속은 안 변함 — 데이터 외부 송신 불가 사용자에게 우리 | Brand keyword "Local·Quiet" 강화 |
| **Sunsama/Akiflow가 PKM 추가** | 낮 (다른 시장 정조준) | 그쪽은 캘린더 중심, 우리는 PKM·Git까지 — 진영 다름 | 무관 |
| **MS Copilot이 Windows 통합 PKM 출시** | 중-높 (Snapdragon X 및 Intel NPU PC 푸시) | Calm·Privacy 강조 — Copilot은 클라우드+광고 의심. 1인 도구로서 단순함 강조 | Brand keyword "Quiet·Privacy" 강화 |

---

## 5. 포지셔닝 검증 체크리스트

- [x] 핵심 메시지가 [iet03] 킥오프 Pain Point ("도구 단절") 직접 연결
- [x] 차별화 포인트 3개 모두 [Phase0-경쟁사분석] 빈자리에서 도출
- [x] 타겟 세그먼트가 [Phase1-사용자] iet03 페르소나 (1인 윈도우 지식노동자)와 일치
- [x] 포지셔닝 리스크 5개 + 대응 전략 명시 ([01_Differentiation_Strategy](./01_Differentiation_Strategy.md) 축 4 참조)
- [x] [추론] 항목 (메시지 풀어쓰기) → Phase 3 BA Writer가 PRD Vision에서 검증

---

## 6. Phase 3 BA Writer로 전달할 포지셔닝 핵심

> 이 메시지는 [00_Strategy_Summary](./00_Strategy_Summary.md)에서 BA Writer 지시로 통합 정리.

- **타겟**: 1인 윈도우 지식노동자
- **카테고리**: 로컬-퍼스트 통합 운영 도구
- **차별점**: 컨텍스트 자동 결합 + 로컬 의미 검색 + 데이터 외부 송신 0
- **브랜드 키워드**: Personal · Local · Connected · Quiet
- **피해야 할 비교**: "Notion 대체" 또는 "Obsidian 대체" 단순 위치 — *역할이 다름*. MC는 *1인 통합 운영*, 그들은 *팀/PKM 매니아용 단일 영역*.
