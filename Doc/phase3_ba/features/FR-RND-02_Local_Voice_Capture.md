---
source: ../../../MASTER_SPEC.md
source_ids: [FR-RND-02, HYP-RND-02]
generated_at: 2026-05-27
master_version: v1.9-rnd
master_status: Draft
generator: ba-writer
editable: true
sync_mode: Auto
standard_compat: ai-friendly-doc-standard-v1.0
standard_path: 02_Product/features/FR-RND-02_Local_Voice_Capture.md
---

# FR-RND-02: Local Voice Capture Experiment

## 1. 기능 요약

로컬 STT로 빠른 음성 메모를 capture inbox에 넣는 실험이다. 목표는 “말한 내용을 완벽히 받아쓰기”가 아니라, 업무 capture로 쓸 수 있는 충분한 정확도와 낮은 지연 시간을 확인하는 것이다.

## 2. Business Rules

| Rule ID | IF | THEN |
|---------|----|------|
| BR-RND-VOICE-01 | confidence가 기준 미만이면 | inbox에 “검토 필요” 라벨로 저장한다. |
| BR-RND-VOICE-02 | STT 모델이 로드되지 않았으면 | 음성 버튼은 disabled 또는 fallback 안내 상태가 된다. |
| BR-RND-VOICE-03 | 음성 처리 결과가 비어 있으면 | item을 생성하지 않고 오류/empty 상태를 보여준다. |

## 3. Acceptance Criteria

```gherkin
Scenario: 짧은 음성 메모가 inbox에 저장된다
  Given 로컬 STT 모델이 로드되어 있다
  When 사용자가 10초 이하 음성을 녹음한다
  Then capture_inbox에 transcript가 pending 상태로 저장된다
```

```gherkin
Scenario: 모델이 없으면 명확히 비활성화된다
  Given STT 모델 파일이 없다
  When 사용자가 voice status를 조회한다
  Then available=false와 model 상태가 반환된다
```

```gherkin
Scenario: 지연 시간이 기준을 넘으면 제품 승격을 보류한다
  Given 30개 음성 샘플을 처리했다
  When P95 처리 시간이 3초를 초과한다
  Then RnD 결과는 fail 또는 needs-optimization으로 기록된다
```

## 4. Test Cases

| TC-ID | 유형 | 입력 | 기대 결과 |
|-------|------|------|-----------|
| TC-RND-VOICE-01 | 통합 | 10초 wav sample | inbox pending row |
| TC-RND-VOICE-02 | 상태 | model missing | available=false |
| TC-RND-VOICE-03 | 성능 | 30개 sample | P95 <= 3s |

