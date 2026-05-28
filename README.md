# MissionC

MissionC is a local-first mission control system for a single knowledge worker.
It is designed to help projects close, not merely be viewed. It connects
schedule, tasks, notes, projects, WBS, reviews, integrations, and operational
diagnostics into one reliable workspace.

The project was formerly developed under the short name `MC`. The internal
environment prefix may still use `MC_*` for compatibility, but the product,
repository, and documentation name is now MissionC.

## Philosophy

MissionC follows the AI_SDLC principle that a system should not contain
meaningless structure. Every screen, document, integration, and workflow should
serve a clear intention.

This project treats software as a flexible craft:

- Mission and implementation must stay connected.
- Projects should move toward explicit closing outcomes.
- Local trust is more important than feature spectacle.
- Automation should be honest about its state and failure modes.
- Product concepts may evolve through actual use, but every pivot should leave
  evidence.

The fuller philosophy and concept model are documented in
[Doc/PRODUCT_PHILOSOPHY.md](Doc/PRODUCT_PHILOSOPHY.md).

## AI_SDLC Alignment

MissionC is managed with the AI_SDLC framework located at:

```text
C:\Users\iet03\Documents\Hub\agents\AI_SDLC
```

The current project setup uses the AI_SDLC v2.1.1 model:

- Essence: product philosophy, first principles, and quality factors.
- Specification: requirements, rules, UI catalog, and operational contracts.
- Evidence: tests, issues, commits, release notes, and review results.
- Operation: diagnostics, incidents, sync status, and maintenance decisions.

Semantic-Dev-Graph is used as a lightweight bridge between product meaning and
Git evidence. It should remain markdown-first and small: only meaningful
decisions, pivots, quality-factor changes, and Class B/C/D changes need graph
entries.

## Current Scope

MissionC currently includes:

- FastAPI core API.
- SQLite local database and migrations.
- Jinja/HTMX-based local web interface.
- Local-first item, calendar, project, inbox, and hierarchy workflows.
- Google Calendar, GitHub, and Telegram integration paths.
- Diagnostics and credential setup screens.
- RnD track for local AI search, voice capture, and tagging.

## Run Locally

Install dependencies first:

```powershell
pip install -r requirements.txt
```

Start the local app:

```powershell
python .\run.py
```

Then open:

```text
http://127.0.0.1:8000
```

`run.py` runs migrations before starting the FastAPI server.

## Project Structure

```text
MissionC/
  Doc/
    MASTER_SPEC.md          # AI_SDLC master specification
    CLAUDE.md               # agent entrypoint and operating rules
    phase*/                 # AI_SDLC phase artifacts
  src/
    core_api/               # FastAPI application
  static/                   # local frontend assets
  tests/                    # pytest coverage
  migrate.py                # SQLite migration runner
  run.py                    # local development launcher
```

## Core Documents

- [Doc/MASTER_SPEC.md](Doc/MASTER_SPEC.md)
- [Doc/PRODUCT_PHILOSOPHY.md](Doc/PRODUCT_PHILOSOPHY.md)
- [Doc/CLOSING_GRAPH_REVIEW.md](Doc/CLOSING_GRAPH_REVIEW.md)
- [Doc/IMPLEMENTATION_LEDGER.md](Doc/IMPLEMENTATION_LEDGER.md)
- [Doc/REPO_BOUNDARIES.md](Doc/REPO_BOUNDARIES.md)
- [Doc/CLAUDE.md](Doc/CLAUDE.md)
- [Doc/phase6_review/Review_Summary.md](Doc/phase6_review/Review_Summary.md)
- [Doc/phase7_release/Postmortem.md](Doc/phase7_release/Postmortem.md)

## Repository Target

GitHub repository target:

```text
Eun-Tack/MissionC
```
