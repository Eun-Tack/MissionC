# Implementation Guide — Radial Command Palette V1.5

> **대상 독자**: 이 기능을 구현할 개발자 (1차 핸드오프 문서)
> **전제**: V1.0 코드베이스 (`src/core_api/`) 이해. FastAPI + htmx + Jinja2 + SQLite.
> **상위 문서**: `00_Overview.md` (시작점), `PRD_RADIAL.md` (요구사항), `Screen_Spec_Radial.md` (UI), `BR_AC_Radial.md` (검증), `ADR-011` (결정 이유)

---

## 0. 시작 전 체크리스트

```
[ ] V1.0 출시 완료 확인 (Doc/phase7_release/Postmortem.md)
[ ] 로컬 dev 서버 정상 동작 (uvicorn run.py)
[ ] V1.0 의 7 페이지 모두 200 OK 확인 (스모크 테스트)
[ ] 이 문서를 끝까지 읽고 PRD/ADR/Screen Spec/BR_AC 4종 모두 일독
[ ] 의문점 발견 시 PR/issue 코멘트로 질문 (자체 결정 X)
```

---

## 1. 작업 범위 — 변경되는 파일 목록

### 1.1 신규 파일 (3 개)

| 파일 | 책임 | 예상 line |
|------|------|----------|
| `src/core_api/templates/partials/radial_palette.html` | DOM 구조 (SVG 8 슬라이스 + 중앙 hub + InlineForm 컨테이너) | ~120 |
| `src/core_api/static/radial.css` | 글래스 모피즘 + 모션 키프레임 + 반응형 | ~180 |
| `src/core_api/static/radial.js` | 키 핸들러 + 슬라이스 dispatch + Web Animations API + 컨텍스트 인지 | ~280 |

### 1.2 수정 파일 (1 개, 최소)

| 파일 | 변경 내용 | 영향 |
|------|-----------|------|
| `src/core_api/templates/base.html` | 1) `radial_palette.html` include / 2) `radial.css` link / 3) `radial.js` script | 기존 페이지 영향 0 (radial 은 hidden 상태로 추가) |

### 1.3 변경 없음 (재사용)

| 파일 | 재사용 이유 |
|------|------------|
| `src/core_api/routers/items.py` | 캡처 슬라이스가 기존 POST `/api/items` 호출 |
| `src/core_api/routers/search.py` | 검색 슬라이스가 기존 GET `/api/cmdk` 호출 |
| `src/core_api/routers/voice.py` | 음성 슬라이스가 기존 STT 모달 트리거 |
| `src/core_api/routers/review.py` | 회고 슬라이스가 기존 `/morning` `/evening` 라우트 |
| `src/core_api/templates/partials/context_panel.html` | 컨텍스트 슬라이스가 기존 패널 토글 |
| **DB 스키마** | **마이그레이션 불필요** |

---

## 2. 빌드 순서 (권장 — 검증 가능한 단계로 분할)

### Step 1: 정적 자산 추가 + base.html 통합 (반나절)
```
1. src/core_api/static/radial.css 작성 (시각만, 키 핸들러 X)
2. src/core_api/templates/partials/radial_palette.html 작성 (DOM)
3. base.html 에 include + link 추가
4. 모든 페이지에서 radial 이 *존재만* 하고 hidden 상태인지 확인
```

**검증**: 7 페이지 진입 시 DOM inspector 로 `<div class="radial" hidden>` 존재 확인.
**완료 기준**: AC-RADIAL-30 (V1.0 회귀 0) 통과.

### Step 2: 키 핸들러 + 진입/종료 (1 일)
```
1. radial.js 작성 시작 — RadialPalette 클래스
2. Cmd+K / Ctrl+K / / / Esc 핸들러 (capture phase)
3. Web Animations API 로 spring 진입 모션
4. window.openRadial() / window.closeRadial() 노출
```

**검증**: 모든 페이지에서 Cmd+K → 진입, Esc → 종료. 모션 100ms.
**완료 기준**: AC-RADIAL-22 (토글) 통과.

### Step 3: 8 슬라이스 강조 + 키 매핑 (1 일)
```
1. SVG 8 등분 path 좌표 계산 (반지름 240 / hub 80, polar to cartesian)
2. 화살표 8 방향 → 슬라이스 인덱스 매핑
3. 단일 문자 단축키 (c/s/t/x/r/y/p/v) → 슬라이스 인덱스 매핑
4. 강조 시각 (CSS transition) + 중앙 hub 라벨 동기화
5. wrap-around 동작 (좌우/상하 끝에서)
```

