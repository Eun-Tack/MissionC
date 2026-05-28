# MissionC Product Philosophy

MissionC is not just a task manager. It is a personal operating system for
keeping work, meaning, and evidence connected.

## Core Belief

A system should not contain meaningless structure.

Every concept in MissionC should earn its place. A table, screen, label,
automation, graph edge, shortcut, or document must help the user preserve
context, make better decisions, or maintain trust in the system.

## Product Thesis

Modern knowledge work breaks because context is scattered. A schedule lives in
one place, a memo in another, a project in another, and the reason behind a
decision disappears into chat, Git, or memory.

MissionC exists to turn those fragments into a coherent personal mission
control system.

## Craft Principles

| Principle | Meaning | Product Implication |
|-----------|---------|---------------------|
| Meaning before feature | A feature is valid only when it serves a clear concept. | Do not add screens or commands just because they are possible. |
| Context continuity | Work items should remember why they exist and where they belong. | Calendar, items, notes, projects, Git evidence, and reviews should connect. |
| Local trust | The user should feel ownership over their data and operating environment. | Prefer local storage, local diagnostics, explicit credentials, and visible sync state. |
| Honest automation | Automation should reduce work without pretending to be more reliable than it is. | Sync, cache, credentials, and AI actions must expose status and failure. |
| Flexible craft | Product concepts can evolve through use, but pivots must be traceable. | Use Semantic-Dev-Graph decisions for pivots and meaning changes. |
| Small surface, deep utility | A few well-connected workflows are better than many detached features. | Prioritize daily flow, calendar, organization graph, capture, and review before novelty. |

## Concept Model

MissionC should use a small set of concepts consistently.

| Concept | Definition | Notes |
|---------|------------|-------|
| Organization | The top-level affiliation context. This replaces the ambiguous Korean term "sosok" in current product language. | Examples: employer, client, institution, partner body. |
| Business | A program, initiative, or workstream under an organization. | Can be used when work needs a layer between organization and project. |
| Project | A concrete outcome-oriented unit of work. | A project may belong to a business or remain unassigned until clarified. |
| Item | A schedule, task, memo, or project reference. | Items are the atomic work surface. |
| Capture | A low-friction input before classification. | Quick capture, Telegram, and future voice input should land here safely. |
| Review | The place where unfinished work becomes learning. | Morning/evening review should feed future planning and quality factors. |
| Semantic Decision | A traceable statement connecting product meaning to implementation evidence. | Used for pivots, quality-factor changes, and major workflow choices. |
| Lab Feature | A visible but explicitly experimental capability. | Radial command palette belongs here until interaction safety is proven. |

## Naming Decision

MissionC is the product and repository name.

`MC` can remain in internal compatibility surfaces:

- `MC_*` environment variables,
- database filenames,
- historical migration comments,
- older phase evidence.

User-facing copy and new documentation should prefer MissionC.

## Organization Terminology

The Korean term previously written as "소속" means Organization in MissionC.

Product language should prefer:

- Korean: 조직
- English: Organization
- Avoid as primary UI term: 소속

Old documents may still contain "소속" as historical evidence. Current docs and
new UI copy should use 조직 unless the user explicitly wants the older term in a
specific place.

## Automation Direction

MissionC should move toward automatic background sync, but only with honest
state:

- cache-first rendering,
- visible last-sync time,
- visible failure state,
- manual refresh fallback,
- no blocking page loads,
- no silent credential failure.

This applies first to Google Calendar and GitHub. Telegram should not become
fully active until polling offset is persisted.

## Feature Lab Direction

Lab features are allowed when an idea is meaningful but not yet safe enough for
the default workflow.

Rules:

- Lab features must be behind a setting or explicit toggle.
- Lab features must not trap the user.
- Lab features must have a documented exit path: promote, redesign, or remove.
- Lab features should link to an issue or Semantic-Dev-Graph decision.

The radial command palette is the first MissionC lab feature.
