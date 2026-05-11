# V1.5 Radial Command Palette — Overview

> **버전**: V1.5 | **작성일**: 2026-05-10 | **승인**: iet03 (`[iet03]` 자가검증 결과 V1.5 시작점으로 확정)
> **대상 독자**: 개발자, 디자이너, QA — 협업 핸드오프 문서

---

## 1. 한 줄 정의

`Cmd+K` 진입 시 검색박스가 아닌 **8 슬라이스 방사형 메뉴** 가 화면 중앙에 떠서, 사용자의 모든 컨텍스트 진입점을 1단축키로 통일한다.

---

## 2. 왜 이것이 V1.5 의 시작점인가

V1.0 의 핵심 가치 (`스케줄·프로젝트·문서·생각이 한 컨텍스트 안에서 연결`) 는 **사용자가 화면을 전환하지 않을 때** 가장 강하게 작동한다. Radial Palette 는 모든 컨텍스트 진입을 1초 안에 처리해 *전환 비용 = 0* 을 달성한다.

3축 검증 (`[iet03]` 자가검증 결과 — 2026-05-10):

| 축 | 점수 | 근거 |
|---|------|------|
| 시스템 목적 부합 | 🟢🟢 | 어디서든 모든 모드 진입 = 컨텍스트 전환 비용 0 |
| 실효성 | 🟢🟢 | 일 30~50 회 사용 (가장 빈도 높은 진입점) |
| 혁신성 | 🟢🟢 | 게임/Photoshop radial-menu 패턴을 생산성 도구 영역에 도입 — Notion/Linear/Obsidian 어디에도 없음 |

---

## 3. V1.5 산출물 목록

| 파일 | 대상 독자 | 용도 |
|------|----------|------|
| `00_Overview.md` (이 문서) | PM / 모든 멤버 | 진입점 + 패키지 맵 |
| `PRD_RADIAL.md` | PM / BA / 개발자 | FR 정의, 페르소나 시나리오, 스코프 |
| `ADR-011_Radial_Command_Palette.md` | 아키텍트 / 시니어 개발자 | UI 패러다임 결정 + 대안 비교 |
| `Screen_Spec_Radial.md` | 디자이너 / 프론트엔드 | ASCII 목업, 키 맵, 인터랙션 상태 |
| `BR_AC_Radial.md` | BA / 개발자 / QA | IF-THEN 비즈니스 규칙 + Gherkin AC |
| `Implementation_Guide.md` | 개발자 (핸드오프 1차 독자) | 코드 위치 가이드, 빌드 순서, 위험 |

---

## 4. 스코프

### V1.5 포함
- 8 슬라이스 radial menu (캡처/검색/오늘/회고/프로젝트/음성/어제/컨텍스트)
- 키보드 단독 조작 (마우스 보조)
- V1.0 기존 엔드포인트 재사용 (신규 백엔드 0)
- 기존 컨텍스트 패널과 통합

### V1.5 미포함 (V1.6+ 후속)
- LLM 추천 슬라이스 (Phi-3 NPU 통합 → V2.0)
- Magnetic Inbox 카드 모드 → V1.6
- Bidirectional Anchors → V1.7
- Radial 슬라이스 사용자 정의 (커스터마이징) → V2.0

---

## 5. 성공 기준 (V1.5 종료 게이트)

| 지표 | 목표 | 측정 |
|------|------|------|
| 진입 응답 시간 | ≤ 100 ms | `Cmd+K` 입력 ~ radial 표시까지 |
| 슬라이스 선택 시간 | ≤ 800 ms | `Cmd+K` ~ 액션 완료 평균 |
| 키보드 전용 조작 가능성 | 100% | 마우스 미사용으로 8 슬라이스 모두 도달 |
| AC Pass Rate | ≥ 95% | `BR_AC_Radial.md` 의 Gherkin 시나리오 |
| 회귀 테스트 | V1.0 기능 영향 0 | 기존 13 라우터 / 21 템플릿 정상 동작 |

---

## 6. 의존성 / 전제

- **V1.0 출시 완료** — 2026-05-10 closed
- **htmx + Jinja2 스택 유지** — ADR-002 레이어드 렌더링 전략 준수
- **신규 라이브러리 0** — 기존 `htmx 1.9.12`, Tailwind CDN, Pretendard 폰트만 사용
- **기존 컨텍스트 패널 재사용** — `templates/partials/context_panel.html` (변경 없음)

---

## 7. 작업 일정

| 주 | 단계 | 산출 |
|----|------|------|
| W1 (2026-05-11~17) | 디자인 검토 | Screen Spec 검토, 인터랙션 프로토타이핑 (HTML 단일 파일) |
| W2 (2026-05-18~24) | 구현 | 신규 `templates/partials/radial_palette.html` + JS, base.html 키 핸들러 |
| W3 (2026-05-25~31) | QA + 통합 | Gherkin AC 수동 워크스루, V1.0 회귀 검증, 게이트 통과 |

---

## 8. 핵심 파일 변경 요약 (개발자 빠른 참조)

```
신규:
  src/core_api/templates/partials/radial_palette.html
  src/core_api/static/radial.css
  src/core_api/static/radial.js

수정 (최소):
  src/core_api/templates/base.html  # script include + Cmd+K listener mount

신규 백엔드 엔드포인트: 0 (전부 클라이언트 사이드 라우팅 + 기존 endpoint 재사용)
DB 마이그레이션: 0
```

상세 위치는 `Implementation_Guide.md` 참조.
