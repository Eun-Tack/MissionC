# MissionC Repository Boundaries

This document separates development documents, implementation code, runtime
data, and generated/local artifacts. The goal is to keep MissionC clear enough
that documents guide implementation without becoming mixed with runtime state.

## Boundary Model

| Layer | Purpose | Path | Rule |
|-------|---------|------|------|
| Framework reference | AI_SDLC standards, agents, ontology, Semantic-Dev-Graph concept | `C:\Users\iet03\Documents\Hub\agents\AI_SDLC` | Do not copy the whole framework into MissionC. Link only the parts MissionC uses. |
| Project development docs | Product meaning, requirements, design, reviews, release notes, implementation ledger | `Doc/` | Docs describe why and what. They do not store runtime state. |
| Agent entrypoints | Working rules for AI agents | `CLAUDE.md`, `Doc/CLAUDE.md` | Root file points inward; detailed rules live in `Doc/CLAUDE.md`. |
| Implementation code | Running application, routers, templates, static assets, tools | `src/`, `run.py`, `migrate.py`, `mc_tray.pyw`, `project_hub.py` | Code implements behavior. It should cite doc IDs when the decision is non-obvious. |
| Tests | Executable evidence | `tests/` | Tests prove behavior and regressions. They should map to ledger capabilities over time. |
| Runtime data | Local DB, logs, caches, secrets | `data/`, `.env`, keyring, `.whisper_cache/`, `*.log` | Never commit. Keep local-first. |
| GitHub operation | Issues, PR checks, semantic decisions | `.github/` | Use as lightweight operational scaffolding, not a second documentation system. |

## Development Documents

Development documents belong under `Doc/`.

Recommended roles:

| Document | Role |
|----------|------|
| `Doc/MASTER_SPEC.md` | Single source of product meaning and current specification. |
| `Doc/PRODUCT_PHILOSOPHY.md` | MissionC philosophy, concept model, terminology, and product judgment rules. |
| `Doc/IMPLEMENTATION_LEDGER.md` | Current implementation-to-data-to-test bridge. |
| `Doc/REPO_BOUNDARIES.md` | Repository ownership and separation rules. |
| `Doc/phase0_research/` | Research evidence. |
| `Doc/phase1_interview/` | User and scenario discovery. |
| `Doc/phase2_strategy/` | Strategic positioning and integration choices. |
| `Doc/phase3_ba/` | Requirements, rules, flows, acceptance criteria. |
| `Doc/phase4_design/` | Architecture, schema, API contracts, UI specs, ADRs. |
| `Doc/phase5_impl/` | Implementation summaries and task briefs. |
| `Doc/phase6_review/` | Review findings, test summaries, quality gates. |
| `Doc/phase7_release/` | Release notes, postmortems, issue records. |

## Implementation Code

Implementation code belongs outside `Doc/`.

| Area | Path | Notes |
|------|------|-------|
| App entrypoint | `src/core_api/main.py` | Router registration, auth guard, scheduler lifecycle. |
| Config and DB | `src/core_api/config.py`, `src/core_api/db.py`, `migrate.py` | Local SQLite and environment handling. |
| Routers | `src/core_api/routers/` | User-facing and API workflows. |
| Templates | `src/core_api/templates/` | Server-rendered UI. |
| Frontend assets | `src/core_api/static/` | Local JS/CSS, including vendor shim. |
| Tools | `src/tools/`, `src/secret_bridge/` | Local setup and secret helper paths. |
| Legacy/prototype launcher | `project_hub.py` | Keep only if still useful; otherwise mark legacy before removal. |

## Runtime Data

Runtime data must stay untracked.

| Artifact | Rule |
|----------|------|
| `.env`, `.env.local` | Secret-bearing local config; never commit. |
| `data/`, `*.db`, `*.sqlite` | Local database state; never commit. |
| `*.log` | Operational logs; never commit. |
| `.whisper_cache/` | Local model/cache state; never commit. |
| `.claude/` | Local assistant state; never commit. |

## Change Discipline

Use this split when deciding where work belongs:

- If it changes behavior, edit code and tests.
- If it changes product meaning, edit `Doc/MASTER_SPEC.md`.
- If it changes what is currently implemented, edit `Doc/IMPLEMENTATION_LEDGER.md`.
- If it changes data relationships, edit schema/migration and the data map.
- If it changes a long-term decision, add a Semantic-Dev-Graph entry or issue.
- If it is only runtime state, keep it out of Git.

## Cleanup Candidates

These are not deletions to perform blindly. They are candidates to review:

| Candidate | Reason | Proposed Action |
|-----------|--------|-----------------|
| `project_hub.py` | Appears to be an older Local Project Hub implementation. | Mark legacy or move to `archive/` after confirming it is unused. |
| Root `static/` | May belong to the older app while current app uses `src/core_api/static/`. | Compare references before removing or archiving. |
| Radial palette files | Implemented but currently unstable. | Keep as lab feature, gate behind a toggle, and track via issue #1. |
| Old phase docs with v1/v1.5 language | Useful history but can confuse current status. | Keep as historical evidence; use Master Spec and Ledger as current truth. |

## Naming Rule

Use MissionC for:

- README and GitHub repository,
- user-facing product language,
- current project docs,
- future issue/PR titles.

Keep `MC` only where changing it would create compatibility cost:

- `MC_*` environment variables,
- existing DB file names,
- legacy comments or migration history,
- old phase evidence.

## Terminology Rule

Current product language should use:

| Preferred Term | Meaning | Avoid as Primary New Copy |
|----------------|---------|---------------------------|
| Organization / 조직 | Top-level affiliation context | 소속 |
| Business / 사업 | Program or workstream under an organization | - |
| Project / 프로젝트 | Outcome-oriented unit of work | - |

Historical phase documents may keep the older term `소속`, but new copy should
prefer `조직` to reduce ambiguity.
