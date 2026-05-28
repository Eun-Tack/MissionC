---
project: MissionC
project_code: MISSIONC-001
legacy_name: MC Mission Control
cycle_version: v2.1.1-missionc
status: Draft
created_at: 2026-05-27
updated_at: 2026-05-28
framework: AI_SDLC_Standard v2.1.1
predecessor: Doc/phase7_release/Postmortem.md
backlog_input: Doc/phase6_review/Review_Summary.md
---

# MASTER_SPEC.md - MissionC

MissionC is the single source of truth for the product formerly called `MC`.
The repository folder may remain `schedule`, and compatibility names such as
`MC_*` environment variables may remain in code, but the product and repository
identity is MissionC.

## 0. Product Essence

### 0.1 Philosophy

MissionC is a local-first mission control system for a single knowledge worker.
It exists to prevent schedules, notes, projects, decisions, and integration
signals from becoming scattered fragments.

The guiding belief is simple: a system should not contain meaningless
structure. Every visible feature, hidden rule, document, and automation path
must be connected to a clear intention.

MissionC treats software as flexible craft. Its concepts may evolve through
real use, but pivots should be explicit, traceable, and grounded in evidence.

### 0.2 First Principles

| FP-ID | Principle | Statement | Source |
|-------|-----------|-----------|--------|
| FP-1 | Local-first | Personal work data should default to local SQLite, local files, and local control. | ADR-004 |
| FP-2 | One operator | Optimize for one recurring user before optimizing for teams or SaaS patterns. | Vision and Scope |
| FP-3 | Context continuity | Tasks, schedules, notes, projects, GitHub issues, and calendar events should form one connected context. | Phase 3 BA |
| FP-4 | Honest automation | Sync, cache, credential, and diagnostic states must be visible rather than silently failing. | Review Summary |
| FP-5 | RnD before AI promise | AI/NPU features must pass measurable local experiments before becoming product workflows. | RnD track |
| FP-6 | Meaningful structure | Product concepts, data models, and UI surfaces should carry intentional meaning, not decorative labels. | Owner interview |

### 0.3 Quality Factors

| F-ID | Factor | Definition | Primary Signals |
|------|--------|------------|-----------------|
| F-1 | Capture Reliability | Inputs should not be lost across quick capture, inbox, Telegram, or calendar flows. | capture success rate, duplicate rate |
| F-2 | Context Retrieval | A user should reach the relevant work context in one or two actions. | search latency, context-open latency |
| F-3 | Local Trust | Secrets and personal data should not leak into plaintext storage or unnecessary remote calls. | secret incidents, local-only coverage |
| F-4 | Operational Honesty | Sync, cache, DB, and credential states should be explainable from the UI or logs. | stale sync count, diagnostic coverage |
| F-5 | RnD Measurability | AI features need datasets, pass criteria, failure criteria, and rollback paths. | experiment pass rate, rollback rate |
| F-6 | Semantic Coherence | Product meaning, requirements, implementation, and Git evidence should remain connected. | semantic decision coverage |

## 1. Project Overview

MissionC is a FastAPI, SQLite, Jinja, and HTMX-based local application. It
manages daily work through items, projects, calendar views, hierarchy views,
capture inboxes, and integration setup.

Current implementation details are tracked in `Doc/IMPLEMENTATION_LEDGER.md`.
Repository ownership boundaries are tracked in `Doc/REPO_BOUNDARIES.md`.

### 1.1 Current State

| Area | Current State | Evidence |
|------|---------------|----------|
| Core API | FastAPI routers for items, calendar, inbox, hierarchy, setup, settings, and diagnostics. | `src/core_api/routers/*` |
| Data | SQLite schema and migration runner. | `migrate.py`, `Doc/phase4_design/schema/mc_schema.sql` |
| UI | Local web interface using Jinja templates and local frontend assets. | `src/core_api/templates/*`, `static/*` |
| Integrations | Google Calendar, GitHub, and Telegram paths exist, with credential handling and diagnostics. | `src/core_api/auth.py`, `src/core_api/integrations.py`, `src/core_api/setup.py` |
| QA | Pytest coverage for API, database, integration, and regression paths. | `tests/*` |
| RnD | Local AI search, voice capture, tagging, and sync hardening remain experimental. | `Doc/phase5_impl/*`, `Doc/phase6_review/*` |

### 1.2 Scope

| Scope | Item | Status |
|-------|------|--------|
| In | Local tasks, notes, schedules, projects, and hierarchy workflows. | Built |
| In | Google Calendar readonly sync and credential setup. | Built, needs UX hardening |
| In | GitHub issue cache and integration status. | Built, needs rate-limit handling |
| In | Telegram capture. | Built, needs offset persistence before active use |
| In | Semantic-Dev-Graph documentation and decision tracing. | Started |
| Out | Multi-user SaaS, mobile app, remote-first AI processing. | Future |

## 2. Requirement Catalog

