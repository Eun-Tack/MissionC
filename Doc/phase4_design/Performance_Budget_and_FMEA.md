# Performance Budget & FMEA — MC (Mission Control)

> 작성: 2026-05-04 | Phase 4 Designer
> 목적: 모든 NFR 타이밍 기준 단일 출처 + 장애 모드 카탈로그

---

## 1. Performance Budget

### 1.1 UI 응답 (사용자 체감)

| 화면/동작 | 목표 | 측정 기준 | FR/NFR 출처 |
|----------|------|---------|-----------|
| Today's Flow 초기 렌더 | ≤ 1s | TTFB + Jinja2 렌더 완료 | FR-FLOW-01 |
| Context Panel 펼침 | ≤ 500ms | htmx 요청 완료 | FR-FLOW-03 |
| FTS5 검색 (항목 <30) | ≤ 200ms | 요청→결과 fragment | FR-AI-SEARCH |
| 벡터 검색 (항목 ≥30, ai-worker 포함) | ≤ 800ms | 요청→결과 fragment | FR-AI-SEARCH |
| Quick Capture 저장 | ≤ 300ms | POST→htmx 피드백 | FR-CAP-01 |
| Inbox triage 단축키 (a/r/t) | ≤ 100ms | 키 입력→UI 반응 | FR-INBOX-01 NFR |
| Diagnostics 로드 | ≤ 1.5s | health 집계 응답 | FR-DIAG-01 NFR |
| Credential 검증 | ≤ 3s | POST→valid 응답 | FR-SET-CRED-01 NFR |
| JSON Export | ≤ 5s | GET→다운로드 시작 | FR-BACKUP-01 |
| Inbox 항목 표시 (TG 수신 후) | ≤ 5s | TG polling→UI visible | FR-INBOX-01 NFR |

### 1.2 AI 추론 (ai-worker)

| 작업 | 목표 | EP | 비고 |
|------|------|---|------|
| 임베딩 (단건) | ≤ 200ms | NPU / CPU fallback | KoE5 384-dim |
| STT (Whisper Base) | ≤ 3s | NPU / CPU fallback | 30초 음성 기준 |
| 슬롯 추출 (Phi-3, V1.1) | ≤ 2s | NPU | Phi-3 mini INT4 |
| ai-worker cold start | ≤ 10s | — | 모델 로드 포함 |

### 1.3 백그라운드 작업

| 작업 | 주기/목표 | 담당 |
|------|---------|------|
| GitHub 캐시 갱신 | 15분 간격 | integrations APScheduler |
| 알림 폴링 (notification_events) | 60초 간격 | notifier-daemon |
| watchdog 파일 감지 → DB 동기화 | ≤ 2s (변경 후) | core-api watchdog |
| Telegram polling | 즉시 (long-polling 1s timeout) | integrations |

### 1.4 DB & 파일

| 항목 | 기준 | 비고 |
|------|------|------|
| SQLite WAL 체크포인트 | 자동 (1000 페이지) | FTS5 포함 |
| mc.db 파일 크기 (V1.0) | < 50 MB | 임베딩 1000건 × 384 × 4byte ≈ 1.5MB |
| 최대 동시 DB 커넥션 | 1 write + N read | WAL 모드 |

---

## 2. FMEA (Failure Mode and Effects Analysis)

### 카탈로그 읽는 법

| 컬럼 | 설명 |
|------|------|
| 장애 | 발생 가능한 실패 |
| 감지 | 언제/어떻게 알게 되나 |
| 사용자 영향 | 체감 증상 |
| 복구 방법 | 자동/수동 조치 |
| 담당 | 책임 서비스/컴포넌트 |
| 우선순위 | P0(즉시)/P1(24h)/P2(주간) |

---

### FM-01: ai-worker 다운 (NPU/CPU 비가용)

| | |
|--|--|
| **장애** | ai-worker 프로세스 미실행 또는 모델 로드 실패 |
| **감지** | core-api → `GET /health:8001` 타임아웃 (≤500ms 초과) |
| **사용자 영향** | 벡터 검색 불가 → FTS5 자동 fallback. STT 불가 → Voice Capture 버튼 비활성화 |
| **복구** | 자동: FTS5 fallback (검색). 수동: Task Scheduler "MC-AIWorker" 재시작. SC-10 Diagnostics에 `degraded` 표시 |
| **담당** | ai-worker + core-api (fallback 로직) |
| **우선순위** | P1 (FTS5 fallback 있어 즉시 차단 아님) |

---

### FM-02: secret-bridge 다운 (DPAPI 비가용)

| | |
|--|--|
| **장애** | secret-bridge 프로세스 미실행 |
| **감지** | `POST /api/cred/gh` → 503 응답. SC-10 `secret_bridge: down` |
| **사용자 영향** | GitHub/TG 연동 자격증명 등록 불가. 기존 캐시된 데이터는 계속 표시됨 |
| **복구** | 수동: `python secret_bridge/main.py` 재실행 또는 Task Scheduler 확인 |
| **담당** | secret-bridge |
| **우선순위** | P1 |

---

### FM-03: Docker 컨테이너 미실행 (core-api/integrations)

| | |
|--|--|
| **장애** | `docker-compose up` 안 한 상태 또는 컨테이너 crash |
| **감지** | 브라우저 `localhost:8000` 접속 안 됨 (Connection Refused) |
| **사용자 영향** | UI 전체 불가 |
| **복구** | `docker-compose up -d`. 자동 재시작: `restart: unless-stopped` 정책 (docker-compose.yml) |
| **담당** | docker-compose |
| **우선순위** | P0 (전면 장애) |

---

### FM-04: SQLite 파일 잠금 (WAL 충돌)

