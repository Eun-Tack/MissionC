# PRD — AI / NPU 기능

> 모듈: FR-AI-VOICE, FR-AI-SEARCH, FR-AI-TAG (V1.0) / FR-AI-SLOT (V1.1)
> 우선순위: Must (VOICE/SEARCH), Should (TAG)
> 작성: 2026-04-27 | BA Writer v1.0
> HW: Intel Core Ultra 7 355 + Intel NPU (AI Boost) + 32GB RAM

---

## FR-AI-VOICE: 음성 캡처 (Whisper NPU)

**한 줄**: 단축키 또는 버튼으로 음성 입력 → Whisper 변환 → Quick Capture 자동 입력(사용자 확인 후 저장). `[iet03]`
**비즈니스 가치**: 이동 중·손이 바쁠 때 입력 지원. 도구 전환 없이 캡처. `[iet03]`

### AS-IS → TO-BE

| 구분 | 내용 | 출처 |
|------|------|------|
| AS-IS | 음성 입력 → 다른 앱으로 이동 → 수동 텍스트 입력 | `[iet03]` |
| TO-BE | 단축키 → 발화 → 텍스트 미리보기 → Enter로 저장 | `[iet03]` |
| 변경 유형 | 신규(중) | |

### 처리 흐름

```
1. 단축키(글로벌) 또는 마이크 버튼 클릭
2. silero-vad 실시간 VAD 시작 (묵음 2초 → 자동 종료)
3. 수집된 음성 → Whisper Base ONNX (NPU) 변환
4. 결과 텍스트를 Quick Capture 입력란에 표시
5. confidence < 0.6이면 "다시 말하기" 버튼 추가 (BR-AI-06)
6. 사용자 확인(Enter) → 저장 (BR-AI-01 — 자동 저장 금지)
실패: "음성 인식에 실패했습니다. 텍스트로 입력해 주세요"
```

### Acceptance Criteria

```gherkin
Scenario: 정상 음성 캡처
  Given MC가 실행 중이다
  When  단축키를 누르고 "내일 오전 10시 병원 예약"을 발화한다
  Then  Quick Capture 입력란에 변환된 텍스트가 표시된다
  And   사용자가 Enter를 누를 때 저장된다 (자동 저장 X)

Scenario: 묵음 자동 종료
  Given 음성 입력 모드가 활성화되어 있다
  When  2초 이상 묵음이 지속된다
  Then  VAD가 자동으로 녹음을 종료하고 변환을 시작한다

Scenario: 낮은 신뢰도 결과
  Given Whisper 변환 결과의 confidence가 0.55다
  When  결과가 표시된다
  Then  결과 텍스트와 함께 "다시 말하기" 버튼이 표시된다

Scenario: 모델 미로드 상태 첫 호출
  Given 앱 첫 실행으로 Whisper 모델이 아직 로드 중이다
  When  음성 입력 단축키를 누른다
  Then  "모델 로딩 중... ({진행률}%)" 메시지 + 로드 완료 후 자동 시작
```

### 테스트 케이스

| TC-ID | 연결 AC | 시나리오 | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|---------|------|---------|
| TC-VOICE-01 | AC-1 | 정상 캡처 | 텍스트 QC에 표시, 사용자 확인 후 저장 | E2E | P0 |
| TC-VOICE-02 | AC-2 | 묵음 자동 종료 | 2초 후 변환 시작 | 통합 | P1 |
| TC-VOICE-03 | AC-3 | 낮은 신뢰도 | 재시도 버튼 표시 | 통합 | P1 |
| TC-VOICE-04 | AC-4 | 모델 로딩 중 | 진행률 메시지 + 완료 후 활성 | E2E | P1 |
| TC-VOICE-05 | — | 응답 시간 | 10초 이내 발화(~5단어) | ≤ 3초 변환 완료 | 성능 | P1 |

### NFR

| 항목 | 값 | 출처 |
|------|---|------|
| 변환 응답 (10초 발화) | ≤ 3초 | `[추론 — Whisper Base NPU 벤치마크]` |
| 모델 메모리 | ~150MB (Whisper Base) | `[추론]` |
| 외부 송신 | 0 (BR-AUTH-03a) | `[iet03]` |

---

## FR-AI-SEARCH: 로컬 의미 검색 (BGE-small NPU)

