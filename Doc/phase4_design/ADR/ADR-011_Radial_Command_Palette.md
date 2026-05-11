# ADR-011: Radial Command Palette UI 패러다임

> **상태**: Accepted | **결정일**: 2026-05-10
> **결정자**: iet03 (자가검증 결과 V1.5 시작점으로 확정)
> **연관**: V1.0 ADR-002 (UI 렌더링 전략) 의 Layer 3 (Motion / Spatial) 활용 + 신규 인터랙션 패러다임

---

## 1. 컨텍스트

V1.0 출시 후 자가 회고 (`Doc/phase7_release/Postmortem.md`) 결과, 사용자(iet03)는 다음을 명시적으로 요구:

1. "흔해빠진 방법 말고 실험적이고 도전적이고 혁신적" UI (V1.0 ADR-002 와 동일)
2. **실효성 있는** 혁신 — 데모용이 아닌 매일 사용 빈도 높은 패턴
3. V1.0 의 핵심 가치 (`스케줄·프로젝트·문서·생각이 한 컨텍스트 안에서 연결`) 강화

**핵심 긴장**: 일반적인 cmdk (검색박스 형태 — Linear, Raycast, Notion 모두 동일) 는 *검색* 만 가능하지만, 사용자는 검색 외에도 캡처/회고/회상/컨텍스트 진입 등 다양한 모드 진입을 1 단축키로 원함.

---

## 2. 고려된 대안

### A. 표준 cmdk (Linear/Notion 패턴)
- 검색박스 + 자동완성 결과 리스트
- ✅ 학습 곡선 거의 0
- ❌ 검색 외 액션이 모두 *키워드 입력 → 결과 클릭* 의 2단계
- ❌ 혁신성 0 (모든 도구가 동일)
- ❌ "캡처" 같은 즉시 입력 액션과 "어제 회고" 같은 모드 전환이 같은 박스에 섞임 → 인지 부담

### B. Stack-of-Cards (Raycast Extensions)
- 단축키 → 카테고리 카드 → 액션 카드 의 시퀀스
- ✅ 확장성 높음
- ❌ 진입 단계 ≥ 2 (사용자 의도와 반대 — V1.5 목표는 1 단계)
- ❌ 키보드 네비게이션이 선형 (방향성 없음)

### C. **Radial Menu (선택안)**
- 8 방향 방사형 메뉴 — 게임 (Witcher quick-cast) / Photoshop (brush picker) 패턴
- ✅ 1 키보드 입력 + 1 방향키 = 2 키 안에 모든 액션 도달
- ✅ 공간 메모리 활용 — 사용자 손가락 패턴이 슬라이스 위치에 매핑됨
- ✅ 혁신성 (생산성 도구 영역에 부재)
- ⚠️ 학습 곡선 — 첫 진입 onboarding 필요
- ⚠️ 슬라이스 수 제약 — 8개가 인지 한계 (그 이상은 hierarchy 필요)

### D. Floating Toolbar (Notion slash command)
- `/` 입력 시 인라인 메뉴
- ✅ 경량
- ❌ 입력 컨텍스트(텍스트 입력 중) 에서만 작동 — 페이지 전환에 부적합

---

## 3. 결정

**Radial Menu (대안 C) 채택**.

### 결정 근거

| 평가 축 | 가중치 | A: 표준 cmdk | B: Stack | **C: Radial** | D: Slash |
|---------|--------|--------------|----------|---------------|----------|
| 시스템 목적 부합 | 30% | 5/10 | 6/10 | **9/10** | 4/10 |
| 실효성 (일상 사용) | 30% | 8/10 | 6/10 | **9/10** | 5/10 |
| 혁신성 | 25% | 1/10 | 4/10 | **9/10** | 5/10 |
| 구현 난이도 | 15% | 9/10 (쉬움) | 7/10 | **6/10** | 8/10 |
| **가중 총점** | | 5.10 | 5.65 | **8.40** | 4.95 |

---

## 4. 구체화 결정 사항

### 4.1 슬라이스 수: **8 개 고정**

