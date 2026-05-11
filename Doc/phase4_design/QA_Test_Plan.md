# QA Test Plan — MC (Mission Control)

> 작성: 2026-05-04 | Phase 4 Designer
> 범위: Phase 5 구현 대상 V1.0 (M1~M10)
> 컨텍스트: 1인 프로젝트. CI는 최소 범위. NPU는 mock 우선, 주간 실기기 검증.

---

## 1. 테스트 전략 개요

| 레벨 | 도구 | 범위 | Mock 정책 |
|------|------|------|---------|
| Unit | pytest | 비즈니스 로직, 상태 머신, 검색 라우팅 | DB: SQLite 인메모리. ai-worker: stub. secret-bridge: stub |
| Integration | pytest + httpx | 서비스 간 HTTP 통신, SQLite write/read | Docker Compose 기동. ai-worker: CPU fallback. TG: test bot 토큰 |
| E2E (smoke) | playwright | Today's Flow, Inbox, Morning/Evening 핵심 흐름 | 없음 (실 서비스 기동) |
| NPU 실기기 | 수동 | STT ≤3s, embed ≤200ms, ai-worker health | 주 1회 또는 모델 교체 시 |
| Performance | pytest-benchmark | Context Panel ≤500ms, Search ≤200ms/800ms | SQLite 인메모리 |

---

## 2. NPU 테스트 전략

NPU는 CI 환경에서 재현 불가 (Intel Core Ultra 7 로컬 전용). 분리 운영.

```
CI (자동):
  - ai-worker endpoint는 MockAIClient(stub)로 대체
  - MockAIClient.embed("text") → 고정 vector[384] 반환 (all zeros + index hash)
  - MockAIClient.stt(audio) → {"transcript": "test", "confidence": 0.9}

주간 수동 (실기기):
  - NPU health check: GET http://localhost:8001/health → ep="NPU" 확인
  - Whisper 15개 샘플 발화 → 평균 latency_ms ≤ 3000
  - KoE5 embed 100건 → 평균 latency_ms ≤ 200
  - 모델 교체 시 (KoE5 → bge-m3): vector_dim 확인 필수
```

---

## 3. Mock 정책 상세

| 컴포넌트 | CI Mock 방법 | 근거 |
|---------|------------|------|
| ai-worker (HTTP) | `MockAIClient` fixture — httpx MockTransport | NPU 비가용 |
| secret-bridge (HTTP) | `MockSecretBridge` fixture — `{"value": "test_token"}` 고정 반환 | DPAPI 비가용 |
| Telegram Bot | `python-telegram-bot` Test Bot 토큰 또는 Mock Handler | 네트워크 |
| GitHub API | `responses` 라이브러리 mocking | rate limit 방지 |
| Docker (core-api) | 직접 `app` import (TestClient) | 컨테이너 불필요 |

---

## 4. 모듈별 테스트 커버리지 목표

1인 프로젝트 특성상 전체 80% 목표보다 **크리티컬 경로 100% 보장** 우선.

| 모듈 | 단위 커버리지 목표 | 크리티컬 AC |
|------|----------------|-----------|
| items CRUD + 상태 머신 | 90% | AC-TASK-* (done/cancel 전이) |
| 검색 라우팅 (FTS5/vec 분기) | 100% | count <30 / ≥30 분기 |
| Context Panel ≤500ms | 성능 테스트 | PERF-CTX-01 |
| Capture Inbox routing | 90% | AC-INBOX-01~04 |
| secret-bridge 화이트리스트 | 100% | TC-CRED-01-05 (보안) |
| conflict resolution | 90% | AC-CONFLICT-* |
| carry-over 로직 | 100% | 이월 조건 정확성 |
| notifier-daemon polling | 80% | dedup (event_id 중복 방지) |
| 전체 평균 | ≥ 75% | — |

---

## 5. 테스트 케이스 — 크리티컬

### TC-SEARCH-01: 검색 라우팅 분기

```python
def test_search_uses_fts5_below_threshold(db_in_memory):
    # 29개 items 삽입
    response = client.post("/partial/search", data={"q": "테스트"})
    assert response.status_code == 200
    assert mock_ai_client.embed.call_count == 0  # ai-worker 미호출

def test_search_uses_vec_above_threshold(db_in_memory, mock_ai_client):
    # 31개 items 삽입
    response = client.post("/partial/search", data={"q": "테스트"})
    assert mock_ai_client.embed.call_count == 1
```

---

### TC-INBOX-01: TG 메시지 → Inbox 자동 라우팅

```python
def test_telegram_message_goes_to_inbox(db_in_memory):
    # integrations → POST /api/items with source="telegram"
    response = client.post("/api/items", json={"title": "test", "type": "task", "source": "telegram"})
    # capture_inbox에 pending 항목 생성 확인
    row = db.fetchone("SELECT * FROM capture_inbox WHERE source='telegram'")
    assert row["status"] == "pending"
```

---

