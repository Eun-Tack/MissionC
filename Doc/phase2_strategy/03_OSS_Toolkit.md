# OSS 툴킷 & 기술 스택 — MC

> 프로젝트: MC (Mission Control)
> 작성: 2026-04-27 | Strategist v1.0
> 인풋: [Phase 0 Tech_Landscape](../phase0_research/03_Tech_Landscape.md), [Phase 1 Feature](../phase1_interview/02_Feature.md)

---

## 1. 스택 원칙

| 원칙 | 내용 |
|-----|-----|
| **Python 단일 스택** | Electron+Python sidecar 안티패턴 금지. UI = htmx + Tailwind CDN (Python http.server 서빙) |
| **로컬-퍼스트** | AI 추론·데이터 모두 로컬. 외부 SaaS 추론 금지 (BR-AUTH-03a) |
| **NPU 우선** | Intel Core Ultra 7 355 NPU → Whisper + BGE-small-ko + Phi-3 mini (ONNX Runtime EP) |
| **최소 의존** | 라이브러리 추가 기준: (1) 없으면 직접 구현이 100줄 이상, 또는 (2) 성능 임계값을 못 맞춤 |

---

## 2. 핵심 라이브러리 목록

### 2.1 데이터 레이어

| 라이브러리 | 버전 기준 | 용도 | 비고 |
|-----------|---------|-----|-----|
| **sqlite3** | stdlib | 메인 DB — 태스크·프로젝트·메타데이터 | .md 원본과 분리된 메타 매핑 |
| **sqlite-vec** | ≥ 0.1.6 | 벡터 검색 (의미 검색 인덱스) | sqlite3 extension로 로드; FTS5 fallback |
| **watchdog** | ≥ 4.0 | .md 파일 변경 감지 (LocalDocsHub 연동) | inotify/kqueue/FSEvents 추상화 |
| **python-dateutil** | ≥ 2.9 | 자연어 날짜 파싱 ("다음 주 월요일") | pytz 대신 사용 |

### 2.2 AI / NPU

| 라이브러리 | 버전 기준 | 용도 | HW 타깃 |
|-----------|---------|-----|--------|
| **optimum[openvino]** | ≥ 1.18 | Hugging Face 모델 → Intel OpenVINO 변환·추론 | NPU (Intel AI Boost) |
| **onnxruntime** | ≥ 1.18 | ONNX 모델 추론 공통 런타임 | NPU / iGPU EP |
| **faster-whisper** | ≥ 1.0 | 음성 → 텍스트 (V1.0 음성 캡처) | NPU CTranslate2 backend |
| **silero-vad** | ≥ 5.1 | Voice Activity Detection — 묵음 구간 자동 커팅 | CPU (경량) |
| **sentence-transformers** (BGE-small-ko) | ≥ 3.0 | 텍스트 임베딩 생성 → sqlite-vec 저장 | NPU ONNX export |

> V1.1+: Phi-3 mini (ONNX, INT4) — 슬롯 추출·자연어 명령 해석. V1.0에서는 미포함.

### 2.3 외부 연동

| 라이브러리 | 버전 기준 | 용도 | 적용 버전 |
|-----------|---------|-----|---------|
| **python-telegram-bot** | ≥ 21.0 | Telegram Bot API (빠른 캡처·알림) | V1.0 |
| **PyGithub** | ≥ 2.3 | GitHub Issues/PR 조회·생성·연결 | V1.0 |
| **google-auth-oauthlib** | ≥ 1.2 | Google OAuth 2.0 (Gmail + Drive 공용 토큰) | V1.1 |
| **google-api-python-client** | ≥ 2.130 | Gmail IMAP 래퍼 + Drive API | V1.1 (Gmail), V1.2 (Drive) |

### 2.4 UI / 서버

| 라이브러리/도구 | 버전 기준 | 용도 | 비고 |
|--------------|---------|-----|-----|
| **http.server** (stdlib) | — | Python 내장 HTTP 서버 (V1.0 UI 서빙) | V1.0; V2에서 Tauri 검토 |
| **htmx** | ≥ 2.0 (CDN) | 서버-사이드 렌더링 + 부분 갱신 (SPA 없이) | CDN 로컬 캐시 |
| **Tailwind CSS** | ≥ 3.4 (CDN) | 유틸리티-퍼스트 스타일링 | CDN 로컬 캐시; 빌드 불필요 |
| **Lucide Icons** | ≥ 0.378 (CDN) | 아이콘 세트 | CDN 로컬 캐시 |

### 2.5 시스템 유틸

| 라이브러리 | 버전 기준 | 용도 |
|-----------|---------|-----|
| **keyring** | ≥ 25.0 | OAuth 토큰·API 키 안전 저장 (Windows Credential Store) |
| **plyer** | ≥ 2.1 | OS 알림 (Windows toast, macOS NSAlert) |
| **markdown-it-py** | ≥ 3.0 | .md 파싱 → HTML 렌더링 (컨텍스트 패널) |
| **schedule** (라이브러리) | ≥ 1.2 | 경량 cron-like 스케줄러 (저녁 리뷰 트리거 등) |

---

## 3. 아키텍처 레이어 다이어그램

```
┌─────────────────────────────────────────────────┐
│  UI Layer (브라우저 창)                           │
│  htmx + Tailwind + Lucide  ←→  http.server       │
└───────────────────┬─────────────────────────────┘
                    │ HTTP (로컬 포트)
┌───────────────────▼─────────────────────────────┐
│  App Layer (Python)                              │
│  라우터 · 비즈니스 로직 · 스케줄러               │
│  python-telegram-bot · PyGithub · google-api     │
└──────┬─────────────────────┬────────────────────┘
       │                     │
┌──────▼──────┐     ┌────────▼────────────────────┐
│  Data Layer │     │  AI Layer                   │
│  SQLite     │     │  faster-whisper (NPU)        │
│  + FTS5     │     │  BGE-small-ko ONNX (NPU)     │
│  + sqlite-  │     │  silero-vad (CPU)            │
│    vec      │     │  (V1.1+) Phi-3 mini (NPU)   │
└──────┬──────┘     └─────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────┐
│  File Layer                                     │
│  .md 원본 (로컬 폴더) + watchdog 감시           │
│  (V1.2) Google Drive SDK — Cold tier            │
└─────────────────────────────────────────────────┘
```

---

## 4. 의존성 설치 순서 (Phase 4 참고)

```bash
# 1. 코어
pip install python-dateutil watchdog markdown-it-py schedule keyring plyer

# 2. DB
pip install sqlite-vec  # sqlite3는 stdlib

# 3. AI (NPU)
pip install optimum[openvino] onnxruntime faster-whisper silero-vad
pip install sentence-transformers  # BGE-small-ko 다운로드 별도

# 4. 외부 연동
pip install python-telegram-bot PyGithub

# 5. Google (V1.1+)
pip install google-auth-oauthlib google-api-python-client
```

> htmx · Tailwind · Lucide는 CDN JS/CSS를 `static/vendor/`에 로컬 캐시. pip 불필요.

---

## 5. 버전 고정 전략

- `requirements.txt` — 개발·배포 공용. 최초 설치 후 `pip freeze`로 고정.
- `requirements-ai.txt` — AI/NPU 의존성 분리 (무거운 패키지 선택 설치 가능).
- NPU EP 드라이버 의존성: Intel NPU Driver ≥ 1.5 + OpenVINO ≥ 2024.1 — README에 설치 가이드 포함 (Phase 4 착수 시).
