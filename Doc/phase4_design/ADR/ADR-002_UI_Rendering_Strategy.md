# ADR-002: UI 렌더링 전략

> 상태: Accepted | 결정일: 2026-04-27
> 결정자: iet03 (혁신적·실험적 UI 요구 + V1.0 단일 스택 제약 동시 만족)

---

## 컨텍스트

iet03은 "흔해빠진 방법 말고 실험적이고 도전적이고 혁신적"인 UI를 명시적으로 요구했다.
동시에 V1.0은 Python 단일 스택(http.server + htmx + Tailwind CDN)이라는 기술 제약이 있다.

**핵심 긴장**: SPA 프레임워크(React/Vue/Svelte) 없이 어떻게 혁신적 인터랙션을 구현하는가.

---

## 결정

**레이어드 렌더링 아키텍처**: htmx를 데이터 레이어로, 네이티브 브라우저 API를 시각 레이어로 분리한다.

```
┌─────────────────────────────────────────────────────────┐
│  Rendering Stack                                        │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Layer 4: Ambient / Generative                   │   │
│  │  • Canvas 2D — Time Constellation (SC-03 V1.2)  │   │
│  │  • WebGL (iGPU) — 파티클 배경 (V1.1 선택)         │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Layer 3: Motion / Spatial                       │   │
│  │  • View Transitions API — 페이지 전환            │   │
│  │  • Web Animations API (WAAPI) — 컨텍스트 패널   │   │
│  │  • CSS @starting-style — 마운트 애니메이션        │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Layer 2: Glass / Material                       │   │
│  │  • CSS backdrop-filter: blur(20px)              │   │
│  │  • CSS color-mix() — 다이나믹 팔레트             │   │
│  │  • CSS @property (Houdini) — 커스텀 프로퍼티     │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Layer 1: Data / Structure                       │   │
│  │  • htmx — 서버 부분 교체 (hx-swap oob)           │   │
│  │  • Tailwind CDN — 유틸리티 클래스               │   │
│  │  • Alpine.js (경량) — 순수 클라이언트 상태        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 레이어별 기술 결정

### Layer 1: 데이터 레이어 (htmx + Alpine.js)

| 기술 | 용도 | 이유 |
|------|------|------|
| htmx 2.x | 서버 부분 응답, OOB 스왑 | Python http.server와 직접 통합. SPA 빌드 불필요. |
| Alpine.js 3.x | 로컬 UI 상태 (패널 열림/닫힘, 탭 선택) | 8KB. htmx가 처리 못하는 즉시 반응 상태만 담당. |
| Tailwind CDN | 유틸리티 CSS | 빌드 불필요. 커스텀 `tailwind.config` CDN 파라미터로 확장. |

**htmx OOB 패턴** (컨텍스트 패널):
```html
<!-- 서버 응답 — 헤더 없이 2개 DOM 동시 교체 -->
<div id="context-panel" hx-swap-oob="true">...</div>
<div id="item-row-42" hx-swap-oob="true">...</div>
```

### Layer 2: Glass / Material 시스템

```css
/* Design Token — CSS @property (Houdini) */
@property --glass-opacity {
  syntax: '<number>';
  inherits: true;
  initial-value: 0.08;
}

.glass {
  background: color-mix(in oklch, var(--surface) 92%, transparent);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid color-mix(in oklch, white 15%, transparent);
}

