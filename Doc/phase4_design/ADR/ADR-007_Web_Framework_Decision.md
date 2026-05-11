# ADR-007: 웹 프레임워크 결정 — http.server → FastAPI

> 상태: Accepted | 결정일: 2026-04-28
> 결정자: iet03 (코덱스 외부 검토 반영)

---

## 컨텍스트

CLAUDE.md / Phase 0~2 가설 단계: "Python + http.server" 후보로 명시. Phase 3 BA 07_Summary §8: "Python http.server → htmx + Tailwind CDN" 권장.

Phase 4 ADR-001/TS-01에서 **FastAPI + uvicorn**을 도입했으나 변경 사유가 명시되지 않아 구현자가 어느 문서를 우선해야 할지 애매했다. 외부 검토(코덱스)에서 명시 결정 로그 부족 지적.

---

## 결정

**FastAPI + uvicorn**을 V1.0 웹 프레임워크로 채택한다.

### 변경 사유

| 항목 | http.server | FastAPI | 선택 이유 |
|------|------------|---------|---------|
| HTTP 라우팅 | 수동 if/else | 데코레이터 + 타입 힌트 | 26개 FR × 다중 엔드포인트 — 수동 라우팅 유지비용 큼 |
| 폼/JSON 파싱 | 수동 (cgi 모듈, deprecated 3.13) | Pydantic 자동 | Quick Capture/Settings 다수 입력 처리 |
| Lifespan hook | 없음 | `@asynccontextmanager` | watchdog Observer, sqlite-vec 로딩 시점 명확화 |
| 비동기 IO | 동기만 | async/await | ai-worker HTTP 호출 시 블로킹 회피 |
| OpenAPI 자동 문서 | 없음 | 자동 (`/docs`) | 1인 개발 디버깅 편의 |
| 의존성 부하 | 0 (stdlib) | ~10MB (FastAPI + Pydantic + uvicorn) | Docker 이미지 — 무시 가능 |
| 학습 곡선 | 낮음 | 낮음 (htmx 통합 유지) | iet03 기 사용 경험 |

### 호환성

- htmx 부분 응답: FastAPI `Jinja2Templates` + `HTMLResponse` 그대로 가능
- 정적 파일 서빙: `StaticFiles` 마운트
- 빌드 단계: 여전히 없음 (FastAPI는 런타임 라이브러리)
- "Python 단일 스택" 정책: 위반 없음

### "Electron 금지" 정책과의 관계

CLAUDE.md "Electron 금지"는 **데스크톱 셸을 JS로 만들지 말 것** 의미였다. FastAPI는 백엔드 프레임워크로, JS 데스크톱 런타임과 무관 → 정책 호환.

---

## 고려한 대안

| 옵션 | 이유로 제외 |
|------|-----------|
| http.server (계속) | 26 FR × 라우팅 수동 관리 비용 + cgi 모듈 deprecation |
| Flask | 비동기 우선 아님, ai-worker HTTP 호출 시 핸들러 블로킹 |
| Starlette (FastAPI 하위) | Pydantic 통합 등 FastAPI 상위 기능 손실 |
| Litestar | iet03 미경험 — 학습 곡선 |

---

## 결과

- BA 07_Summary §8 "http.server → htmx" 권장은 **이 ADR로 supersede**
- TS-01 core-api 기술 스택 재확인
- Phase 5 Coder는 본 ADR 우선
- Pydantic V2 사용 (FastAPI 0.100+ 기본)

### 근거

| 근거 유형 | 내용 |
|---------|------|
| 정책 | Python 단일 스택 + Electron 금지 — 위반 없음 |
| 외부 검토 | 코덱스 — 결정 로그 명시 필요 |
| 기술 비교 | 라우팅·비동기·Lifespan 측면에서 FastAPI 압승 |
