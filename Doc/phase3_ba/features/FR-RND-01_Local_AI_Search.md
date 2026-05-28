---
source: ../../../MASTER_SPEC.md
source_ids: [FR-RND-01, HYP-RND-01, SLO-02]
generated_at: 2026-05-27
master_version: v1.9-rnd
master_status: Draft
generator: ba-writer
editable: true
sync_mode: Auto
standard_compat: ai-friendly-doc-standard-v1.0
standard_path: 02_Product/features/FR-RND-01_Local_AI_Search.md
---

# FR-RND-01: Local Semantic Search Experiment

## 1. 기능 요약

로컬 메모, 할 일, 프로젝트 기록을 대상으로 임베딩 기반 의미 검색을 실험하고, 제품 기능으로 승격할 수 있는 품질과 성능 기준을 확인한다.

## 2. AS-IS / TO-BE

| 구분 | 내용 |
|------|------|
| AS-IS | FTS5 기반 키워드 검색은 동작하지만 표현이 다른 메모를 회수하기 어렵다. |
| TO-BE | 로컬 embedding index로 의미가 비슷한 결과를 top-5 안에 안정적으로 제시한다. |

## 3. 입력/출력

| 항목 | 내용 |
|------|------|
| Input | query text, item/memo corpus, optional filters |
| Output | ranked result list, score, matched source, fallback FTS result |

## 4. Business Rules

| Rule ID | IF | THEN |
|---------|----|------|
| BR-RND-SEARCH-01 | embedding index가 없거나 stale이면 | FTS5 검색으로 fallback한다. |
| BR-RND-SEARCH-02 | top result score가 threshold 미만이면 | “확실한 결과 없음” 상태를 표시한다. |
| BR-RND-SEARCH-03 | 모델 성능이 SLO를 넘으면 | 제품 기본 검색에 편입하지 않는다. |

## 5. Acceptance Criteria

```gherkin
Scenario: 의미가 같은 다른 표현을 찾는다
  Given 50개 이상의 gold query/result set이 준비되어 있다
  When 사용자가 의미 검색을 실행한다
  Then 정답 문서가 top-5 안에 포함되는 비율이 80% 이상이어야 한다
```

```gherkin
Scenario: embedding index가 없을 때 fallback한다
  Given embedding index 파일이 없거나 생성 중이다
  When 사용자가 검색을 실행한다
  Then FTS5 결과가 표시되고 오류로 중단되지 않아야 한다
```

```gherkin
Scenario: 성능 경계값을 초과하면 제품 승격을 보류한다
  Given semantic search P95 latency가 800ms를 초과한다
  When RnD 결과를 평가한다
  Then 기능 상태는 Draft 또는 Experiment로 남아야 한다
```

## 6. Test Cases

| TC-ID | 유형 | 입력 | 기대 결과 |
|-------|------|------|-----------|
| TC-RND-SEARCH-01 | 품질 | 50개 gold query | top-5 hit rate >= 80% |
| TC-RND-SEARCH-02 | 성능 | 100회 반복 검색 | P95 <= 800ms |
| TC-RND-SEARCH-03 | fallback | index missing | FTS5 result shown |

## 7. Open Questions

| OQ-ID | 질문 |
|-------|------|
| OQ-RND-SEARCH-01 | gold set을 실제 업무 데이터에서 어떻게 익명화/샘플링할 것인가? |
| OQ-RND-SEARCH-02 | KoE5 384차원과 bge-m3 계열 중 어떤 모델을 baseline으로 둘 것인가? |

