# 환경 명세 — MC V1.0

> 결정일: 2026-04-27

---

## 호스트 환경

| 항목 | 값 |
|------|-----|
| OS | Windows 11 Home 23H2+ |
| CPU | Intel Core Ultra 7 355 (Meteor Lake) |
| NPU | Intel AI Boost NPU (13 TOPS) |
| iGPU | Intel Arc Graphics (ANGLE/WebGL 가속) |
| RAM | 32GB LPDDR5 |
| 스토리지 | NVMe SSD (mc.db + MC-Notes/ 로컬) |
| Python | 3.11+ (CPython, Windows) |
| Docker Desktop | 4.x + WSL2 backend |

---

## 디렉터리 구조 (ADR-005, ADR-006 반영)

```
C:\Users\iet03\Documents\Hub\agents\schedule\   ← 프로젝트 루트
  ai_worker\          ← Tier 1: Windows 호스트 Python 서비스
    main.py
    models\           ← ONNX + OpenVINO IR 모델 파일 (git-ignored)
    requirements.txt
  secret_bridge\      ← Tier 1: Windows 호스트, loopback 시크릿 브리지
    main.py           ← keyring → HTTP (port 9999)
  notifier_daemon\    ← Tier 1: Windows 호스트, OS 토스트 발송
    main.py           ← 1분 주기 SQLite 폴링 (read-only)
  core_api\           ← Tier 2: Docker 컨테이너 (포트 8000)
    main.py
    templates\        ← htmx HTML 템플릿
    static\           ← CSS, JS, fonts
    Dockerfile
  integrations\       ← Tier 2: Docker 컨테이너 (포트 8002)
    main.py
    Dockerfile
  data\
    mc.db             ← SQLite (volume mount, WAL 모드)
  MC-Notes\           ← .md 메모 파일 (watchdog 대상)
    2026\
  tools\
    setup_models.py        ← 최초 모델 다운로드
    migrate.py             ← DB 마이그레이션
    secret_set.py          ← keyring 시크릿 등록 CLI
    install_services.ps1   ← Task Scheduler 등록
  docker-compose.yml
  Doc\                ← AI_SDLC 산출물
```

---

## 서비스 구성

> 4-tier 모델은 ADR-006 참조. Tier 1은 Task Scheduler 자동 시작, Tier 2는 Docker compose.

### Tier 1 — 호스트 백그라운드 (Task Scheduler)

#### ai-worker

```text
실행: python ai_worker/main.py
포트: 8001 (loopback only)
의존: OpenVINO Runtime 2024.x, onnxruntime-openvino 1.18+
모델: ai_worker/models/ (KoE5 + Whisper Base + silero-VAD)
```

#### secret-bridge

```text
실행: python secret_bridge/main.py
포트: 9999 (loopback + Docker host-gateway만 허용)
역할: keyring(DPAPI) ↔ Docker 컨테이너 시크릿 중계
허용 키: MC_GH_PAT, MC_TG_BOT_TOKEN, MC_GOOGLE_OAUTH (V1.1)
```

#### notifier-daemon

```text
실행: python notifier_daemon/main.py
주기: 60초 SQLite 폴링 (read-only mode)
출력: Windows Toast (plyer.notification)
중복 방지: notification_events 테이블
```

### Tier 2 — Docker 컨테이너

#### core-api

```text
이미지: python:3.11-slim
포트: 8000:8000
볼륨:
  - ./data:/app/data          (mc.db)
  - ./MC-Notes:/app/mc-notes  (watchdog 접근)
  - ./core_api:/app
환경변수 (.env, 비민감만):
  LOG_LEVEL=info
  DB_PATH=/app/data/mc.db
  AI_WORKER_URL=http://host.docker.internal:8001
  SECRET_BRIDGE_URL=http://host.docker.internal:9999
  INTEGRATIONS_URL=http://integrations:8002
```

#### integrations

```text
이미지: python:3.11-slim
포트: 8002:8002
볼륨:
  - ./data:/app/data          (mc.db 쓰기 — capture_inbox/retry_queue)
환경변수 (.env, 비민감만):
  CORE_API_URL=http://core-api:8000
  SECRET_BRIDGE_URL=http://host.docker.internal:9999
시크릿 접근:
  TG_BOT_TOKEN  ← secret-bridge GET /secret/MC_TG_BOT_TOKEN (런타임)
  GH_PAT        ← secret-bridge GET /secret/MC_GH_PAT       (런타임)
  ⚠ .env에 직접 토큰 저장 금지 — ADR-005
```

### docker-compose.yml 요약

```yaml
services:
  core-api:
    build: ./core_api
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
      - ./MC-Notes:/app/mc-notes
    env_file: .env             # 비민감 변수만
    extra_hosts:
      - "host.docker.internal:host-gateway"

  integrations:
    build: ./integrations
    ports: ["8002:8002"]
    volumes:
      - ./data:/app/data
    env_file: .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on: [core-api]
```

---

## 보안 & 시크릿 (ADR-005)

| 시크릿 | keyring target | 접근 방법 — 호스트 | 접근 방법 — Docker |
|--------|---------------|------------------|-------------------|
| GitHub PAT | `MC_GH_PAT` | `keyring.get_password("MC_GH_PAT", "iet03")` | `GET http://host.docker.internal:9999/secret/MC_GH_PAT` |
| Telegram Bot Token | `MC_TG_BOT_TOKEN` | 동일 | 동일 |
| Google OAuth (V1.1) | `MC_GOOGLE_OAUTH` | 동일 | 동일 |

**.env 파일 정책**:
- 비민감 변수만 (포트, 로그 레벨, 컨테이너 간 URL).
- 토큰·시크릿·인증값 직접 저장 금지 (ADR-005).
- `.env`는 git-ignored.

**시크릿 등록 절차**:
```powershell
python tools/secret_set.py MC_GH_PAT
# stdin으로 값 입력 → keyring.set_password("MC_GH_PAT", "iet03", value)
```
또는 SC-08 Settings → Credential 컴포넌트(SC-08-Cred).

---

## 브라우저 타깃

- **타깃**: Microsoft Edge (Chromium) 또는 Google Chrome, 최신 버전
- 로컬 전용 도구이므로 IE/Firefox 폴리필 불필요
- View Transitions API, CSS backdrop-filter, CSS @property, Canvas 2D, Web Animations API 모두 Chromium 최신에서 지원됨

---

## 개발 환경 빠른 시작

```powershell
# 1. Python 의존성
pip install -r ai_worker/requirements.txt
pip install -r secret_bridge/requirements.txt
pip install -r notifier_daemon/requirements.txt

# 2. 시크릿 등록 (Windows Credential Manager)
python tools/secret_set.py MC_GH_PAT
python tools/secret_set.py MC_TG_BOT_TOKEN

# 3. 모델 다운로드 (최초 1회, ~300MB)
python tools/setup_models.py

# 4. DB 초기화
python tools/migrate.py

# 5. Tier 1 서비스 시작 (개발 시 수동, 프로덕션은 Task Scheduler)
Start-Process python -ArgumentList "secret_bridge/main.py"
Start-Process python -ArgumentList "ai_worker/main.py"
Start-Process python -ArgumentList "notifier_daemon/main.py"

# 6. Tier 2 Docker 시작
docker compose up -d

# 7. (옵션) 서비스 자동 시작 등록
.\tools\install_services.ps1
```

접속: http://localhost:8000
