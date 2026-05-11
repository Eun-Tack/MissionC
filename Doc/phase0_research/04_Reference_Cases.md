# 레퍼런스 구현 사례 — MC

> 작성: Researcher v1.0 / 2026-04-26
> 목적: MC 설계 시 참고할 만한 OSS 사례와 안티패턴.

---

## 1. 활용 가치 있는 레퍼런스 (OSS)

| 사례 | 무엇을 배울 수 있는가 | 한계/주의 |
|------|------------------|---------|
| **[Logseq](https://github.com/logseq/logseq)** | 로컬-퍼스트 PKM의 풀 OSS 구현. Main/Worker 분리, DataScript 그래프, SQLite 동시 사용. | ClojureScript 학습 곡선 높음. 통째 채택보다 패턴 차용. |
| **[MarkdownDB](https://markdowndb.com)** | .md 폴더를 SQL 테이블처럼 다루는 라이브러리. JS API. | 검색·관계 모델은 직접 추가 필요. |
| **[sqlite-memory](https://github.com/sqliteai/sqlite-memory)** | md + SQLite + 벡터 검색 풀 패턴 참조. | AI 에이전트 메모리용 — UI 없음. 데이터 계층만 차용. |
| **[QMD](https://github.com/ehc-io/qmd)** | 마크다운 KB CLI. FTS + 의미검색 하이브리드 가중치 (0.3/0.7) 디폴트. | CLI 전용. UI는 직접. |
| **[Foam](https://foambubble.github.io/foam/)** | VS Code 위 PKM. 가벼운 구현. | VS Code 종속. MC는 자체 UI 필요 → 참고만. |
| **[obsidian-pm](https://github.com/StepanKropachev/obsidian-pm)** | Obsidian 안에서 Gantt/Kanban/서브태스크 — 마크다운 그대로 저장. | Obsidian 종속. 데이터 모델 패턴(서브태스크/의존성/시간)은 차용 가능. |
| **[Octokit.js](https://github.com/octokit/octokit.js/)** | GitHub REST + GraphQL 클라이언트. PAT/App 인증, 이슈/PR/프로젝트 풀 셋. | GraphQL로 한 번에 묶어 가져오는 패턴 권장 (요청수 절감). |

---

## 2. 안티패턴 — 피해야 할 것

| 안티패턴 | 어디서 보고됐나 | MC가 피하는 방법 |
|---------|----------------|----------------|
| **Vault 강제 (모든 메모를 한 폴더에)** | Obsidian 1인 사용자 진입 마찰 | LocalDocsHub의 .md를 외부 위치 그대로 참조. MC는 메타·연결만. |
| **Outliner 강제 (모든 줄이 블록)** | Logseq 산문 작성 마찰 | 일반 .md 파일 자유 형식 유지. 블록 단위 구조는 선택적 메타데이터로. |
| **Electron + Python sidecar** | "프로세스 2개 패키징·업데이트 복잡" — 직접 보고 안티패턴 | 단일 런타임 선택. V1은 Python http.server 단일 프로세스. |
| **클라우드 LLM 의존** | Notion AI / Tana AI: 본인 메모가 외부로 송신됨 | 로컬 GPU/NPU 옵션. 외부 LLM은 사용자 명시 동의 시만. |
| **"규모 커지면 느려짐"** | Notion 대형 워크스페이스 / Obsidian 대형 vault 그래프 뷰 | DB 분리 (그래프는 인덱스, 본문은 .md). UI 워커 스레드. |
| **VS Code 종속** | Foam, Dendron — UI 자유도 0 | 자체 브라우저 UI 또는 Tauri/Electron. |
| **모바일 우선 무시** (1인용은 데스크톱 충분) | — | V1은 Windows 데스크톱만. 모바일 미고려. |

---

## 3. 실패 사례 / 죽어가는 도구의 교훈

| 도구 | 상태 | 교훈 |
|------|------|------|
| **Dendron** | 메인테이너 활동 감소, 사용자 이탈 (대부분 Logseq/Obsidian로) | 좁은 차별화(dot-namespace 강제)가 진입 장벽이 됨. |
| **Roam Research** | 클라우드 종속 + 가격 + 유출 사고 | 1인용은 로컬-퍼스트 + 데이터 소유권이 안전. |
| **Bear (구버전), Notion 일부 1인 사용자** | 동기화/마이그레이션 어려움 | .md 파일 그대로 + Git 동기화 가능한 형식이 장수. |

---

## 4. Phase 1 Interviewer용 보강 질문 (이 단계에서 추가 도출)

00_Research_Summary.md의 잠정 6개에 더해:

7. **로컬 LLM 의존도** — 로컬 GPU/NPU를 동작 조건에 두는 기능이 V1에 들어가도 되는가, 아니면 모든 핵심 기능은 GPU 없이 작동해야 하는가? (V2 분리 가능?)
8. **검색 깊이** — V1에서 .md 본문 풀텍스트 검색이 필요한가, 메타데이터(제목·태그·링크)만으로 충분한가?
9. **데이터 손실 시나리오** — 전원 차단·디스크 오류 시 우선순위. .md 원본만 살아있으면 OK인가, MC 인덱스 복구도 자동화돼야 하는가?
10. **Git 인증** — GitHub PAT를 Windows Credential Manager에 저장해도 되는가? 또는 다른 방식 선호?

---

## Sources

- [Logseq DeepWiki](https://deepwiki.com/logseq/logseq)
- [Matthew Bellringer — From Dendron to Logseq](https://www.matthewbellringer.com/from-dendron-to-logseq/)
- [Slant — Logseq vs Dendron](https://www.slant.co/versus/39125/41500/~logseq_vs_dendron)
- [Hacker News — Dendron Discussion](https://news.ycombinator.com/item?id=29998680)
- [GitHub — obsidian-pm (StepanKropachev)](https://github.com/StepanKropachev/obsidian-pm)
- [MarkdownDB](https://markdowndb.com)
- [sqlite-memory](https://github.com/sqliteai/sqlite-memory)
- [QMD](https://github.com/ehc-io/qmd)
- [Octokit.js](https://github.com/octokit/octokit.js/)
- [From Electron+Python to Tauri+Rust](https://medium.com/@trivajay259/from-electron-python-to-tauri-rust-why-i-switched-for-desktop-apps-e3f9d1fb575b)