/* 다크 퍼스트 — 시스템 테마 반응 */
@media (prefers-color-scheme: dark) {
  :root { --surface: oklch(15% 0.01 265); }
}
```

**주요 효과**:
- `backdrop-filter` — Voice Glass 오버레이, 컨텍스트 패널 배경
- `color-mix(in oklch)` — 태그 색상 자동 조화 (hue rotation으로 팔레트 생성)
- CSS `@property` — `--glass-opacity` 애니메이션 가능한 커스텀 프로퍼티

### Layer 3: 모션 시스템

```javascript
// WAAPI — 컨텍스트 패널 0.5s 이내 열림 (FR-FLOW-03 AC 기준)
const panel = document.getElementById('context-panel');
panel.animate([
  { opacity: 0, transform: 'translateX(12px)' },
  { opacity: 1, transform: 'translateX(0)' }
], { duration: 280, easing: 'cubic-bezier(0.16, 1, 0.3, 1)', fill: 'forwards' });
```

| 전환 | API | 목표 시간 |
|------|-----|---------|
| 컨텍스트 패널 열림 | WAAPI | ≤ 280ms |
| 페이지 이동 | View Transitions API | ≤ 160ms |
| 아이템 마운트 | CSS @starting-style | ≤ 120ms |
| 캘린더 토글 | CSS transition | ≤ 80ms |

**View Transitions API** (SC 간 이동):
```javascript
document.startViewTransition(() => {
  htmx.trigger('#main-content', 'loadPage', { path: '/morning' });
});
```

### Layer 4: Canvas / Generative

| 화면 | 기술 | 버전 |
|------|------|------|
| SC-03 Time Constellation | Canvas 2D (requestAnimationFrame) | V1.2 |
| 파티클 배경 (선택) | WebGL (iGPU — ANGLE) | V1.1 |
| 음파 시각화 | Canvas 2D + Web Audio API AnalyserNode | V1.1 (Voice Glass) |

**Time Constellation 렌더 루프** (설계 스케치):
```javascript
// 24시간 방사형 — 각도 = 시각 * 15deg
function drawConstellation(ctx, items) {
  const cx = ctx.canvas.width / 2, cy = ctx.canvas.height / 2;
  items.forEach(item => {
    const angle = (item.hour * 60 + item.minute) / 1440 * Math.PI * 2 - Math.PI / 2;
    const r = 40 + item.durationMin * 0.8; // 시간 길이 → 반경
    ctx.beginPath();
    ctx.arc(cx + Math.cos(angle) * r, cy + Math.sin(angle) * r, 3, 0, Math.PI * 2);
  });
}
```

---

## 디자인 시스템 기반

### 색상 — OKLCH 다크 퍼스트

```css
:root {
  /* Base */
  --bg:       oklch(12% 0.008 265);   /* near-black blue-tint */
  --surface:  oklch(18% 0.010 265);
  --border:   oklch(30% 0.012 265);

  /* Accent */
  --accent:   oklch(72% 0.18 255);    /* electric indigo */
  --positive: oklch(72% 0.16 155);    /* sage green */
  --warn:     oklch(75% 0.18 50);     /* amber */

  /* Text */
  --text-hi:  oklch(92% 0.005 265);
  --text-lo:  oklch(55% 0.008 265);
}
```

### 타이포그래피

- **한글**: Pretendard Variable (CDN) — 가변 폰트로 weight animation 가능
- **등폭**: JetBrains Mono (CDN) — 시간·코드 표시
- **스케일**: 12/13/14/16/20/28px (T-shirt sizing 아닌 기능 기반)

### 간격 — 4px 그리드

컴포넌트 내부 `4/8/12/16px`, 섹션 간격 `24/32/48px`.

---

## 고려한 대안

| 옵션 | 이유로 제외 |
|------|-----------|
| React + Vite | 빌드 파이프라인 필요. Python 단일 스택 위반. |
| Svelte (컴파일) | 마찬가지로 빌드 단계 필요. |
| HTMX만 (CSS 전환만) | 혁신 요구 미충족. backdrop-filter/Canvas 없이 Voice Glass·Constellation 불가. |
| Three.js | 번들 크기 600KB+. CDN 무거움. Canvas 2D로 Constellation 충분. |
| Framer Motion (React) | React 종속. Alpine.js + WAAPI 조합으로 동일 효과 달성. |

---

## 결과

- **V1.0**: htmx + Alpine.js + Tailwind CDN + WAAPI + View Transitions + CSS Glass
- **V1.1**: Voice Glass 완성 (Canvas 2D + Web Audio API) + WebGL 파티클 (선택)
- **V1.2**: Time Constellation Canvas 2D 완성
- 빌드 단계 없음 — Python http.server가 정적 파일 직접 서빙
- 브라우저 호환: Chromium 기반 (로컬 Windows 전용이므로 Edge/Chrome 고정 타깃)

### 근거

| 근거 유형 | 내용 |
|---------|------|
| 사용자 요구 | "혁신적·실험적·도전적" UI — iet03 2026-04-27 |
| 기술 제약 | Python 단일 스택, 빌드 파이프라인 없음 |
| 하드웨어 | iGPU(Intel Arc) Canvas/WebGL 가속 가능, NPU는 AI 전용 |
| 브라우저 환경 | 로컬 Windows = 최신 Chromium 고정 타깃 → 최신 CSS/API 자유롭게 사용 |
