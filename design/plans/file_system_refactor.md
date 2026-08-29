---
title: File System Refactor Plan
status: live
part_of: agentic-sdlc
doc_type: reference
---

# File System Refactor Plan

## Goal Description
The objective is to establish a solid foundation for the repository's future growth as a modular Python package while deeply honoring its current focus on structural design and planning. 

Based on our alignment, this involves two major steps:
1. Creating an `AGENTS.md` file to act as the primary operational instruction manual (the "README for AI") for all coding assistants operating in this repository.
2. Refactoring the file system into a structured Python layout (`src/`), a formalized design sandbox (`design/`), and a finalized documentation hub (`docs/`), alongside foundational community files.

---

## Proposed Changes

### 1. New Repository Root Files
These files establish governance for both humans and AI agents.

#### [NEW] `AGENTS.md`
A concise operational index specifically targeted at AI agents.
* **Manifest Protection:** Explicitly forbids agents from modifying `AGENTIC_ARCHITECTURE_MANIFEST.md` and `FRONTMATTER_MANIFEST.md` unless explicitly instructed.
* **Manual Pre-commit Hooks:** Instructs agents to manually execute the Python validation scripts in `scripts/` (e.g., `check_agent_cards.py`, `check_frontmatter.py`) before committing any changes to the `design/` folder, since CI/Git hooks are not yet wired.
* **Changelog Process:** Dictates the strict append-only rule for `CHANGELOG.md` upon every PR/commit.
* **Delegation:** Instructs Claude models to cross-reference `CLAUDE.md`.

#### [NEW] `README.md`
The human-facing entry point.
* Summarizes the Agentic SDLC Orchestration mission.
* Outlines the file system structure (`src/` vs `design/` vs `docs/`).
* Explains that the project is currently in the structural design phase.

#### [NEW] `CONTRIBUTING.md`
Human contribution guidelines.
* Explains the strict delineation between brainstorming in `design/` and documenting finalized reality in `docs/`.

#### [NEW] `CHANGELOG.md`
An initialized changelog.
* Includes a header defining the outstanding process: *Changes must be appended only. Never delete or replace historical entries. This process will be formalized in CI in the future.*

---

### 2. File System Refactor: The `design/` Staging Ground
All current planning documents and audits will be relocated here to serve as the conceptual brainstorming and drafting area. The Python contracts (`contracts/*.py`) will also remain here until they are actively implemented in the executable codebase.

#### [MODIFY] `design/plans/` -> `design/plans/`
The entire `design/plans/` directory (including `contracts/`, `optimization/`, `agents/`, etc.) will be moved to `design/plans/`.

#### [MODIFY] `design/audits/` -> `design/audits/`
The entire `design/audits/` directory will be moved to `design/audits/`.

---

### 3. File System Refactor: The `src/` Codebase
We will initialize the modular Python structure. Per our alignment, these directories will serve as empty scaffolding for now, ready to receive code when implementation begins.

#### [NEW] `src/core/`
Scaffold for the universal orchestration engine.
#### [NEW] `src/adapters/sdlc/`
Scaffold for the software delivery adapter.
#### [NEW] `src/adapters/personal/`
Scaffold for the personal performance optimization adapter.
#### [NEW] `src/adapters/team/`
Scaffold for the team performance optimization adapter.
#### [NEW] `src/shared/`
Scaffold for shared utilities and cross-cutting concerns.

---

### 4. File System Refactor: The `docs/` Reality Hub
This directory is reserved exclusively for official, finalized documents that reflect the actual built software.
#### [RETAIN] `docs/guides/`
The Git & GitHub guidebooks we just generated will remain here as the first pieces of finalized documentation.

---

## Verification Plan

### Automated Verification
After executing the `mv` and `mkdir` commands, we will run the following to verify the structural integrity:
```bash
tree -L 3
```

### Manual Verification
1. Review `AGENTS.md` to ensure the tone is imperative, concise, and effectively protects the root manifests.
2. Verify that `design/plans/contracts/` successfully moved to `design/plans/contracts/` and was not prematurely moved to `src/`.
