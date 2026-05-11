# TS-03: integrations 기술 명세

> 서비스: integrations | Docker 컨테이너 | 포트 8002
> ADR-001 참조 | FR-INT-TG-01~02, FR-INT-GH-01~02

---

## 책임 범위

- Telegram Bot polling (FR-INT-TG-01~02)
- GitHub REST API 캐시 (FR-INT-GH-01~02)
- (V1.1) Gmail OAuth 연동
- (V1.2) Google Drive Cold 티어 연동

---

## 기술 스택

| 라이브러리 | 버전 | 용도 |
|----------|------|------|
| FastAPI | 0.111+ | HTTP 서버 |
| python-telegram-bot | 21+ | Bot polling |
| PyGithub | 2.x | GitHub REST |
| httpx | 0.27+ | core-api 콜백 |
| APScheduler | 3.x | GitHub 15분 캐시 갱신 |

---

## Telegram Bot 흐름 (OQ-BA-03 해결 — polling 선택)

로컬 PC 공개 IP 없음 → webhook 불가 → polling 방식.

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # tg_inbound 테이블에 INSERT
    db.execute("INSERT INTO tg_inbound(tg_message_id, text) VALUES (?,?)",
               (update.message.message_id, text))
    # core-api에 신규 항목 생성 요청
    await core_api.post("/api/items", json={"title": text[:100], "source": "telegram"})
    await update.message.reply_text("✓ MC에 저장됨")
```

**알림 발송** (FR-INT-TG-02):
```
POST /notify/telegram
Body: {"chat_id": int, "message": str}
→ bot.send_message(chat_id, message)
```

---

## GitHub 캐시 갱신 (FR-INT-GH-01)

```python
@scheduler.scheduled_job('interval', minutes=15)  # BR-GIT-03
async def refresh_github_cache():
    repos = db.fetchall("SELECT DISTINCT github_repo FROM projects WHERE status='active'")
    for repo in repos:
        issues = gh_client.get_repo(repo).get_issues(state='open')
        # github_cache UPSERT (최대 50건/repo)
        for issue in issues[:50]:
            db.upsert_github_cache(repo, issue)
```

Rate Limit 처리: `X-RateLimit-Remaining < 10` → 갱신 건너뜀 + `settings` 에 `github_rate_limited_until` 기록 (BR-GIT-04).

---

## API 엔드포인트

```
GET  /github/issues/{repo}          → DB 캐시 반환 (JSON)
POST /github/issues                 → 이슈 생성 (FR-INT-GH-02)
POST /notify/telegram               → TG 메시지 발송
GET  /health                        → 서비스 상태
```

---

## V1.1 Gmail (확장 계획)

```python
# integrations/gmail.py (V1.1 추가)
# google-auth-oauthlib + gmail.readonly scope
# 수신 메일 → tg_inbound 유사 큐 → core-api
```

## V1.2 Google Drive Cold 티어 (확장 계획)

```python
# integrations/drive.py (V1.2 추가)
# drive.file scope (BR-AUTH-03b)
# archive_item(item_id) → Drive upload → local .md 삭제
# fetch_cold_body(cold_path) → Drive 다운로드 → 임시 반환
```
