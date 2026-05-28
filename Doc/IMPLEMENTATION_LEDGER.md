# MissionC Implementation Ledger

This ledger connects the current implementation to AI_SDLC meaning, data, code,
tests, and known gaps. It is not a replacement for the phase documents. It is
the operational bridge between the documents and the running code.

## Purpose

MissionC now has enough implementation surface that the project needs a compact
truth table:

- what is actually implemented,
- which product meaning or requirement it serves,
- which data entities it depends on,
- which code owns it,
- which tests prove it,
- which holes still need owner confirmation.

## Implementation Map

| Capability | AI_SDLC Anchor | Data Entities | Code Owners | Evidence | Status |
|------------|----------------|---------------|-------------|----------|--------|
| Local app shell and auth guard | FP-1, FP-2, F-3 | `settings`, session cookie | `src/core_api/main.py`, `src/core_api/routers/auth.py` | `/health`, page smoke tests | Built |
| Initial setup and settings | FR-INT-01, F-4 | `settings`, `organizations`, `businesses`, `tags`, `labels` | `src/core_api/routers/setup.py`, `setup.html`, `settings.html` | settings page smoke, DB seed tests | Built |
| Items CRUD | FR-CORE-01, F-1 | `items`, `item_tags`, `item_labels`, `item_projects` | `src/core_api/routers/items.py`, `context_panel.html` | item API tests, DB CRUD tests | Built |
| Recurring item completion | FR-CORE-01, F-1 | `items.recurrence_rule`, `items.recurrence_parent_id`, `items.source` | `src/core_api/routers/items.py`, `migrate.py` | recurrence regression test | Built |
| Daily flow | FR-CORE-01, F-2 | `items`, `labels`, `item_labels`, `item_projects` | `src/core_api/routers/flow.py`, `index.html`, `flow_list.html` | page smoke tests | Built |
| Morning/evening closing review | FR-CLOSE-01, FP-9, F-8 | `items`, `incomplete_reasons`, `review_memos` | `src/core_api/routers/review.py`, `morning.html`, `evening.html` | page smoke tests, review route exists | Built, needs closing semantics |
| Project close summary | FR-CLOSE-02, SDG-DEC-009, FP-9, FP-10 | future close summary fields, future `project_outcomes` | future project detail and evening review flow | `Doc/CLOSING_OUTCOME_MODEL.md` | Planned |
| Calendar | FR-CAL-01, FR-CAL-02 | `items`, `gcal_cache`, `projects`, `businesses`, `organizations` | `src/core_api/routers/calendar.py`, `calendar.html` | calendar page smoke, org/project form smoke | Built, needs UX review |
| Organization/business/project hierarchy | FR-ORG-01, FP-3 | `organizations`, `businesses`, `projects`, `project_stages` | `src/core_api/routers/hierarchy.py`, `hierarchy.html`, `project.html` | hierarchy page smoke, FK tests | Built, needs copy/data polish |
| WBS closing map | FR-WBS-01, FR-ORG-01, FP-9, F-8 | `projects`, `project_stages`, `items`, `item_projects`, future blocker/review overlays | `src/core_api/routers/wbs.py`, `wbs.html` | page smoke missing | Built, needs closing semantics and tests |
| Capture inbox | FR-CAP-01, F-1 | `capture_inbox`, `items` | `src/core_api/routers/inbox.py`, `inbox.html` | inbox API tests | Built |
| Search and command search API | FR-RND-01, F-2 | `items_fts`, `items`, `projects` | `src/core_api/routers/search.py`, `search.html`, local HTMX shim | search tests | Built as FTS, semantic RnD not built |
| Contacts and attendees | FP-3, F-2 | `contacts`, `item_contacts` | `src/core_api/routers/contacts.py`, `contacts.html`, `attendees.html` | API test gap | Built, needs tests |
| Diagnostics and alerts | FR-OPS-01, F-4 | `settings`, `notification_events`, `retry_queue` | `src/core_api/routers/diagnostics.py`, `diagnostics.html`, `alerts.html` | diagnostics smoke | Built |
| Notifications due API | FR-OPS-01, F-4 | `notification_events`, `items` | `src/core_api/routers/notifications.py`, `base.html` | API test gap | Built, needs tests |
| Google Calendar auth and sync | FR-CAL-02, FR-INT-01, F-3, F-4 | `gcal_cache`, `settings`, keyring secret `MC_GCAL_TOKEN` | `src/core_api/routers/auth.py`, `src/core_api/setup.py`, `src/core_api/integrations.py` | token key regression covered indirectly | Built, needs live OAuth verification |
| GitHub sync | FR-INT-01, F-4 | `github_cache`, `settings`, keyring secret | `src/core_api/integrations.py`, diagnostics/setup screens | test gap | Partially built |
| Telegram polling | FR-CAP-01, F-1 | `capture_inbox`, in-memory `_tg_offset` | `src/core_api/integrations.py` | test gap | Built but deferred |
| Voice capture | FR-RND-02, F-5 | uploaded audio only, future `capture_inbox` link | `src/core_api/routers/voice.py` | voice status smoke | Experimental |
| AI suggestion | FR-RND-03, F-5 | `items`, `tags`, `projects` | `src/core_api/routers/ai_suggest.py` | test gap | Lightweight heuristic |
| Radial command palette | SDG-DEC-003, FR-LAB-01, F-7 | command state in browser, future lab toggle setting | `radial.js`, `radial.css`, `radial_palette.html` | GitHub issue #1 | Lab feature planned |
| Background sync | SDG-DEC-006, FR-SYNC-01, F-4 | `settings`, `gcal_cache`, `github_cache`, future sync state/cursor | `src/core_api/main.py`, `src/core_api/integrations.py`, diagnostics/settings UI | design pending | Planned |
| Outcome graph | SDG-DEC-008, FR-OUTCOME-01, FP-10, F-9 | future `project_outcomes`, `outcome_evidence`, `outcome_impacts`, `project_links` | future project close flow, project detail, WBS overlays | `Doc/OUTCOME_GRAPH.md`, `Doc/CLOSING_OUTCOME_MODEL.md` | Planned |

