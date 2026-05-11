# ADR-008: 설치형 배포 전략

> 날짜: 2026-05-04 | 상태: Accepted
> 결정자: iet03 | 맥락: Phase 4 v1.3 — 다른 사용자 배포 지원

---

## 배경

MC는 원래 iet03 단일 노트북용으로 설계됐으나, 다른 사용자도 설치할 수 있어야 하는 요구가 생겼다. Docker Desktop을 전제로 한 현재 아키텍처는 일반 사용자에게 설치 장벽이 높다. GitHub Releases를 통한 `.exe` 배포로 전환한다.

---

## 결정

### Docker 제거 — 네이티브 Python 서비스로 전환

| 기존 (Docker) | 변경 후 (Native) |
|-------------|----------------|
| core-api — Docker 컨테이너 | core-api — Windows 서비스 (Task Scheduler) |
| integrations — Docker 컨테이너 | integrations — Windows 서비스 (Task Scheduler) |
| ai-worker — 로컬 Python | ai-worker — 로컬 Python (유지) |
| secret-bridge — 로컬 Python | secret-bridge — 로컬 Python (유지) |
| notifier-daemon — 로컬 Python | notifier-daemon — 로컬 Python (유지) |

Docker 제거 이유:
- Docker Desktop 설치 요구 → 일반 사용자 진입 장벽
- 1인 로컬 도구에서 컨테이너 격리 이점보다 복잡성 비용이 큼
- 모든 서비스가 SQLite 파일 직접 접근으로 단순화 가능

### 설치 패키지 구조

```
MC-Setup-v1.0.0.exe (NSIS 인스톨러)
  ├── Python 3.12 Embedded Runtime
  ├── MC 서비스 파일들 (core_api/, integrations/, ai_worker/, etc.)
  ├── SQLite + sqlite-vec DLL
  ├── install.ps1 (Task Scheduler 등록 스크립트)
  └── models/ (ONNX 모델 — 별도 다운로드 또는 번들)
```

### 서비스 등록 (Task Scheduler)

설치 완료 시 자동 등록:
```
MC-CoreAPI       → core_api/main.py      포트 8000
MC-Integrations  → integrations/main.py  포트 8002
MC-AIWorker      → ai_worker/main.py     포트 8001 (하드웨어 탐지 후)
MC-SecretBridge  → secret_bridge/main.py 포트 9999
MC-Notifier      → notifier/main.py      (HTTP 없음)
```

모두 `logon type=S4U` (서비스 계정 없이 사용자 세션 시작 시 자동 실행).

### GitHub 배포 파이프라인

```
git push tag v1.0.0
  → GitHub Actions 트리거
    → PyInstaller 빌드 (Windows runner)
    → NSIS 인스톨러 패키징
    → GitHub Release 자동 생성
    → MC-Setup-v1.0.0.exe 업로드
```

`.github/workflows/release.yml` 핵심:
```yaml
- uses: actions/setup-python@v5
  with: {python-version: "3.12"}
- run: pip install pyinstaller
- run: pyinstaller mc.spec
- run: makensis installer.nsi
- uses: softprops/action-gh-release@v2
  with:
    files: dist/MC-Setup-*.exe
```

### ONNX 모델 배포 전략

모델 파일은 크기 문제(~200MB)로 인스톨러에 번들하지 않는다:
- 최초 실행 시 모델 자동 다운로드 (GitHub Releases assets 또는 HuggingFace Hub)
- NPU/GPU 없으면 모델 다운로드 건너뜀 (ADR-009 참조)
- `models/` 폴더 위치: `%APPDATA%\MC\models\`

### secret-bridge 보안 조정

Docker 제거로 `host.docker.internal` 불필요. 모든 서비스가 `127.0.0.1`에서 직접 통신:
```python
SECRET_BRIDGE_URL = "http://127.0.0.1:9999"  # Docker 없이 직접 loopback
```

---

## 대안 검토

| 대안 | 거절 이유 |
|------|---------|
| Electron | ~150MB, Node.js 런타임 추가, Python 백엔드와 이중 스택 |
| Tauri | Rust 빌드 인프라 필요, 현재 Python 스택과 이질적 |
| Docker 유지 | 사용자 설치 장벽, Docker Desktop 무료 정책 변경 위험 |
| 웹 호스팅 | 로컬 원칙 위반 |

---

## 영향

- ADR-001 (하이브리드 컨테이너 아키텍처) → 폐기. ADR-008로 대체.
- docker-compose.yml → 개발 환경 전용으로 유지 (선택사항)
- Environment_Spec.md → 서비스 목록에서 Docker 참조 제거
- API_Contracts.md → `host.docker.internal` → `127.0.0.1` 전환

---

## Change Log

| 날짜 | 변경 |
|------|------|
| 2026-05-04 | 최초 작성 |