**검증**: 키보드만으로 8 슬라이스 모두 도달.
**완료 기준**: AC-RADIAL-21 (wrap-around) 통과.

### Step 4: 4 가지 액션 패턴 dispatch (1.5 일)
```
1. Direct route (오늘/회고/프로젝트) — location.href = ...
2. Inline form (캡처/검색) — 중앙 hub morph + form 활성
3. Modal (음성/어제) — 기존 모달 호출 또는 신규 모달
4. In-place expand (컨텍스트) — 현재 페이지의 컨텍스트 패널 토글
```

**검증**: 각 슬라이스 실행 시 올바른 패턴으로 동작.
**완료 기준**: AC-RADIAL-01, 02 통과.

### Step 5: 컨텍스트 인지 (FR-RADIAL-03) (0.5 일)
```
1. getRadialContext() 함수 — URL pattern 매칭
2. 캡처 슬라이스 payload 에 project_id 자동 포함
3. 회고 슬라이스의 시간대 분기 (BR-RADIAL-22, 23)
4. 비활성 슬라이스 처리 (gray + shake on attempt)
```

**검증**: `/project/12` 에서 캡처 시 자동 연결, 정오 경계 동작.
**완료 기준**: AC-RADIAL-03, 11, 20 통과.

### Step 6: 접근성 + 회귀 + QA (0.5 일)
```
1. ARIA role + aria-label
2. prefers-reduced-motion 분기
3. AC 12 종 수동 워크스루
4. V1.0 7 페이지 회귀 스모크
```

**완료 기준**: AC 12 종 중 11+ 통과 (95%).

**총 예상**: ~5 일 (1 인 풀타임 기준).

---

## 3. 핵심 코드 스켈레톤

### 3.1 `radial_palette.html` (요지)
```html
{# Loaded once in base.html. Hidden by default. #}
<div id="radial-root" class="radial" role="menu" aria-label="명령 팔레트" hidden>
  <div class="radial-overlay" data-action="close"></div>
  <div class="radial-wheel" role="presentation">
    <svg viewBox="0 0 480 480" class="radial-svg" aria-hidden="true">
      {# 8 slice paths (계산은 JS 에서) — id="slice-0" ~ "slice-7" #}
    </svg>
    <div class="radial-labels" aria-hidden="true">
      {# 8 라벨 위치 (각도 마다 12 시 = -90deg) #}
    </div>
    <div class="radial-hub" aria-live="polite">
      <span class="hub-label">Cmd+K 메뉴</span>
      <input class="hub-input" hidden aria-label="캡처 입력">
    </div>
  </div>
</div>
```

