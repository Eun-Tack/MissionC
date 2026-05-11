# Phase 6 Review Summary — MC V1.0
Date: 2026-05-08  
Reviewer: Claude (AI_SDLC v1.0 Phase 6 protocol)  
Gate result: **CONDITIONAL PASS** — P0 bugs fixed, P1 backlog created

---

## Gate Metrics

| Metric | Target | Actual |
|---|---|---|
| AC Pass Rate | ≥ 95% | ~91% (P1 items pending) |
| P0 Bugs | 0 | 0 (**fixed this session**) |
| P1 Bugs open | 0 | 5 (backlog) |

---

## P0 Bugs — Fixed

### B-001 · XSS in Search Snippet (Phase 4 origin)
- **File:** `search_results.html:12`, `search.py`
- **Issue:** FTS5 `snippet()` output marked `| safe` without sanitization. Malicious HTML in item titles rendered in search results.
- **Fix:** Added `_safe_snippet()` in `search.py` — `html.escape()` then restore only `<mark>`/`</mark>`. Snippet is sanitized before template; `| safe` retained for `<mark>` highlighting.

### B-002 · XSS in Items f-string HTML (Phase 4 origin)
- **File:** `items.py:129`, `items.py:255`
- **Issue:** User-controlled `title` inserted raw into f-string HTML fragments returned by `POST /api/items` and `PATCH /api/items/{id}` (recurrence spawn).
- **Fix:** Added `from html import escape`; wrapped both occurrences with `escape()`.

---

## P1 Bugs — Backlog

| ID | Location | Issue |
|---|---|---|
| B-003 | `items.py` POST/PATCH | No title length validation (≤10,000 chars) |
| B-004 | `integrations.py` | No 14-day inbox expiry for stale captures |
| B-005 | `setup.py` `settings_add_org()` | Org creation does not auto-create `MC-Notes/{name}/` folder |
| B-006 | `hierarchy.py` project delete | Does not clean up `item_projects` rows (BR-PROJ-03) |
| B-007 | export endpoint | Missing `Content-Disposition` header with timestamp filename |

---

## P2 Warnings — Accepted for V1

| ID | Issue |
|---|---|
| W-001 | Reschedule / split actions in context panel are stubs |
| W-002 | N+1 query pattern in flow page item list |
| W-003 | Evening review `category` radio has no `required` attribute |

---

## Feature Gaps vs FR (not bugs)

- GitHub rate-limit header not checked in `sync_github()` — degrades silently at API limit
- Calendar month view caps items at 3 per cell with no drill-down

---

## Phase Origin Analysis

| Phase | Bugs introduced |
|---|---|
| Phase 2 (DB schema) | B-006 (missing cascade) |
| Phase 4 (API / templates) | B-001, B-002, B-007 |
| Phase 5 (integrations) | B-004 |
| Phase 3 (setup) | B-005 |

---

## Next: V1.0 Completion Checklist

- [ ] B-003 title validation
- [ ] B-004 inbox expiry cron
- [ ] B-005 org folder auto-create
- [ ] B-006 project cascade cleanup
- [ ] B-007 export Content-Disposition
- [ ] Server smoke-test after restart
- [ ] Tag V1.0 release
