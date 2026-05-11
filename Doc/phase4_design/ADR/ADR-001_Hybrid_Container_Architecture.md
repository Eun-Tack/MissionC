# ADR-001: 하이브리드 컨테이너 아키텍처

> 상태: Accepted | 결정일: 2026-04-27
> 결정자: iet03 (2026-04-27 Phase 4 진입 시 명시 결정)

---

## 컨텍스트

MC는 1인 Windows 로컬 도구다. V1.0을 빠르게 완료하고, 이후 모바일 캡처·Gmail·Drive 등의 모듈을 점진적으로 붙이는 전략이 확정되었다. 아키텍처가 이 확장을 지원해야 한다.

Intel NPU는 Windows 드라이버 레벨(OpenVINO/DirectML)에서 동작하므로 Docker 컨테이너 내부에서 NPU EP를 직접 쓰는 것은 복잡도가 높다.

---

## 결정

**하이브리드 컨테이너** 구조를 채택한다.

```
┌─────────────────────────────────────────────────────┐
│  Host (Windows 11)                                  │
│                                                     │
│  ┌─────────────────────┐  ┌──────────────────────┐  │
│  │ ai-worker (Python)  │  │  docker-compose      │  │
│  │  - Whisper NPU      │  │                      │  │
│  │  - BGE-small NPU    │  │  ┌────────────────┐  │  │
│  │  - Phi-3 mini (V1.1)│  │  │ core-api       │  │  │
│  │  Windows 프로세스    │  │  │ (htmx + SQLite)│  │  │
│  │  포트: 8001          │  │  │ 포트: 8000     │  │  │
│  └──────────┬──────────┘  │  └───────┬────────┘  │  │
│             │ HTTP/IPC    │          │            │  │
│             └────────────►│  ┌────────────────┐  │  │
│                           │  │ integrations   │  │  │
│                           │  │ (TG Bot + GH)  │  │  │
│                           │  │ 포트: 8002     │  │  │
│                           │  └────────────────┘  │  │
│                           └──────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 서비스별 역할

| 서비스 | 실행 방식 | 책임 | 포트 |
|--------|---------|------|------|
| **ai-worker** | Windows 로컬 Python 프로세스 (systemd/Task Scheduler) | Whisper STT, BGE 임베딩, Phi-3 슬롯 추출. NPU 직접 접근. | 8001 |
| **core-api** | Docker 컨테이너 | htmx UI 서빙, SQLite CRUD, 비즈니스 로직 | 8000 |
| **integrations** | Docker 컨테이너 | Telegram Bot polling, GitHub API 캐시, (V1.1) Gmail, (V1.2) Drive | 8002 |

### 서비스 간 통신

- `core-api` → `ai-worker`: HTTP REST (`localhost:8001/infer`)
- `core-api` → `integrations`: HTTP REST (`localhost:8002/...`)
- SQLite 파일: `core-api` 컨테이너에 볼륨 마운트 (`./data/mc.db`)
- `ai-worker`는 동일 SQLite에 직접 접근 (볼륨 공유 또는 `core-api` API 경유)

---

## 고려한 대안

| 옵션 | 이유로 제외 |
|------|-----------|
| 완전 컨테이너화 (NPU 포함) | Docker 내 Intel NPU EP 설정 복잡도 높음 (WSL2 + OpenVINO 드라이버 충돌 위험) |
| 완전 단일 프로세스 (모놀리스) | 모듈 확장 시 코드 결합도 증가. 모바일 PWA·Gmail 모듈 독립 배포 불가. |
| Tauri (V1.0) | 빌드 복잡도 높음. V1.0 목표(빠른 완료)와 불일치. V2 재검토 예정. |

---

## 결과

- **V1.0**: ai-worker(로컬) + core-api(Docker) + integrations(Docker)
- **V2 모바일 PWA**: integrations 컨테이너에 mobile-capture 서비스 추가
- **V2 Gmail/Drive**: integrations 컨테이너 모듈 추가
- NPU 업그레이드 시 ai-worker만 교체

### 근거

| 근거 유형 | 내용 | 출처 |
|---------|------|------|
| 기술 제약 | Intel NPU = Windows 드라이버 의존 | Phase 0 Tech_Landscape.md |
| 확장 전략 | 모듈별 독립 배포로 점진적 기능 추가 | iet03 결정 2026-04-27 |
| 안티패턴 회피 | Electron+Python sidecar 대신 순수 Python | Phase 0 Tech_Landscape.md |
