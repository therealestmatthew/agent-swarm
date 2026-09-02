---
title: "Walkthrough: File System Refactor & AGENTS.md"
status: live
part_of: repo-meta
doc_type: reference
---

# Walkthrough: File System Refactor & AGENTS.md

## Changes Made
1. **File System Refactoring:**
   - Relocated the `plan/` and `audit/` directories to their new staging ground at `design/plans/` and `design/audits/`.
   - Scaffolded the future executable modular bundles into the `src/` directory (`src/core/`, `src/adapters/sdlc/`, `src/adapters/personal/`, `src/adapters/team/`, `src/shared/`).
   - Established the `docs/` directory as the hub for finalized reality, containing the previously generated `docs/guides/`.

2. **Root File Generation:**
   - Created **`AGENTS.md`**, serving as the "README for AI," complete with explicit rules on tooling protection, design/reality delineation, manual pre-commit validation hook execution, and append-only changelog rules.
   - Created **`README.md`** as a human-friendly entry point to introduce the mission, core vs. adapter split, and the design-phase scaffolding.
   - Created **`CONTRIBUTING.md`** with guidelines enforcing the `design/` vs `docs/` boundary.
   - Created **`CHANGELOG.md`** with an initialized state and an explicit process warning regarding its append-only nature.

## What Was Tested
- Directory structure was verified using standard bash tools (`find`, `ls`) to ensure all moves were successful and the new hierarchies were established.
- All manifest files (`AGENTIC_ARCHITECTURE_MANIFEST.md` and `FRONTMATTER_MANIFEST.md`) were confirmed untouched at the root of the repository.

## Validation Results
- The file system now properly delineates between conceptual work (`design/`), future implementation (`src/`), and finalized documentation (`docs/`), while establishing clear operational rules for AI agents in `AGENTS.md`.