| | |
|--|--|
| **장애** | 다중 writer 동시 접근 (이론상 core-api + watchdog 동시 write) |
| **감지** | `sqlite3.OperationalError: database is locked` 로그 |
| **사용자 영향** | 특정 항목 저장 실패. 즉시 재시도 가능 |
| **복구** | 자동: WAL 모드에서 reader는 차단 안 됨. Writer는 busy_timeout 3000ms 설정 (BR 없음 — 구현 요구사항) |
| **담당** | core-api DB 연결 설정 |
| **우선순위** | P1 |

---

### FM-05: GitHub Rate Limit 초과 (BR-GIT-04)

| | |
|--|--|
| **장애** | GitHub API 시간당 5000 요청 초과 |
| **감지** | `X-RateLimit-Remaining < 10` 헤더 |
| **사용자 영향** | Context Panel의 GitHub issues 섹션 캐시 데이터 표시 (최대 15분 지연) |
| **복구** | 자동: 갱신 건너뜀 + `settings.github_rate_limited_until` 기록. 해제 후 자동 재개 |
| **담당** | integrations (APScheduler) |
| **우선순위** | P2 |

---

### FM-06: Telegram Bot Token 만료/무효

| | |
|--|--|
| **장애** | `MC_TG_BOT_TOKEN` 폐기 또는 변경 |
| **감지** | python-telegram-bot polling 오류 로그. SC-10 `telegram_polling: false` |
| **사용자 영향** | TG → Inbox 수신 불가. TG 알림 발송 불가 |
| **복구** | 수동: SC-08-Cred에서 새 토큰 재등록 → integrations 재시작 |
| **담당** | integrations + FR-SET-CRED-01 |
| **우선순위** | P1 |

---

### FM-07: STT confidence 임계값 미달 (BR-AI-06)

| | |
|--|--|
| **장애** | Whisper confidence < 0.6 (배경 소음, 비한국어 혼입 등) |
| **감지** | ai-worker 응답 `"confidence": 0.45` |
| **사용자 영향** | Voice Capture가 items로 바로 저장되지 않고 Inbox에 `low_conf` 상태로 대기 |
| **복구** | 자동: capture_inbox에 저장. 사용자 SC-09 Inbox에서 수동 triage |
| **담당** | core-api (confidence 판단 로직) |
| **우선순위** | P2 (데이터 손실 없음) |

---

### FM-08: .md 파일 충돌 (BR-CONFLICT-01)

| | |
|--|--|
| **장애** | watchdog 감지 시점에 외부 편집기가 동일 파일 수정 |
| **감지** | file_index.last_hash vs 디스크 해시 불일치 |
| **사용자 영향** | SC-12 충돌 다이얼로그 팝업 (3가지 옵션 제공) |
| **복구** | 수동: keep_local / keep_remote / merge 선택. 선택 전까지 해당 파일 DB 반영 보류 |
| **담당** | core-api (watchdog + conflict API) |
| **우선순위** | P1 (데이터 무결성) |

---

### FM-09: notifier-daemon 미실행 (알림 누락)

| | |
|--|--|
| **장애** | notifier-daemon Task Scheduler 미등록 또는 프로세스 크래시 |
| **감지** | 일정 5분 전 OS 토스트 미표시. SC-10 `notifier: down` |
| **사용자 영향** | 스케줄 알림 미수신. 데이터 손실 없음 |
| **복구** | 수동: `schtasks /run /tn "MC-Notifier"`. 또는 재설치 스크립트 |
| **담당** | notifier-daemon (ADR-006) |
| **우선순위** | P1 |

---

### FM-10: 임베딩 모델 차원 불일치 (마이그레이션 오류)

| | |
|--|--|
| **장애** | KoE5(384) → bge-m3(1024) 전환 시 sqlite-vec 인덱스 차원 충돌 |
| **감지** | `POST /infer/embed` 응답 `"dim": 1024` vs DB `FLOAT[384]` |
| **사용자 영향** | 벡터 검색 오류 → FTS5 fallback |
| **복구** | 마이그레이션 v002 실행 (전체 재임베딩). OQ-D-01 — Phase 5 결정 후 마이그레이션 스크립트 작성 |
| **담당** | ai-worker + DB 마이그레이션 |
| **우선순위** | P0 (마이그레이션 실행 시점에만 발생) |

---

### FM-11: retry_queue 포화 (BR-RETRY-01 최대 5회 초과)

| | |
|--|--|
| **장애** | TG 알림 발송 5회 연속 실패 → `status='failed'` |
| **감지** | SC-11 Alerts에 `failed` 항목 표시. retry_queue.attempts ≥ 5 |
| **사용자 영향** | 해당 알림 영구 미전달. 수동 재시도 필요 |
| **복구** | SC-11에서 수동 재시도 버튼 (FR-NOTIFY-CTR-01). 근본 원인 SC-10 Diagnostics 확인 |
| **담당** | integrations + core-api (알림 센터) |
| **우선순위** | P2 |

---

## 3. 복구 시간 목표 (RTO)

| 장애 유형 | RTO 목표 | 비고 |
|---------|---------|------|
| Docker 컨테이너 재시작 | ≤ 30s | `restart: unless-stopped` |
| ai-worker 재시작 | ≤ 15s (모델 로드 포함) | Task Scheduler |
| secret-bridge 재시작 | ≤ 5s | |
| 전체 시스템 재부팅 후 | ≤ 60s | 모든 Tier 1 서비스 자동 시작 |
| 데이터 복구 (JSON Export 사용) | 수동 (정의 안 됨) | V1.0 범위 외 |

---

## Change Log

| 버전 | 날짜 | 변경 내용 |
|------|------|---------|
| 1.0 | 2026-05-04 | 최초 작성. 11개 장애 모드 + 전체 NFR 예산 |