- 인지 부담 한계 = 7±2 (Miller's Law) → 8 개가 최대
- 향후 LLM 슬라이스(V2.0) 추가 시 9 번째가 아닌 **기존 슬라이스의 sub-action 형태로 통합**
- 슬라이스 사용자 정의는 V1.5 미포함 (커스터마이징 = 학습 비용)

### 4.2 시각 표현: **SVG 8 조각 + Glass Morphism**

ADR-002 의 Layer 2 (Glass / Material) + Layer 3 (Motion) 활용:
- SVG path 8 개로 각 조각 (Canvas 비채택 — 접근성 위해)
- `backdrop-filter: blur(20px)` 로 배경 흐림
- `Web Animations API` 로 spring 모션 — `keyframes` 보다 정밀한 제어
- 라이브러리 0 — 모든 기능 네이티브 브라우저 API

### 4.3 키보드 매핑: **3 중 진입**

```
Cmd+K    → radial 진입
↑↗→↘↓↙←↖  → 8 방향 슬라이스 강조 + Enter 실행
c/s/t/x/r/y/p/v → 각 슬라이스 즉시 실행 (강조 단계 생략)
Esc      → 닫기
```

3 중 진입은 학습 단계별 사용을 지원:
- 초보: 진입 후 화살표로 둘러보고 Enter
- 중급: 진입 후 단일 문자 즉시 실행
- 숙련: 단일 문자만으로 0.5초 내 액션 (radial 사실상 invisible)

### 4.4 슬라이스 액션 분리 원칙

- **Direct route 슬라이스**: 클릭 즉시 페이지 전환 (오늘/회고/프로젝트)
- **Inline form 슬라이스**: radial 안에서 input 또는 form 표시 (캡처/검색)
- **Modal escalate 슬라이스**: 별도 모달 호출 (음성/어제)
- **In-place expand 슬라이스**: 현재 페이지의 컴포넌트 토글 (컨텍스트 패널)

이 4 가지 패턴 분리로 구현 코드 일관성 확보.

### 4.5 컨텍스트 인지 (FR-RADIAL-03)

URL pattern 매칭 기반 단순 dispatch (V1.5):

```js
function getRadialContext() {
  const path = location.pathname;
  if (path.startsWith('/project/')) return {projectId: path.split('/')[2]};
  if (path === '/inbox') return {mode: 'inbox-mass'};
  if (path === '/morning' || path === '/evening') return {mode: 'review'};
  return {mode: 'default'};
}
```

V1.6 부터 LLM 추론으로 확장 검토.

---

## 5. 거절된 제안 (회의 시 검토됨)

| 제안 | 거절 사유 |
|------|-----------|
| 12 슬라이스 (시계) | Miller's Law 위반 — 인지 부담 |
| 슬라이스 사용자 정의 | V1.5 학습 곡선 가중. V2.0 검토 |
| 호버만으로 진입 (마우스 우선) | 키보드 우선 원칙 위반 |
| 마우스 제스처 (원 그리기) | 키보드 도달성 0% — 접근성 위반 |
| 슬라이스에 색상 차별화 | OKLCH brand-soft 통일성 깨짐 |

---

## 6. 결과 / 영향

### 긍정적
- 1 단축키로 모든 핵심 모드 진입 — 화면 전환 비용 사실상 0
- 후속 V1.6/V1.7/V2.0 의 진입점 확보 (Radial 이 척추가 됨)
- ADR-002 의 Layer 3 (Motion) 활용 사례 첫 실증

### 부정적
- 첫 진입 사용자에게 학습 필요 — onboarding tooltip 1 회 표시 필수
- SVG path 좌표 계산 코드 복잡도 (~150 line JS)

### 중립적
- 표준 cmdk 사용자가 처음 어색해 할 가능성 — *이것이 의도된 차별화*

---

## 7. 검증 계획

V1.5 종료 시점에 다음 측정:

| 항목 | 목표 | 미달 시 |
|------|------|--------|
| 진입 응답 | ≤ 100ms | Web Animations API 성능 점검 |
| 키보드 전용 도달성 | 100% | 슬라이스 라우팅 디버그 |
| 일 사용 빈도 | ≥ 20 회 | UX 재설계 (V1.6) |
| 사용자 만족도 (`[iet03]` 자가평가) | ≥ 4/5 | 슬라이스 구성 재검토 |

검증 미달 시 ADR-011 supersede 후 **표준 cmdk 로 fallback** (대안 A) — 사용자 의도가 우선이므로 패러다임 고수 X.

---

## 8. 관련 문서

- 상위 가치: V1.0 PRD `00_Vision_and_Scope.md`
- 시각 전략: ADR-002 (UI Rendering Strategy)
- 자가 검증: `Doc/phase7_release/Postmortem.md` § 7
- 구현 상세: `Doc/phase4_design/V1.5_Radial_Palette/Implementation_Guide.md`