### 3.2 `radial.js` 의 핵심 클래스 (요지)
```js
const SLICES = [
  { id: 0, angle: -90,  symbol: '📥', label: '캡처',     keys: ['c', 'ArrowUp'],     pattern: 'inline-form' },
  { id: 1, angle: -45,  symbol: '🔍', label: '검색',     keys: ['s'],                pattern: 'inline-form' },
  { id: 2, angle:   0,  symbol: '📅', label: '오늘',     keys: ['t', 'ArrowRight'],  pattern: 'route',  href: '/' },
  { id: 3, angle:  45,  symbol: '🪟', label: '컨텍스트', keys: ['x'],                pattern: 'expand' },
  { id: 4, angle:  90,  symbol: '🌙', label: '회고',     keys: ['r', 'ArrowDown'],   pattern: 'route',  hrefFn: timeAwareReview },
  { id: 5, angle: 135,  symbol: '🕘', label: '어제',     keys: ['y'],                pattern: 'modal' },
  { id: 6, angle: 180,  symbol: '🗂', label: '프로젝트', keys: ['p', 'ArrowLeft'],   pattern: 'route',  href: '/hierarchy' },
  { id: 7, angle: -135, symbol: '🎙', label: '음성',     keys: ['v'],                pattern: 'modal' },
];

class RadialPalette {
  constructor() {
    this.root = document.getElementById('radial-root');
    this.open = false;
    this.focusedIdx = null;
    this._bindGlobalKeys();
    this._bindInternalEvents();
  }

  _bindGlobalKeys() {
    // capture phase — 다른 핸들러보다 먼저
    document.addEventListener('keydown', (e) => {
      if (this._isMetaK(e))         { e.preventDefault(); this.toggle(); return; }
      if (e.key === '/')            { if (!this._isInputFocused()) { e.preventDefault(); this.show(); } return; }
      if (this.open && e.key === 'Escape') { e.preventDefault(); this.hide(); return; }
      if (this.open) this._routeKey(e);
    }, true);
  }

  show()       { this.root.hidden = false; this._animateIn(); this.open = true; }
  hide()       { this._animateOut().then(() => this.root.hidden = true); this.open = false; }
  toggle()     { this.open ? this.hide() : this.show(); }

  _routeKey(e) {
    // 화살표 → 강조 / 단일 문자 → 즉시 실행
    // BR-RADIAL-10~14 구현
  }

  _executeSlice(idx) {
    const ctx = this._getContext();          // FR-RADIAL-03
    const slice = SLICES[idx];
    if (slice.disabled) return this._shake(idx);
    switch (slice.pattern) {
      case 'route':       this._route(slice, ctx); break;
      case 'inline-form': this._inlineForm(slice, ctx); break;
      case 'modal':       this._modal(slice, ctx); break;
      case 'expand':      this._expand(slice, ctx); break;
    }
  }

  _animateIn() {
    // Web Animations API — spring(380, 28)
    this.root.querySelector('.radial-wheel').animate(
      [{transform:'scale(0.8)', opacity:0}, {transform:'scale(1)', opacity:1}],
      {duration: 120, easing: 'cubic-bezier(0.32, 0.72, 0, 1)', fill: 'both'}
    );
  }

  _isMetaK(e) {
    return (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k';
  }

  _isInputFocused() {
    const el = document.activeElement;
    return el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) && !el.readOnly;
  }
}

window.radialPalette = new RadialPalette();
window.openRadial = () => window.radialPalette.show();
window.closeRadial = () => window.radialPalette.hide();
```

### 3.3 base.html 수정 (3 줄)
```html
<!-- <head> 안 -->
<link rel="stylesheet" href="/static/radial.css">

<!-- <body> 끝 직전 -->
{% include "partials/radial_palette.html" %}
<script src="/static/radial.js" defer></script>
```

---

## 4. 위험 요소 + 회피 전략

| 위험 | 발생 가능성 | 영향 | 회피 |
|------|-----------|------|------|
| `Cmd+K` 가 다른 페이지의 핸들러와 충돌 | 중 | 키 입력 무반응 | capture phase listener 사용 + `e.stopPropagation()` |
| Web Animations API 가 일부 환경에서 미지원 | 낮음 | 모션 깨짐 | `if (!el.animate)` fallback → 즉시 표시 |
| SVG path 8 등분 좌표 계산 오류 | 중 | 슬라이스 클릭 영역 어긋남 | 단위 테스트 — `polarToCartesian(angle, radius)` 헬퍼 분리 |
| 모바일 브라우저 viewport 작음 | 중 | radial 잘림 | viewport ≤ 480px 시 표시 안 함 (Screen Spec § 8) |
| InlineForm 의 input 이 모바일 키보드와 충돌 | 낮음 | 입력 어려움 | viewport 작을 때 InlineForm 만 fullscreen 변환 (V1.6) |
| 단일 문자 단축키가 한국어 IME 와 충돌 | 중 | 입력 차단 | IME 활성 시 (`e.isComposing`) 단일 문자 무시 |
| 음성 슬라이스의 마이크 권한 미요청 | 중 | 슬라이스 무용 | 모달 진입 시 권한 요청, BR-RADIAL-25 |

---

## 5. 자체 검증 체크리스트 (구현자 → 자가 PR 전)

### 기능
```
[ ] Cmd+K 모든 페이지에서 진입
[ ] Esc 닫힘 (모션 100ms)
[ ] 토글 (Cmd+K 두 번 → 닫힘)
[ ] 화살표 8 방향 모두 강조 동작
[ ] 단일 문자 8 개 모두 즉시 실행
[ ] wrap-around 양 방향 동작
[ ] 입력 필드 포커스 중 / 키 통과
[ ] 입력 필드 포커스 중 Cmd+K 진입
```

