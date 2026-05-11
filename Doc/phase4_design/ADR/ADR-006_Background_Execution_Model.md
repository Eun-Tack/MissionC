# ADR-006: 백그라운드 실행 모델

> 상태: Accepted | 결정일: 2026-04-28
> 결정자: iet03 (코덱스 외부 검토 반영)

---

## 컨텍스트

FR-NOTIFY-01: "MC가 종료된 상태에서도 일정 5분 전 OS 토스트 알림". FR-INT-TG-01: "Telegram polling 상시 동작".

기존 설계는 core-api(Docker) + integrations(Docker) + ai-worker(호스트)였지만 "브라우저가 닫혀도 알림이 와야 한다"는 요구가 어디서 책임을 지는지 불명확했다. Docker 컨테이너만 살아 있으면 알림은 가능하지만, 컨테이너 자체를 사용자가 끄고 다시 키는 PC 사용 패턴에 맞지 않는다.

---

## 결정

**4-tier 실행 모델**: 알림·시크릿·NPU는 호스트 백그라운드 서비스로, UI·DB는 Docker로, 트레이는 옵셔널 launcher로 분리한다.

```
┌────────────────────────────────────────────────────────────────┐
│ Tier 1 — Always-On (Windows Task Scheduler / 부팅 시 자동)      │
│   • ai-worker                  (포트 8001)                      │
│   • secret-bridge              (포트 9999, loopback)            │
│   • notifier-daemon            (5분마다 폴링 → Windows Toast)   │
│                                                                │
│   ✅ PC가 켜져 있으면 항상 동작 — 브라우저/Docker 상태와 무관    │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ Tier 2 — Persistent (Docker Compose, 사용자 선택 항시 실행)      │
│   • core-api                   (포트 8000)                      │
│   • integrations               (포트 8002, TG polling 포함)     │
│                                                                │
│   ✅ 부팅 시 자동 시작 (compose --profile=auto)                  │
│   ⚠ 사용자가 docker stop 하면 멈춤 — Tier 1이 메우는 구조        │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ Tier 3 — On-Demand (브라우저)                                   │
│   • Edge/Chrome → http://localhost:8000                         │
│   • UI 사용 시에만 활성, 닫혀도 다른 Tier에 영향 없음            │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ Tier 4 — Optional Tray Launcher (V1.1, 미루기 가능)              │
│   • Pystray + plyer 미니 트레이 앱                               │
│   • "MC 열기" / "Docker 시작·중지" / "노티 켜기·끄기"            │
└────────────────────────────────────────────────────────────────┘
```

---

## 책임 분담 매트릭스

| 기능 | Tier | 컴포넌트 | 이유 |
|------|------|--------|------|
| OS 토스트 알림 (FR-NOTIFY-01) | 1 | notifier-daemon | Docker 정지 상황에서도 동작 |
| 일정 5분 전 알림 스케줄링 | 1 | notifier-daemon | SQLite 직접 read-only로 폴링 |
| Telegram polling (FR-INT-TG-01) | 2 | integrations | Docker 환경 의존성 격리 |
| Telegram 알림 발송 (FR-INT-TG-02) | 2 | integrations | API 토큰 + bot 라이브러리 |
| GitHub 캐시 갱신 (FR-GIT-04) | 2 | integrations | API 의존성 격리 |
| watchdog 파일 감지 | 2 | core-api | 핫 데이터 싱크 |
| AI 추론 (Whisper/BGE) | 1 | ai-worker | NPU 호스트 직접 접근 |
| 시크릿 접근 | 1 | secret-bridge | DPAPI 호스트 자원 |
| UI 렌더 | 3 | 브라우저 | 사용자 활성 시간만 |

### notifier-daemon 동작 (단순 폴링)

```python
# notifier_daemon/main.py — Windows 호스트 Python 프로세스
import sqlite3, time, datetime as dt
from plyer import notification

DB_PATH = r"C:\Users\iet03\Documents\Hub\agents\schedule\data\mc.db"
LEAD_MIN = 5

def tick():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    now = dt.datetime.utcnow()
    cutoff = (now + dt.timedelta(minutes=LEAD_MIN)).isoformat()
    rows = conn.execute("""
        SELECT i.id, i.title, s.start_at FROM schedules s
        JOIN items i ON i.id = s.item_id
        WHERE s.start_at BETWEEN ? AND ?
          AND i.status IN ('todo','doing')
          AND NOT EXISTS (SELECT 1 FROM notification_events e
                          WHERE e.item_id=i.id AND e.kind='lead' AND e.dismissed=0)
    """, (now.isoformat(), cutoff)).fetchall()
    for item_id, title, start_at in rows:
        notification.notify(title="MC", message=f"{title} — {start_at}", timeout=10)
        conn.execute("INSERT INTO notification_events(item_id, kind, sent_at) VALUES (?,?,?)",
                     (item_id, 'lead', now.isoformat()))
        conn.commit()

while True:
    tick()
    time.sleep(60)
```

- SQLite read-only 모드 + 별도 트랜잭션 → core-api 쓰기와 충돌 최소
- `notification_events` 테이블로 중복 발송 방지

---

## 부팅 자동 시작 (Task Scheduler XML)

```
tools/install_services.ps1
  schtasks /create /xml ai_worker.xml         /tn "MC-AIWorker"
  schtasks /create /xml secret_bridge.xml     /tn "MC-SecretBridge"
  schtasks /create /xml notifier_daemon.xml   /tn "MC-Notifier"
```

Docker는 Docker Desktop 자체 자동 시작 + `compose --profile=auto up -d`.

---

## 고려한 대안

| 옵션 | 이유로 제외 |
|------|-----------|
| 모든 것을 Docker | Tier 1 (NPU/시크릿/노티) 호스트 자원 접근 불가 |
| 모든 것을 호스트 (Docker 없음) | 모듈 경계 흐려짐. V2 모바일 PWA 모듈 확장 어려움 (ADR-001 근거 위반) |
| Tray 앱 메인 (Electron) | "Python 단일 스택" 제약 위반. CLAUDE.md 정책. |
| Cron-on-Docker | Docker 정지 시 알림 누락 — FR-NOTIFY-01 위반 |

---

## 결과

- **V1.0 출하 컴포넌트**: ai-worker, secret-bridge, notifier-daemon, core-api, integrations (5개)
- **V1.1**: tray launcher 추가 (옵션)
- 사용자 시나리오: PC 부팅 → 모든 백그라운드 자동 시작 → 브라우저 안 켜도 알림·TG 동작
- 장애 격리: Docker 다운 → Tier 1 살아 있어 알림은 동작, UI만 못 봄

### 근거

| 근거 유형 | 내용 |
|---------|------|
| BA 요구 | FR-NOTIFY-01 "종료 상태에서도 알림" |
| 외부 검토 | 코덱스 — Docker만으로는 백그라운드 책임 불명확 지적 |
| 하드웨어 | NPU·DPAPI 호스트 자원, Docker에서 우회 불가 |