| FR-ID | Feature | Intent | Priority | Status |
|-------|---------|--------|----------|--------|
| FR-CORE-01 | Item CRUD and status update | Stable creation, update, completion, and classification of work items. | Must | Built |
| FR-CAP-01 | Unified capture inbox | Triage quick, Telegram, and future voice inputs without losing data. | Must | Built |
| FR-CAL-01 | Local calendar view | Show local and cached Google Calendar events together. | Must | Built |
| FR-CAL-02 | Google Calendar OAuth sync | Import primary calendar data through Google OAuth. | Must | Built |
| FR-ORG-01 | Organization and project linkage | Let schedules/items connect to organization, business, and project context. | Must | Built, needs polish |
| FR-INT-01 | Integration health and credentials | Let the user test and understand credential state. | Must | Built |
| FR-OPS-01 | Diagnostics and retry visibility | Surface DB, cache, worker, credential, and sync state. | Must | Built |
| FR-RND-01 | Local semantic search experiment | Validate local embeddings/search before productizing. | Should | Draft |
| FR-RND-02 | Local voice capture experiment | Validate local STT accuracy and latency. | Should | Draft |
| FR-RND-03 | AI tag suggestion experiment | Validate whether local AI reduces manual classification cost. | Could | Draft |

## 3. Business Rules

| BR-ID | If | Then | Linked FR |
|-------|----|------|-----------|
| BR-SEC-01 | A token or refresh token must be stored | Store it in keyring or a secret bridge, not in plaintext project files. | FR-INT-01 |
| BR-CAP-01 | Capture processing fails | Preserve the source input and leave retryable evidence. | FR-CAP-01 |
| BR-CAL-01 | Google Calendar API fails | Show cached data where possible and record the failure state. | FR-CAL-02 |
| BR-RND-01 | An AI experiment fails pass criteria | Keep the manual/local workflow as the default path. | FR-RND-* |
| BR-SDG-01 | A feature changes product meaning or quality factors | Add or update a Semantic-Dev-Graph decision entry. | FR-OPS-01 |

## 4. Semantic-Dev-Graph Seed

Semantic-Dev-Graph connects product meaning to implementation evidence without
introducing a heavy graph database. MissionC will use markdown tables and front
matter first.

| SDG-ID | Type | Statement | Anchored On | Evidence | Status |
|--------|------|-----------|-------------|----------|--------|
| SDG-DEC-001 | Decision | MissionC remains local-first and single-operator before team/SaaS expansion. | FP-1, FP-2, F-3 | `Doc/MASTER_SPEC.md` | Active |
| SDG-DEC-002 | Decision | Product name becomes MissionC; `MC` remains only as compatibility shorthand. | FP-6, F-6 | `README.md`, `Doc/CLAUDE.md` | Active |
| SDG-DEC-003 | Decision | Palette UX issues are treated as a separate interaction-quality track before reactivation. | F-2, F-4 | GitHub issue backlog | Proposed |
| SDG-DEC-004 | Decision | AI features stay in RnD until measurable local experiments pass. | FP-5, F-5 | RnD docs and tests | Active |

## 5. Operations Catalog

| SLO-ID | Indicator | Target | Linked FR |
|--------|-----------|--------|-----------|
| SLO-01 | Core page P95 latency | Under 500ms locally | FR-CORE-01 |
| SLO-02 | Local search P95 latency | Under 300ms for FTS, under 800ms for future semantic search | FR-RND-01 |
| SLO-03 | Capture loss rate | Under 1% | FR-CAP-01 |
| SLO-04 | Secret plaintext incidents | 0 | FR-INT-01 |

| Severity | Definition | Example |
|----------|------------|---------|
| SEV1 | App cannot start or database is at risk. | migration failure, startup crash |
| SEV2 | Major workflow fails. | item update 422, Google token mismatch |
| SEV3 | A specific integration or UI area fails. | Telegram duplicate capture, stale sync |
| SEV4 | Documentation, wording, or minor UI mismatch. | misleading auto-refresh text |

## 6. Dependency Graph

| Source ID | Target Artifact | Sync Mode |
|-----------|-----------------|-----------|
| FP-1, F-3 | `src/core_api/auth.py`, `.gitignore`, credential setup docs | Watch |
| F-2 | hierarchy, search, calendar, command palette UX | Manual |
| FR-ORG-01 | item/calendar forms and project/business selectors | Manual |
| FR-RND-* | RnD experiment reports | Manual |
| BR-SDG-01 | semantic decision templates and PR review checklist | Manual |

## 7. Change Log

| Date | Change ID | Class | Description |
|------|-----------|-------|-------------|
| 2026-05-27 | CHG-MASTER-001 | Class B | Added AI_SDLC master specification for MC. |
| 2026-05-27 | CHG-RND-001 | Class B | Added local AI/search/voice/tag/sync hardening RnD track. |
| 2026-05-28 | CHG-MISSIONC-001 | Class B | Reframed MC as MissionC and aligned docs to AI_SDLC v2.1.1. |

## 8. Open Questions

| OQ-ID | Question | Impact | Status |
|-------|----------|--------|--------|
| OQ-RND-01 | What real notes/items should become the semantic search gold set? | High | Open |
| OQ-RND-02 | What WER and latency thresholds make voice capture useful enough? | Medium | Open |
| OQ-RND-03 | When should Google/GitHub sync move from on-demand to background scheduling? | Medium | Open |
| OQ-RND-04 | What exact persistence key/table should Telegram polling offset use? | High before Telegram launch | Open |
| OQ-SDG-01 | Which semantic decisions deserve first-class issue templates versus simple markdown rows? | Medium | Open |
