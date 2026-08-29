---
title: README for AI Agents
status: live
part_of: repo-meta
doc_type: reference
---

# README for AI Agents

Welcome. You are operating in the `agent-swarm` repository. This file contains critical operational constraints. Do not infer conventions—follow these rules explicitly.

## 1. Tooling & Manifest Protection (CRITICAL)
This repository relies heavily on custom tooling and manifests.
* **NEVER modify** `AGENTIC_ARCHITECTURE_MANIFEST.md` or `FRONTMATTER_MANIFEST.md` unless explicitly instructed by the user. These files are structurally tied to Python tools.
* **Mandatory Pre-Commit Validation:** Before committing any changes to files in the `design/` directory, you **must manually run** the validation scripts in the `scripts/` folder (e.g., `python scripts/check_agent_cards.py`, `python scripts/check_frontmatter.py`). There are no automated Git hooks yet; you are responsible for running these checks and fixing any errors before concluding your task.

## 2. File System Delineation
Understand the difference between planning and reality:
* `design/`: This is the staging ground. It contains brainstorming, concepts, schemas, and historical plans (`design/plans/`, `design/audits/`). Do not confuse these with actual implementations. Python contracts currently reside here until active implementation begins.
* `docs/`: This is for **finalized reality**. Only official, implemented architectures, guides, and runbooks go here. 
* `src/`: The future executable codebase (modular bundles). Currently empty scaffolding.

## 3. Changelog Policy
* Modifying `CHANGELOG.md` is strictly **Append-Only**. 
* Never replace, rewrite, or delete historical entries. Always append new changes when merging PRs or making significant commits.

## 4. LLM-Specific Instructions
* If you are a Claude model (Anthropic), you must also cross-reference `CLAUDE.md` at the project root for domain-specific architectural context regarding the Agentic SDLC Orchestration.
