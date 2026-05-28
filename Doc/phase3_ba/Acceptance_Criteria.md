---
source: ../../MASTER_SPEC.md
source_ids: [FR-RND-01, FR-RND-02, FR-RND-03, FR-RND-04]
generated_at: 2026-05-27
master_version: v1.9-rnd
master_status: Draft
generator: ba-writer
editable: true
sync_mode: Auto
standard_compat: ai-friendly-doc-standard-v1.0
standard_path: 02_Product/Acceptance_Criteria.md
---

# Acceptance Criteria - MC Product and RnD

## 1. AC 통계

| 항목 | 수치 |
|------|------|
| 문서화된 RnD FR | 4 |
| 상세 AC 작성 완료 | 2 |
| 제품 승격 전 blocker OQ | 4 |
| 현재 자동 테스트 | 50 passed |

## 2. 우선순위 매트릭스

| 우선순위 | FR | 상태 | 다음 행동 |
|----------|----|------|-----------|
| Must | FR-CORE-01, FR-CAP-01, FR-CAL-01, FR-CAL-02, FR-INT-01, FR-OPS-01 | Built | regression 유지 |
| Should | FR-RND-01, FR-RND-02, FR-RND-04 | Draft | 실험 설계/측정 |
| Could | FR-RND-03 | Draft | 검색/음성 이후 착수 |

## 3. AC 요약

| AC ID | FR | 유형 | 요약 | 검증 |
|-------|----|------|------|------|
| AC-FR-RND-01-1 | FR-RND-01 | 정상 | gold set top-5 hit rate >= 80% | Pending |
| AC-FR-RND-01-2 | FR-RND-01 | 예외 | embedding index missing 시 FTS fallback | Pending |
| AC-FR-RND-01-3 | FR-RND-01 | 경계 | P95 > 800ms면 제품 승격 보류 | Pending |
| AC-FR-RND-02-1 | FR-RND-02 | 정상 | 짧은 음성이 inbox pending으로 저장 | Pending |
| AC-FR-RND-02-2 | FR-RND-02 | 예외 | 모델 없음 상태가 명확히 반환 | Pending |
| AC-FR-RND-02-3 | FR-RND-02 | 경계 | P95 > 3s면 제품 승격 보류 | Pending |

## 4. Product Regression AC

```gherkin
Scenario: Item status update works
  Given an item exists
  When PATCH /api/items/{id} is called with status=done
  Then the response status is 200
  And the item status is updated to done
```

```gherkin
Scenario: GCal credential state is consistent
  Given Google Calendar OAuth callback stores MC_GCAL_TOKEN
  When settings and diagnostics pages check credential state
  Then both pages read the same MC_GCAL_TOKEN key
```

```gherkin
Scenario: Recurring item completion does not violate DB constraints
  Given a recurring item exists
  When the item is completed
  Then the next item is inserted with a schema-valid source
  And recurrence_parent_id links back to the completed item
```

## 5. Phase 6 Validation Matrix

| 검증 항목 | 명령/방법 | 현재 결과 |
|-----------|-----------|-----------|
| API/DB smoke | `python -m pytest -q` with TMP/TEMP=`C:\tmp` | 50 passed |
| GCal key consistency | static grep for `MC_GOOGLE_OAUTH` in runtime paths | runtime paths clean |
| Recurrence source constraint | test or manual completion path | Pending dedicated test |
| Telegram duplicate handling | restart simulation | Pending before TG activation |