**한 줄**: 텍스트 임베딩 + sqlite-vec 벡터 검색으로 의미 기반 유사 항목을 찾는다. FTS5가 fallback. `[iet03]`
**비즈니스 가치**: "다른 표현으로 쓴 메모"도 찾아냄. 기존 FTS(단어 일치)의 핵심 한계 돌파. `[iet03]`

### AS-IS → TO-BE

| 구분 | 내용 | 출처 |
|------|------|------|
| AS-IS | 단어 일치 검색 — 표현 다르면 못 찾음 | `[iet03]` |
| TO-BE | 의미 검색 디폴트 — 뜻이 같은 표현도 검색됨. 데이터 30개 미만이면 FTS만. | `[iet03]` |
| 변경 유형 | 신규(대) | |

### 처리 흐름

```
1. 검색 쿼리 입력
2. 인덱스 항목 수 확인
   ├─ 30개 미만: FTS5 키워드 검색만 실행
   └─ 30개 이상: BGE-small NPU 임베딩 생성 → sqlite-vec 코사인 유사도 검색
3. 결과 0건: FTS5 fallback 자동 실행 (BR-AI-04)
4. 결과 표시 (≤ 200ms 목표)
```

### Acceptance Criteria

```gherkin
Scenario: 의미 검색 기본 동작
  Given 인덱스에 항목이 30개 이상이다
  When  "회의 준비"를 검색한다
  Then  "미팅 자료 작성" 등 유사 의미 항목도 결과에 포함된다
  And   200ms 이내에 결과가 표시된다

Scenario: 데이터 30개 미만 → FTS 전용
  Given 인덱스에 항목이 15개다
  When  검색 쿼리를 입력한다
  Then  FTS5 키워드 검색만 실행된다
  And   의미 검색 비활성 안내 "(항목 수 부족, 키워드 검색 중)" 메시지가 표시된다

Scenario: 의미 검색 결과 0건 → FTS fallback
  Given 의미 검색 결과가 0건이다
  When  시스템이 감지한다
  Then  FTS5 키워드 검색이 자동 실행된다
  And   "의미 검색 결과 없음 — 키워드로 재검색" 안내가 표시된다

Scenario: 신규 항목 즉시 인덱싱
  Given 새 메모 "NPU 벤치마크 결과"를 저장한다
  When  저장 후 "NPU 성능"으로 검색한다
  Then  신규 메모가 결과에 포함된다 (백그라운드 임베딩, BR-AI-02)
```

### 테스트 케이스

| TC-ID | 연결 AC | 시나리오 | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|---------|------|---------|
| TC-SEARCH-01 | AC-1 | 의미 검색 | 유사 표현 결과 포함 | E2E | P0 |
| TC-SEARCH-02 | AC-1 | 응답 시간 | ≤ 200ms (50개 항목 기준) | 성능 | P0 |
| TC-SEARCH-03 | AC-2 | 30개 미만 FTS | FTS만 실행, 안내 표시 | 통합 | P1 |
| TC-SEARCH-04 | AC-3 | fallback 자동 실행 | FTS fallback + 안내 | 통합 | P1 |
| TC-SEARCH-05 | AC-4 | 신규 항목 즉시 검색 | 저장 직후 검색 가능 | 통합 | P1 |

### NFR

| 항목 | 값 | 출처 |
|------|---|------|
| 의미 검색 응답 | ≤ 200ms (50개 항목 기준, P95) | `[iet03]` |
| 임베딩 크기 | 512차원 float32 | `[추론 — BGE-small 기본값]` |
| 모델 메모리 | ~120MB | `[추론]` |
| 외부 송신 | 0 (BR-AUTH-03a) | `[iet03]` |

---

## FR-AI-TAG: 태그 제안 + 자동 정규화 (임베딩 재사용)

**한 줄**: 새 항목 저장 시 의미 가까운 기존 항목의 태그를 제안 + 신규 태그 입력 시 기존 유사 태그(sim ≥ 0.85)로 정규화 제안. `[iet03]` (D2)

### 비즈니스 규칙 (v1.5 신규)

