# ADR-005: 시크릿 저장 정책

> 상태: Accepted | 결정일: 2026-04-28
> 결정자: iet03 (코덱스 외부 검토 반영)

---

## 컨텍스트

CLAUDE.md 정책: "외부 연동 시 비밀(GitHub 토큰, 메일 SMTP 등) 평문 저장 금지".
BR-AUTH-01: "PAT는 Windows Credential Manager에 저장, .env 평문 금지".

그러나 ADR-001 + Environment_Spec 초기 버전에 `.env` 파일에 `TG_BOT_TOKEN`, `GH_PAT`를 두는 docker-compose 패턴이 명시되어 있어 정책과 충돌했다. Phase 5 진입 전 반드시 닫는다.

---

## 결정

**모든 V1.0 시크릿은 Windows Credential Manager (DPAPI 백엔드)에 저장한다.** `.env` 파일에 토큰을 두지 않는다.

```
┌──────────────────────────────────────────────────────────┐
│ Windows Credential Manager (Generic Credentials)         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Target: MC_GH_PAT          User: iet03              │ │
│  │ Target: MC_TG_BOT_TOKEN    User: iet03              │ │
│  │ Target: MC_GOOGLE_OAUTH    User: iet03   (V1.1)     │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
        ▲                                 ▲
        │ keyring.get_password()          │
        │                                 │
   ┌────┴───────┐                ┌────────┴──────────┐
   │ ai-worker  │                │ integrations      │
   │ (host)     │                │ (Docker)          │
   └────────────┘                └───────────────────┘
                                          │
                                          │ Docker는 host의 Credential Manager 직접 접근 불가
                                          ▼
                                  ┌─────────────────────┐
                                  │ secret-bridge HTTP  │
                                  │ on host port 9999   │
                                  │ (loopback only)     │
                                  └─────────────────────┘
```

### 시크릿 접근 흐름

| 컴포넌트 | 위치 | 접근 방식 |
|---------|------|---------|
| ai-worker | 호스트 (Windows) | `keyring.get_password("MC_GH_PAT", "iet03")` 직접 |
| integrations | Docker 컨테이너 | host 측 secret-bridge에 HTTP 요청 (`http://host.docker.internal:9999/secret/MC_TG_BOT`) |
| core-api | Docker 컨테이너 | 시크릿 직접 사용 안 함 (integrations에 위임) |

### secret-bridge (호스트 측 작은 서비스)

```python
# secret_bridge/main.py — Windows 호스트 프로세스, loopback only
from fastapi import FastAPI, HTTPException, Request
import keyring, ipaddress

ALLOWED_KEYS = {"MC_GH_PAT", "MC_TG_BOT_TOKEN", "MC_GOOGLE_OAUTH"}
app = FastAPI()

@app.middleware("http")
async def loopback_only(request: Request, call_next):
    client = ipaddress.ip_address(request.client.host)
    # Docker가 통과하는 host-gateway 게이트웨이 IP 또는 127.0.0.1만 허용
    if not (client.is_loopback or str(client) == "172.17.0.1"):
        raise HTTPException(403)
    return await call_next(request)

@app.get("/secret/{key}")
def get_secret(key: str):
    if key not in ALLOWED_KEYS:
        raise HTTPException(404)
    val = keyring.get_password(key, "iet03")
    if not val:
        raise HTTPException(404)
    return {"value": val}
```

### 시크릿 등록 / 회전

CLI 도구 `tools/secret_set.py`:
```bash
python tools/secret_set.py MC_GH_PAT
# 프롬프트: 값 입력 → keyring.set_password(...)
```

UI에서 SC-08 Settings → Credential 컴포넌트(설정 화면 보강, FR-SET-CRED-01) 통해 등록·검증·삭제·마스킹 처리.

---

## 고려한 대안

| 옵션 | 이유로 제외 |
|------|-----------|
| `.env` 평문 | CLAUDE.md/BR-AUTH-01 정책 정면 위반. |
| Docker secrets | Swarm/Kubernetes 전용. 단일 호스트 compose 환경에서 무의미. |
| HashiCorp Vault | 1인 로컬 도구에 과잉. |
| 컨테이너 내부 keyring | Windows Credential Manager는 호스트 OS 자원 — 컨테이너에서 직접 접근 불가. |

---

## 결과

- `.env`는 *비민감* 환경변수만 (예: `LOG_LEVEL`, `DB_PATH`). 토큰 절대 금지.
- secret-bridge는 부팅 시 Task Scheduler로 자동 시작 (ai-worker와 동일 트리거).
- `Environment_Spec.md` 보안 섹션 갱신.
- SC-08 Settings에 Credential 컴포넌트 명세 보강 (NEW: SC-08-Cred 서브 화면).
- BR-AUTH-01 + 본 ADR 일치 확인 완료.

### 근거

| 근거 유형 | 내용 |
|---------|------|
| 정책 | CLAUDE.md "비밀 평문 저장 금지" |
| BA | BR-AUTH-01 (Phase 3 BR Log) |
| 외부 검토 | 코덱스 검토 2026-04-28 — `.env` 토큰 명시가 보안 요구와 충돌 지적 |
