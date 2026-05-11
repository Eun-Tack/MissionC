# TS-01: core-api 기술 명세

> 서비스: core-api | Docker 컨테이너 | 포트 8000
> ADR-001, ADR-002, ADR-004 참조

---

## 책임 범위

- htmx UI 서빙 (HTML 부분 응답)
- SQLite CRUD (items, tags, projects, schedules, settings)
- 비즈니스 로직 (이월, 충돌 감지, FTS5/벡터 검색 라우팅)
- watchdog 파일 감지 → DB 동기화
- ai-worker, integrations 서비스 오케스트레이션

---

## 기술 스택

| 레이어 | 라이브러리 | 버전 |
|--------|----------|------|
| 웹 프레임워크 | FastAPI | 0.111+ |
| ASGI 서버 | uvicorn | 0.29+ |
| 템플릿 | Jinja2 | 3.1+ |
| DB | sqlite3 (stdlib) + sqlite-vec | — |
| 파일 감지 | watchdog | 4.0+ |
| HTTP 클라이언트 | httpx | 0.27+ |

---

## URL 라우팅

```
GET  /                     → SC-01 Today's Flow
GET  /morning              → SC-07 Morning Preview
GET  /evening              → SC-07 Evening Review
GET  /search               → SC-02 검색 결과 (htmx partial)
GET  /project/{id}         → SC-06 프로젝트 상세
GET  /settings             → SC-08 설정

# htmx 부분 응답 (hx-target)
GET  /partial/flow          → Today's Flow 아이템 목록
GET  /partial/context/{id}  → 컨텍스트 패널 내용 (≤500ms, FR-FLOW-03)
GET  /partial/calendar      → 캘린더 토글 뷰
POST /partial/search        → 검색 결과

# CRUD API
POST   /api/items           → 항목 생성 (FR-CAP-01)
PATCH  /api/items/{id}      → 상태 변경, 인라인 편집
DELETE /api/items/{id}      → 삭제
POST   /api/items/{id}/tags → 태그 추가 (FR-CAP-02)
POST   /api/carry-over      → 이월 실행 (FR-DAY-03)
GET    /api/export          → JSON 내보내기 (FR-BACKUP-01)
```

---

## 컨텍스트 패널 응답 명세 (FR-FLOW-03)

```
GET /partial/context/{item_id}
→ 200 OK, Content-Type: text/html

응답 구조 (Jinja2 렌더):
  <div id="context-panel" ...>
    <section class="tags">   -- 태그 + 프로젝트 칩
    <section class="memo">   -- .md 파일 첫 500자 + "열기" 링크
    <section class="issues"> -- github_cache 최대 5건
  </div>

지연 목표: ≤ 500ms (DB 3쿼리 병렬: tags, memo HEAD, github_cache)
```

---

## 검색 라우팅 로직

```python
@app.post("/partial/search")
async def search(q: str = Form(...)):
    count = db.scalar("SELECT COUNT(*) FROM items WHERE location='hot'")
    if count < 30:
        rows = db.fts_search(q)          # FTS5
    else:
        vec = await ai_client.embed(q)   # ai-worker HTTP
        rows = db.vec_search(vec)        # sqlite-vec
    return templates.TemplateResponse("partials/search_results.html", {"rows": rows})
```

---

## watchdog 통합

```python
# 컨테이너 내 /app/mc-notes 감시
observer = Observer()
observer.schedule(MCFileHandler(db), path="/app/mc-notes", recursive=True)
observer.start()  # lifespan에서 시작
```

---

## 충돌 감지 (FR-CONFLICT-01)

```sql
-- 신규 일정 추가 전 겹침 체크 (BR-CONFLICT-01)
SELECT s.id FROM schedules s
JOIN items i ON i.id = s.item_id
WHERE i.status NOT IN ('done','cancelled')
  AND s.start_at < :new_end
  AND s.end_at   > :new_start
LIMIT 1;
```

충돌 발생 시 htmx OOB로 경고 배너 + 3가지 옵션 버튼 반환 (이동/겹침허용/취소).
