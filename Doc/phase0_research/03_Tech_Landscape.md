# 기술 트렌드 & 레퍼런스 아키텍처 — MC

> 작성: Researcher v1.0 / 2026-04-26
> 목적: Phase 4 Designer가 기술 결정에 그대로 쓸 수 있는 형태로 정리.
> 결정은 Phase 4에서. 여기서는 검증된 패턴과 옵션만.

---

## 1. 데이터 저장소 패턴 — Markdown + SQLite Hybrid (2026 표준)

로컬-퍼스트 PKM 영역에서 검증된 지배적 패턴:

```
SOURCE OF TRUTH (Markdown 파일)        DERIVED INDEX (SQLite)
─────────────────────────────         ──────────────────────
.md (사용자 친화 / Git-able)    ──→   FTS5 (full-text search)
이미지/첨부                     ──→   sqlite-vec (선택, 의미 검색)
                                       메타·관계 테이블 (links, tags)
```

- **사실 출처 = .md 파일**: Git 호환, 다른 도구로 이동 가능, 사용자가 직접 편집 가능
- **인덱스 = SQLite**: 빠른 검색, 복잡 쿼리, 파일 전체 스캔 회피
- **변경 감지**: `chokidar` (Node) / `watchdog` (Python). 1.5초 디바운스로 연속 저장 묶음 처리.
- 사례: [sqlite-memory](https://github.com/sqliteai/sqlite-memory), [ClawMem](https://github.com/yoloshii/ClawMem), [QMD](https://github.com/ehc-io/qmd), [MarkdownDB](https://markdowndb.com), [memweave](https://towardsdatascience.com/memweave-zero-infra-ai-agent-memory-with-markdown-and-sqlite-no-vector-database-required/)

> **MC 시사점**: LocalDocsHub의 .md를 `source of truth`로 두고, MC는 인덱스만 만든다. 본인 메모를 vault로 흡수하지 않아도 됨.

---

## 2. 그래프/관계 데이터 모델 — Logseq 레퍼런스

| 계층 | 기술 | 역할 |
|------|------|------|
| UI | ClojureScript + Rum (React 래퍼) | 렌더링 |
| In-memory 그래프 | **DataScript** | 블록·페이지 간 양방향 관계, 쿼리 |
| 영속 | **SQLite (sqlite3.wasm)** | 변경사항 저장, 인덱스 |
| 빌드 | Shadow-cljs + Tailwind | 핫 리로딩, CSS |
| 동시성 | **Main thread / DB worker 분리** | UI 블로킹 방지 |

- 출처: [Logseq DeepWiki](https://deepwiki.com/logseq/logseq)
- Main/Worker 분리는 MC도 그대로 적용 가치 있음. 파일 인덱싱이 UI 멈추게 하면 안 됨.

---

## 3. 검색·인덱스

| 방식 | 도구 | 특징 |
|------|------|------|
| Full-text | **SQLite FTS5** | 빌트인. 한국어 토크나이저는 [`sqlite-icu`](https://github.com/simonw/sqlite-fts4) 또는 직접 토큰화. |
| 의미 검색 (선택) | `sqlite-vec` | 임베딩 저장 + 내적/코사인. 외부 API 또는 로컬 임베딩 모델. |
| 하이브리드 | textWeight 0.3 + vectorWeight 0.7 (커뮤니티 디폴트) | MMR 다양화 + 시간 감쇠 |

> V1은 FTS5만으로 충분 가능. 벡터 검색은 V2로 미루는 게 합리적 (사용자 명시 결정 필요).

---

## 4. Git 연동

| 옵션 | 도구 | 비고 |
|------|------|------|
| Node.js | **Octokit.js** (`@octokit/rest`, `@octokit/graphql`) | 모든 GitHub API 커버, 인증 PAT/App, GraphQL로 한 번에 다중 데이터 조회 가능 |
| Python | **PyGithub** | 동등 기능 |
| 로컬 git | `simple-git` (Node) / `git` CLI | 로컬 레포 메타 (커밋 수, 브랜치 등) |

iet03 시나리오는 *본인 GitHub 계정의 이슈/진척도 모니터링* → Octokit.rest로 충분. 인증은 PAT 1개 (로컬 비밀 저장 방식은 Phase 4 결정).

> 출처: [Octokit](https://github.com/octokit), [octokit.js](https://github.com/octokit/octokit.js/)

---

## 5. Windows 로컬 GPU/NPU 활용 가능 영역

### 핵심 사실 (2026-04 기준)

| 항목 | 사실 |
|------|------|
| Ollama | 로컬 LLM 실행에 표준이지만 **Snapdragon X Elite ARM에서는 CPU-only**. NVIDIA/Intel GPU에서는 GPU 가속 OK. |
| Whisper (음성) | **Whisper Base가 NPU에서 동작 가능** (DirectML 경유, ONNX 변환) |
| ONNX Runtime + DirectML | NPU/GPU/CPU 자동 선택. Windows ML의 표준 경로. |
| AnythingLLM + ONNX | "현재 NPU를 실용적으로 풀어내는 유일한 조합" — 2026-04 시점 |
| Phi Silica | NPU에서 컨텍스트 처리에 4.8 mWh — 매우 효율적 |
| 권장 경로 | **ONNX 변환 모델 + ONNX Runtime + DirectML/QNN** |

### MC에 의미 있는 시나리오 (1인 윈도우 사용자)

| 시나리오 | 모델 | 가속 | 가치 vs 복잡도 |
|---------|------|-----|-----------|
| **음성 → 노트 인박스** | Whisper Base/Small (ONNX) | NPU/GPU | 가치 ★★★ / 복잡도 중 |
| **메모 자동 요약·태깅** | Phi-3 / SLM (ONNX) | NPU/GPU | 가치 ★★ / 복잡도 중 |
| **일일 회고 카드 생성** | SLM | NPU/GPU | 가치 ★ / 복잡도 낮 |
| **이미지 무드보드** | SD/SDXL (CUDA만 실용) | GPU | 가치 ★ / 복잡도 높 |

> **V1 권장**: GPU/NPU 의존 기능은 모두 **선택적 모듈**로 분리. 핵심 가치(연결성)는 GPU 없어도 작동해야 함. NPU 활용은 V2 또는 옵션 플러그인으로.

> 출처: [Microsoft DirectML on Copilot+](https://blogs.windows.com/windowsdeveloper/2024/08/29/directml-expands-npu-support-to-copilot-pcs-and-webnn/), [Qualcomm Ollama on WoS](https://www.qualcomm.com/developer/project/ollama-with-windows-on-snapdragon-wos), [Surface Laptop 7 NPU 실측](https://vcfvct.wordpress.com/2025/12/31/running-local-llms-on-a-snapdragon-x-elite-surface-laptop-7-my-journey-to-real-npu-acceleration/), [TechZine — AI Foundry/Windows ML](https://www.techzine.eu/news/applications/131547/the-dust-is-settling-with-ai-on-windows-ai-foundry-windows-ml-and-more/)

---

## 6. 프런트엔드/패키징 옵션

| 옵션 | 설치 크기 | 메모리 | 기존 코드 활용 | MC 적합성 |
|------|---------|--------|----------|---------|
| **Tauri (Rust + WebView2)** | ~2.5MB | 낮음 (네이티브 WebView) | JS/TS 프런트 재사용 | ◯ — 신규 작성 시 1순위 |
| **Electron** | ~85MB | 150~300MB idle | npm 생태계 풍부 | △ — LocalDocsHub와 같은 스택, 단 무거움 |
| **Python `http.server` + 브라우저 (기존 project_hub.py)** | <1MB | 매우 낮음 | 기존 코드 그대로 | ◯ — 의존성 0, 1인 도구로 합리적 |
| **VS Code 확장** | N/A | 0 (VS Code 사용) | LocalDocsHub와 분리 | ✗ — VS Code 종속, 반대 방향 |

> Tauri 플러그인 생태계: 2025-01 47개 → 2026-04 120개로 빠르게 성장 ([출처](https://www.pkgpulse.com/blog/electron-vs-tauri-2026)).
> "Electron + Python sidecar" 조합은 패키징·업데이트 복잡으로 명시적 안티패턴 보고 ([출처](https://medium.com/@trivajay259/from-electron-python-to-tauri-rust-why-i-switched-for-desktop-apps-e3f9d1fb575b)).

---

## 7. Phase 4 Designer용 결정 항목 (참고)

> 이 표는 Phase 4에서 사람(iet03)이 결정. Designer 에이전트는 옵션만 제시.

| 결정 항목 | 후보 | 권장 기본값 |
|---------|------|---------|
| 저장소 패턴 | (a) md + SQLite hybrid (b) SQLite only (c) md only | **(a) hybrid** — 시장 검증 패턴, LocalDocsHub 호환 |
| 파일 감시 | chokidar / watchdog | 프런트 스택과 일치 |
| 검색 | FTS5 (V1) → +sqlite-vec (V2) | **FTS5 only V1** |
| Git 연동 | Octokit / PyGithub / 로컬 git | **Octokit (Node) 또는 PyGithub** — 사용자 의향 따라 |
| 캘린더/알림 | OS 캘린더 연동 / iCal / 메일 SMTP | 메일은 V2, V1은 OS 통지/iCal export |
| 프런트/패키징 | Tauri / Electron / Python http.server | **Python http.server + 브라우저 (V1)** — 가장 빠른 시작, 의존성 0. 차후 Tauri 마이그레이션 가능 |
| GPU/NPU | 없음 / Whisper(NPU) / SLM(NPU·GPU) | **V1 없음**, V2부터 옵션 모듈 |
| 시크릿 저장 | Windows Credential Manager / DPAPI / 평문 | **Windows Credential Manager** (DPAPI 기반) — Phase 4 ADR 필요 |

---

## Sources

- [sqlite-memory (GitHub)](https://github.com/sqliteai/sqlite-memory)
- [ClawMem (GitHub)](https://github.com/yoloshii/ClawMem)
- [QMD (GitHub)](https://github.com/ehc-io/qmd)
- [MarkdownDB](https://markdowndb.com)
- [memweave (Towards Data Science)](https://towardsdatascience.com/memweave-zero-infra-ai-agent-memory-with-markdown-and-sqlite-no-vector-database-required/)
- [Logseq DeepWiki](https://deepwiki.com/logseq/logseq)
- [Octokit](https://github.com/octokit), [octokit.js](https://github.com/octokit/octokit.js/)
- [Microsoft Windows Developer — DirectML on Copilot+ NPU](https://blogs.windows.com/windowsdeveloper/2024/08/29/directml-expands-npu-support-to-copilot-pcs-and-webnn/)
- [Qualcomm — Ollama on Windows on Snapdragon](https://www.qualcomm.com/developer/project/ollama-with-windows-on-snapdragon-wos)
- [Snapdragon X Elite NPU — Real-world Notes](https://vcfvct.wordpress.com/2025/12/31/running-local-llms-on-a-snapdragon-x-elite-surface-laptop-7-my-journey-to-real-npu-acceleration/)
- [TechZine — AI Foundry & Windows ML](https://www.techzine.eu/news/applications/131547/the-dust-is-settling-with-ai-on-windows-ai-foundry-windows-ml-and-more/)
- [Tech Insider — Tauri vs Electron 2026](https://tech-insider.org/tauri-vs-electron-2026/)
- [DoltHub — Electron vs Tauri](https://www.dolthub.com/blog/2025-11-13-electron-vs-tauri/)
- [PkgPulse — Electron vs Tauri 2026](https://www.pkgpulse.com/blog/electron-vs-tauri-2026)
- [From Electron+Python to Tauri+Rust](https://medium.com/@trivajay259/from-electron-python-to-tauri-rust-why-i-switched-for-desktop-apps-e3f9d1fb575b)
