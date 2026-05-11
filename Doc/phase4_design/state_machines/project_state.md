# 프로젝트 상태 머신

> ADR-004 데이터 레이어 참조 | projects.status 필드

```
              ┌───────────┐
  [생성]─────►│  active   │◄──── [복원/재활성화]
              └──┬──┬─────┘
                 │  │
          일시중지│  │완료
                 │  │
          ┌──────▼─┐│ ┌───────────┐
          │ paused ││ │ completed │
          └──┬─────┘│ └─────┬─────┘
             │      │       │
        재개  │      │       │ 아카이브
             │      │       │
             └──────►       ▼
                      ┌──────────┐
                      │ archived │  ── (V1.2 Cold 티어 진입 가능)
                      └──────────┘
```

## 전환 규칙

| From | To | 트리거 | 효과 |
|------|----|--------|------|
| active | paused | 사용자 클릭 "일시중지" (BR-PROJ-03) | Today's Flow에서 프로젝트 항목 숨김 |
| active | completed | 사용자 클릭 "완료" | 프로젝트 색상 dim처리 |
| paused | active | 사용자 클릭 "재개" | Today's Flow 복귀 |
| completed | archived | 사용자 클릭 "아카이브" | V1.2: Cold 티어 이동 가능 |
| archived | active | 사용자 클릭 "재활성화" | V1.2: Cold→Hot 복원 포함 |

## 프로젝트 ⊂ 태그 관계 (BR-PROJ-02)

```
tags 테이블
  id=42, name="MC", color_hue=255

projects 테이블
  id=1, tag_id=42, title="Mission Control", status="active"
```

프로젝트를 생성하면 동일 이름 태그가 자동 생성된다. 태그로 항목을 연결하면 자동으로 프로젝트에도 연결된다. 프로젝트 삭제 시 태그는 유지(항목 연결 보존).

## 프로젝트 강등/복원 (BR-PROJ-03)

```python
def demote_project(project_id: int):
    # paused로 전환 — 태그와 연결은 유지
    db.execute("UPDATE projects SET status='paused' WHERE id=?", (project_id,))

def reinstate_project(project_id: int):
    db.execute("UPDATE projects SET status='active' WHERE id=?", (project_id,))
```
