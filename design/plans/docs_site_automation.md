---
title: "Plan: Documentation Site Automation (Option C)"
status: live
part_of: agentic-sdlc
doc_type: reference
---

# Plan: Documentation Site Automation (Option C)

## Overview
This document outlines the future architecture and setup for automating the generation of a static HTML documentation website directly from the repository's Markdown files. This allows developers and AI agents to manage documentation simply by editing `.md` files, while a CI/CD pipeline handles the website generation and hosting.

## 1. Tooling: MkDocs & Material Theme
We will use **MkDocs**, a fast and simple static site generator that is purpose-built for project documentation. 
* **Core Dependency:** `mkdocs`
* **UI Theme:** `mkdocs-material` (an industry standard, responsive, and highly customizable theme)

## 2. Directory & Configuration Structure
* All markdown files will remain in the `docs/` directory (e.g., `docs/guides/git_gh_cheatsheet.md`).
* A new configuration file, `mkdocs.yml`, will be added to the repository root.

**Example `mkdocs.yml` structure:**
```yaml
site_name: Agent Swarm Documentation
theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
nav:
  - Home: index.md
  - Guides:
    - Git Cheatsheet: guides/git_gh_cheatsheet.md
    - Detailed Git Guide: guides/git_gh_guidebook_detailed.md
```

## 3. CI/CD Automation (GitHub Actions)
To eliminate manual HTML generation, we will configure a GitHub Actions workflow.

* **Workflow File:** `.github/workflows/deploy-docs.yml`
* **Trigger:** The workflow will trigger on `push` events to the `main` branch, specifically when files in the `docs/` directory are modified.
* **Action:** The workflow will check out the code, install python dependencies (`mkdocs-material`), run `mkdocs gh-deploy`, and automatically push the compiled static site to a `gh-pages` branch.
* **Hosting:** GitHub Pages will be configured to serve the site from the `gh-pages` branch.

## Execution Steps (When Ready)
1. Run `pip install mkdocs-material`.
2. Run `mkdocs new .` to initialize the base configuration.
3. Move `docs/guides/` into the structure defined by MkDocs.
4. Add `.github/workflows/deploy-docs.yml`.
5. Enable GitHub Pages on the repository settings.
