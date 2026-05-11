# 태스크 상태 머신

> ADR-004 데이터 레이어 참조 | items.status 필드

```
                    ┌─────────────────────────────────┐
                    │                                 │
              ┌─────▼──────┐                          │
  [생성]─────►│    todo    │◄──────── [이월/복원]      │
              └─────┬──────┘                          │
                    │                                 │
              사용자가 "시작"                           │
                    │                                 │
              ┌─────▼──────┐                          │
              │   doing    │                          │
              └──┬──┬──────┘                          │
                 │  │                                 │
         완료    │  │   대기 발생                      │
                 │  │                                 │
          ┌──────▼─┐│ ┌──────────┐                   │
          │  done  ││ │ waiting  │──── 조건 해제 ─────►│
          └────────┘│ └──────────┘   (todo로 복귀)
                    │
              사용자가 "취소"
                    │
              ┌─────▼──────┐
              │ cancelled  │
              └────────────┘
```

## 전환 규칙

| From | To | 트리거 | 조건 |
|------|----|--------|------|
| todo | doing | 사용자 클릭 "시작" | — |
| todo | cancelled | 사용자 클릭 "취소" | — |
| doing | done | 사용자 클릭 "완료" | — |
| doing | waiting | 사용자 클릭 "대기" | — |
| doing | cancelled | 사용자 클릭 "취소" | — |
| waiting | todo | 사용자 클릭 "재개" | — |
| done | todo | 이월(BR-DAY-02) | Evening Review에서 내일로 이동 |
| cancelled | todo | 사용자 클릭 "복원" | — |

## Evening Review 이월 동작 (BR-DAY-02)

```python
# 이월 시 새 items 레코드를 만들지 않고 기존 레코드 status 변경
# item.id는 유지됨 — 이력 추적 가능
def carry_over(item_id: int, new_date: date):
    db.execute("""
        UPDATE items SET
            status = 'todo',
            scheduled_at = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_date.isoformat(), item_id))
```

## UI 상태 색상 (ADR-002 디자인 시스템)

| status | 색상 토큰 | OKLCH |
|--------|---------|-------|
| todo | `--text-lo` | oklch(55% 0.008 265) |
| doing | `--accent` | oklch(72% 0.18 255) |
| waiting | `--warn` | oklch(75% 0.18 50) |
| done | `--positive` | oklch(72% 0.16 155) |
| cancelled | `--text-lo` strikethrough | — |