| BR-ID | IF | THEN | 출처 |
|-------|----|------|------|
| BR-AI-TAG-01 | 사용자가 신규 태그 입력 | KoE5 임베딩 후 기존 태그와 cosine sim ≥ 0.85인 것을 "기존 태그 제안"으로 표시 | `[iet03]` D2 |
| BR-AI-TAG-02 | 사용자가 "기존 태그 사용" 선택 | item_tags에 기존 tag_id 사용 (신규 tags row 생성 X) | `[iet03]` |
| BR-AI-TAG-03 | 사용자가 "그래도 신규" 선택 | tags 신규 row 생성. 머지 결정은 사용자 권한 | `[iet03]` |
| BR-AI-TAG-04 | 월 1회 위생 작업 | 사용 빈도 ≤1 + sim ≥ 0.9 태그쌍 → "병합 제안" 알림 | `[iet03]` D2 |

### Acceptance Criteria

```gherkin
Scenario: 태그 제안 표시
  Given 인덱스에 항목이 30개 이상이다
  When  새 메모 "iOS 앱 개발 계획"을 저장한다
  Then  "개발", "모바일" 등 관련 태그가 제안 칩으로 표시된다
  And   자동으로 적용되지 않는다 (BR-AI-01)

Scenario: 신규 태그 정규화 제안 (v1.5)
  Given 기존 태그 "NPU 개발"이 있다
  When  사용자가 새 태그 "NPU개발"을 입력한다
  Then  KoE5 임베딩 sim 0.92 → "기존 'NPU 개발' 사용?" 제안이 표시된다
  And   [기존 사용] [신규 생성] 2버튼이 제공된다 (BR-AI-TAG-01~03)

Scenario: 데이터 부족 시 비활성
  Given 인덱스에 항목이 20개다
  When  새 항목을 저장한다
  Then  태그 제안이 표시되지 않는다 (BR-AI-05)

Scenario: 제안 수락
  Given 태그 제안 "개발"이 표시된다
  When  "개발" 칩을 클릭한다
  Then  "개발" 태그가 항목에 추가된다

Scenario: 월 1회 머지 제안 (v1.5)
  Given 사용 빈도 1인 태그 "NPU연구"가 있고 "NPU 연구"(sim 0.93)도 존재한다
  When  월 1회 위생 작업이 실행된다
  Then  "NPU연구 → NPU 연구로 병합?" 알림이 노출된다 (사용자 결정)
```

### 테스트 케이스

| TC-ID | 연결 AC | 기대 결과 | 유형 | 우선순위 |
|-------|---------|---------|------|---------|
| TC-TAG-01 | AC-1 | 제안 칩 표시, 자동 적용 X | 통합 | P1 |
| TC-TAG-02 | AC-2 | 30개 미만 비활성 | 단위 | P1 |
| TC-TAG-03 | AC-3 | 수락 시 태그 추가 | E2E | P2 |

---

## FR-AI-SLOT: 자유 텍스트 → 구조화 추출 (V1.1, Phi-3 mini)

> **V1.1 항목 — V1.0에서 구현하지 않음.**

**한 줄**: 자유 텍스트 → `{time, title, tags, type}` JSON 단발 추출. 다중턴 X. `[iet03]`

### AS-IS → TO-BE

| 구분 | 내용 |
|------|------|
| AS-IS (V1.0) | 시간 패턴만 regex로 분류. 복잡한 자유 텍스트는 메모로 저장. |
| TO-BE (V1.1) | Phi-3 mini INT4가 자유 텍스트를 구조화된 슬롯으로 추출. 사용자 미리보기 후 확인. |

### Acceptance Criteria

```gherkin
Scenario: 슬롯 정상 추출 (V1.1)
  Given Phi-3 mini 모델이 로드되었다
  When  "다음 주 화요일 오후 2시에 김 팀장님 미팅, #업무 #회의" 입력한다
  Then  {time: "다음 주 화요일 14:00", title: "김 팀장님 미팅", tags: ["업무", "회의"], type: "schedule"} 미리보기가 표시된다
  And   사용자 확인 후 저장된다

Scenario: 추출 실패 fallback
  Given 슬롯 추출이 실패한다
  When  결과를 처리한다
  Then  원문이 그대로 메모로 저장된다 (BR-AI-07)
```

---

## Change Log

| 버전 | 날짜 | 변경 내용 | 변경자 |
|------|------|----------|--------|
| 1.0 | 2026-04-27 | 최초 작성 | BA Writer v1.0 |