## Data Connection Map

| Data Area | Tables / Stores | Primary Owners | Connected Capabilities |
|-----------|-----------------|----------------|------------------------|
| Work items | `items`, `items_fts`, triggers | `items.py`, `flow.py`, `calendar.py`, `search.py` | CRUD, flow, calendar, search, recurrence |
| Classification | `tags`, `item_tags`, `labels`, `item_labels` | `items.py`, `setup.py` | tagging, labels, filtering, AI suggestions |
| Organization graph | `organizations`, `businesses`, `projects`, `project_stages`, `item_projects` | `hierarchy.py`, `wbs.py`, `calendar.py`, `items.py` | hierarchy, project detail, WBS, calendar association |
| Capture | `capture_inbox` | `inbox.py`, `integrations.py` | quick capture, Telegram, future voice capture |
| Integrations | `github_cache`, `gcal_cache`, keyring secrets | `integrations.py`, `auth.py`, `setup.py` | GitHub, Google Calendar, diagnostics |
| Operations | `notification_events`, `retry_queue`, `settings` | `diagnostics.py`, `notifications.py`, `setup.py` | alerts, retry visibility, setup, health |
| Review | `incomplete_reasons`, `review_memos` | `review.py` | morning/evening review |
| Closing loop | `items.status`, `items.due_date`, `incomplete_reasons`, `review_memos`, `project_stages`, `item_projects` | `review.py`, `wbs.py`, `items.py`, `flow.py` | daily closing, carry-over, blockers, WBS completion path |
| Close summary | future close summary fields and outcome seed records | future project detail, evening review | closing decision, outcome summary, evidence, lesson, next action |
| Outcome graph | future `project_outcomes`, `outcome_evidence`, `outcome_impacts`, `project_links` | future close summary, WBS, project detail | closed project results, reusable assets, lessons, cross-project links |
| Files | `file_index`, local notes folders | `hierarchy.py`, `integrations.py` | folder open, project folder creation |

## Evidence Coverage

| Evidence Type | Current Coverage | Missing / Weak Coverage |
|---------------|------------------|--------------------------|
| DB schema tests | required tables, settings seed, labels, FTS, FK cascade | migration fixture version alignment |
| API tests | health, items, recurrence, tags, labels, inbox, search, export, page smoke | contacts, WBS, notifications, GitHub/GCal/TG failure paths |
| UI smoke | major pages return 200 | keyboard interaction, modal close, palette behavior |
| Live integration tests | not automated | Google OAuth, GitHub token, Telegram polling |
| Semantic evidence | README, master spec, issue #1 | issue/PR discipline must be used consistently |

## Current Holes

| Hole ID | Area | Observation | Owner Question |
|---------|------|-------------|----------------|
| HOLE-001 | Product naming | Code still uses `MC` in title, env vars, DB names, comments. | Resolved: keep `MC_*` and legacy internals for compatibility; use MissionC in product/docs. |
| HOLE-002 | Organization terminology | User used "소속" to mean organization, creating possible ambiguity. | Resolved: current product language should use 조직/Organization. Historical docs may keep 소속. |
| HOLE-003 | Palette | Palette is implemented but user-reported behavior makes it unsafe to keep global. | Resolved direction: keep it as a lab feature toggle, not a default workflow. |
| HOLE-004 | Sync scheduler | Settings include poll intervals, while local architecture uses on-demand sync except inbox expiry. | Resolved direction: move toward background sync with visible state and manual fallback. |
| HOLE-005 | Telegram offset | `_tg_offset` is in memory, so restart can duplicate messages. | Should we persist it in `settings`, or create a dedicated integration cursor table? |
| HOLE-006 | Tests | Current tests cover core flows but not several newer routers. | Deferred: first refine philosophy and concept model before choosing test priority. |
| HOLE-007 | RnD AI | AI search/voice/tagging are partially represented but not product-grade. | Should these remain explicitly RnD, or should one be promoted into the next product cycle? |
| HOLE-008 | Closing model | Morning/evening review and WBS exist, but they are not yet unified as a project closing system. | First design pass complete in `Doc/CLOSING_OUTCOME_MODEL.md`; next step is close summary UI/data implementation. |
| HOLE-009 | Outcome continuity | Closed projects do not yet leave reusable outcome nodes or typed links to open projects. | Start with a lightweight close summary before adding tables or accounting integration. |

## Maintenance Rule

When code changes behavior, update this ledger if the change affects:

- a user-facing workflow,
- a table or data relationship,
- integration credentials or sync behavior,
- a quality factor,
- a Semantic-Dev-Graph decision,
- test coverage expectations.