### 컨텍스트 인지
```
[ ] /project/{id} 에서 캡처 → project_id 자동 포함 (DB 확인)
[ ] /inbox 에서 캡처 슬라이스 라벨 변경
[ ] 시각 < 12:00 → /morning, ≥ 12:00 → /evening
[ ] 마이크 권한 거부 시 음성 슬라이스 회색
```

### 시각 / 모션
```
[ ] 글래스 모피즘 backdrop-filter 적용
[ ] 슬라이스 강조 시각 차이 명확
[ ] 중앙 hub 라벨 24px 변경 동기화
[ ] InlineForm morph 애니메이션 200ms
[ ] prefers-reduced-motion 시 모션 0
```

### 회귀
```
[ ] 7 페이지 모두 200 OK (smoke)
[ ] 기존 페이지 키 입력 영향 없음
[ ] Lighthouse 접근성 점수 ≥ 90
```

---

## 6. PR 제출 시 필요 항목

```
[ ] 위 § 5 체크리스트 모두 ✓
[ ] AC 12 종 중 11 + 통과 (스크린샷 또는 영상 첨부)
[ ] V1.5_Radial_Palette/ 문서 6 종 변경 없음 (문서는 Phase 4 산출 → 코드 PR 에서 수정 X)
[ ] 위험 요소 § 4 중 발생한 것 PR 본문에 기재
[ ] 신규 의존성 0 확인 (package.json, requirements.txt 변경 없음)
```

---

## 7. 완료 후 — Phase 6 진입 방법

이 모듈은 **V1.0 의 Phase 6 절차를 그대로 따른다**. 즉:

1. 코드 작성 완료 → self review (위 § 5)
2. PR 제출 (자가 또는 외부 리뷰)
3. `Doc/phase4_design/V1.5_Radial_Palette/` 의 BR_AC 통과 확인
4. `Doc/phase6_review/V1.5_Review_Summary.md` 작성 — Phase 6 게이트 (AC ≥ 95%, P0 = 0)
5. 통과 시 → `Doc/phase7_release/Release_Notes_v1.5.md` 작성 + V1.5 태깅

---

## 8. 질문이 생길 수 있는 지점

이 문서를 읽고도 결정 불가한 항목은 **자체 결정하지 말고 질문**:

| 항목 | 결정 필요 시 |
|------|-------------|
| 슬라이스 8 개 외 추가 / 변경 | iet03 승인 — ADR supersede 필요 |
| 신규 의존성 추가 | PRD § 의존성 섹션 위반 — iet03 승인 |
| 신규 백엔드 엔드포인트 추가 | PRD § 5 매트릭스 위반 — 재검토 |
| AC 시나리오 변경 / 추가 | BR_AC 변경 — Phase 4 재진입 |
| ADR 결정 (radial vs 표준 cmdk) 변경 | ADR-011 supersede — iet03 승인 |
| UI 시각 디테일 (색상/폰트/사이즈) | Screen Spec 범위 내 자율 — 단, ADR-002 Layer 2/3 준수 |

---

## 9. 부록 — V1.0 코드 참고 위치

구현 시 참조할 V1.0 코드:

| 참조 항목 | 파일 | 라인 (참고용) |
|----------|------|---------------|
| FastAPI 라우터 등록 패턴 | `src/core_api/main.py` | L13, L57-72 |
| Jinja2 템플릿 + base.html | `src/core_api/templates/base.html` | 전체 |
| htmx 호출 + OOB 패턴 | `src/core_api/routers/items.py:create_item` | L82-144 |
| 컨텍스트 패널 토글 (V1.5 의 expand 패턴 참고) | `src/core_api/routers/flow.py` + `templates/partials/context_panel.html` | flow.py L235-250 |
| FTS5 검색 응답 | `src/core_api/routers/search.py` | `/api/cmdk` 핸들러 |
| Web Animations API 사용 예 (V1.0 참고) | `src/core_api/templates/calendar.html` | 신규 이벤트 드로어 부분 |
| 음성 STT 모달 (재사용 대상) | `src/core_api/routers/voice.py` + Whisper 호출 | 전체 |

이 문서를 끝까지 읽고 시작하시기 바랍니다. 질문이 있으면 PR 코멘트로 — 자체 판단으로 PRD/ADR 범위를 벗어나지 마세요.