### TC-CRED-01-05: secret-bridge 평문 저장 금지 (보안)

```python
def test_secret_not_in_env_file():
    env_content = Path(".env").read_text()
    assert "GH_PAT" not in env_content
    assert "TG_BOT_TOKEN" not in env_content
    assert "GOOGLE_OAUTH" not in env_content

def test_secret_bridge_rejects_unknown_key(mock_bridge):
    response = mock_bridge.get("/secret/UNKNOWN_KEY")
    assert response.status_code == 403
```

---

### TC-CONFLICT-01: 일정 겹침 감지

```python
def test_schedule_conflict_returns_409(db_in_memory):
    # 기존 일정: 10:00-11:00
    client.post("/api/items", json={"title": "기존", "type": "schedule", "scheduled_at": "2026-05-05T10:00"})
    # 겹치는 일정: 10:30-11:30
    response = client.post("/api/items", json={"title": "새일정", "type": "schedule", "scheduled_at": "2026-05-05T10:30"})
    assert response.status_code == 409
    assert response.json()["error"] == "CONFLICT"
```

---

### TC-STATE-01: 태스크 상태 전이 검증

```python
@pytest.mark.parametrize("from_status,to_status,expected", [
    ("todo", "doing", 200),
    ("done", "todo", 422),       # 되돌리기 불가
    ("cancelled", "doing", 422), # 취소 후 재개 불가
])
def test_task_state_transitions(from_status, to_status, expected, db_in_memory):
    item_id = create_item(status=from_status)
    response = client.patch(f"/api/items/{item_id}", json={"status": to_status})
    assert response.status_code == expected
```

---

### TC-PERF-01: Context Panel 500ms 이내

```python
def test_context_panel_performance(db_with_data, benchmark):
    result = benchmark(lambda: client.get(f"/partial/context/1"))
    assert result.status_code == 200
    assert benchmark.stats["mean"] < 0.5  # 500ms
```

---

### TC-CARRY-OVER-01: 이월 로직

```python
def test_carry_over_moves_todo_items(db_in_memory):
    # 어제 날짜 todo 항목 3개, done 항목 1개 생성
    response = client.post("/api/carry-over")
    assert response.json()["carried_count"] == 3
    assert response.json()["skipped_count"] == 1  # done은 이월 안 함
```

---

## 6. E2E Smoke Test (Playwright)

최소 3개 핵심 흐름만. Phase 5 M5 완료 후 작성.

| 시나리오 | 검증 포인트 |
|---------|-----------|
| S-01: Today's Flow 로드 → Quick Capture → 항목 확인 | 항목이 Today's Flow에 표시됨 |
| S-02: Inbox 항목 accept → items로 이동 | accept 후 Inbox 카운트 -1 |
| S-03: Morning Preview → Evening Review → 이월 | 이월 후 항목 상태 변경 확인 |

```python
# tests/e2e/test_core_flows.py
async def test_today_flow_and_capture(page):
    await page.goto("http://localhost:8000")
    await page.fill("[name=quick_capture]", "테스트 항목")
    await page.keyboard.press("Enter")
    await expect(page.locator(".flow-item")).to_contain_text("테스트 항목")
```

---

## 7. CI 구성 (최소)

```yaml
# .github/workflows/ci.yml (또는 로컬 pre-commit)
name: MC CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/unit tests/integration -x --cov=app --cov-report=term-missing
      - run: pytest tests/performance -x
```

**CI에서 제외** (로컬 수동):
- `tests/e2e/` (Playwright, 브라우저 필요)
- `tests/npu/` (NPU 실기기 필요)

**CI 통과 기준** (Phase 5 Gate):
- Unit + Integration 전체 pass
- 커버리지 ≥ 75%
- TC-CRED-01-05 (보안 테스트) 반드시 포함

---

## 8. 테스트 디렉터리 구조

```
schedule/
└── tests/
    ├── conftest.py          # db_in_memory, mock_ai_client, mock_bridge fixtures
    ├── unit/
    │   ├── test_items.py    # CRUD, 상태 머신
    │   ├── test_search.py   # FTS5/vec 라우팅
    │   ├── test_inbox.py    # Inbox routing, triage
    │   ├── test_carry_over.py
    │   └── test_secret_policy.py  # TC-CRED-01-05
    ├── integration/
    │   ├── test_core_api.py      # FastAPI TestClient
    │   ├── test_integrations.py  # GitHub mock, TG mock
    │   └── test_conflict.py      # .md 충돌 해결
    ├── performance/
    │   └── test_perf.py     # Context Panel, Search 타이밍
    ├── e2e/
    │   └── test_core_flows.py  # Playwright (수동/로컬)
    └── npu/
        └── test_npu_latency.py  # 실기기 수동 실행
```

---

## Change Log

| 버전 | 날짜 | 변경 내용 |
|------|------|---------|
| 1.0 | 2026-05-04 | 최초 작성. NPU 분리 전략, 크리티컬 TC 정의 |
