# CLAUDE.md - MissionC Project Entrypoint

This file is the working entrypoint for AI agents operating inside MissionC.
The framework reference is:

```text
C:\Users\iet03\Documents\Hub\agents\AI_SDLC
```

## Project Identity

| Item | Value |
|------|-------|
| Product name | MissionC |
| Legacy shorthand | MC |
| Project code | MISSIONC-001 |
| Local path | `C:\Users\iet03\Documents\Hub\agents\schedule` |
| Framework | AI_SDLC_Standard v2.1.1 |
| Master spec | `Doc/MASTER_SPEC.md` |
| Current implementation | FastAPI + SQLite + Jinja/HTMX local app |

Compatibility note: existing code may keep `MC_*` environment variables,
database names, and internal labels until changing them is worth the migration
cost. User-facing product language should prefer MissionC.

## Product Philosophy

MissionC is a local-first mission control system for one knowledge worker.
It should keep schedules, projects, notes, decisions, and integration signals
inside one reliable operating context.

The central principle is:

> A system should not contain meaningless structure.

Every feature should be connected to product essence, first principles, quality
factors, requirements, or operational evidence. MissionC is craft, not a pile of
detached features.

## Agent Operating Rules

- Read `Doc/MASTER_SPEC.md` before making product-level changes.
- Preserve local-first behavior unless the user explicitly approves otherwise.
- Do not store secrets in plaintext project files.
- Keep UI behavior honest: if sync, cache, credentials, or automation fail, show
  recoverable state rather than silent success.
- For Class B/C/D changes, update docs and tests together with code.
- For changes that affect product meaning, quality factors, or major user flows,
  add or update a Semantic-Dev-Graph decision entry.
- Keep command palette work isolated until close/keyboard behavior is stable.
- Treat `MC` as a compatibility shorthand and `MissionC` as the product name.

## AI_SDLC Phase Paths

| Phase | Purpose | Path |
|-------|---------|------|
| Phase 0 | Research | `Doc/phase0_research/` |
| Phase 1 | Interview | `Doc/phase1_interview/` |
| Phase 2 | Strategy | `Doc/phase2_strategy/` |
| Phase 3 | BA / requirements | `Doc/phase3_ba/` |
| Phase 4 | Design | `Doc/phase4_design/` |
| Phase 5 | Implementation | `Doc/phase5_impl/` |
| Phase 6 | Review | `Doc/phase6_review/` |
| Phase 7 | Release | `Doc/phase7_release/` |

## Useful Local Commands

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the app:

```powershell
python .\run.py
```

Run tests:

```powershell
pytest
```

Check Git state:

```powershell
git status -sb
```

## Semantic-Dev-Graph Rules

Semantic-Dev-Graph should stay lightweight.

Use it for:

- product meaning changes,
- quality-factor changes,
- pivots from user feedback,
- major interaction decisions,
- implementation choices with long-term maintenance impact.

Do not use it for every small commit. A label without operational effect is not
enough; each semantic entry should connect at least one meaning layer to one
implementation or evidence layer.

Minimum fields:

| Field | Meaning |
|-------|---------|
| SDG-ID | Stable semantic decision ID |
| Type | Decision, Pivot, QualityFactor, Evidence, or Risk |
| Statement | What changed or what was decided |
| Anchored On | First principle, quality factor, requirement, or issue |
| Evidence | Commit, test, issue, doc, or release artifact |
| Status | Proposed, Active, Superseded, or Rejected |

## Current Watch Items

| Item | Reason |
|------|--------|
| Command palette | Keyboard close and feature behavior were unstable; keep disabled or isolated until fixed. |
| Google Calendar auth | OAuth and local credential handling must remain consistent and diagnosable. |
| Organization/project linkage | Schedules and items should carry organization, business, and project context. |
| Telegram offset | Must be persisted before Telegram polling becomes active. |
| AI RnD | Local AI features need measurable experiments before product workflows. |

## Change Log

| Date | Change |
|------|--------|
| 2026-05-28 | Reframed project as MissionC and aligned agent entrypoint with AI_SDLC v2.1.1. |
