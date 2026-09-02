---
title: Git & GitHub CLI (`gh`) Guidebook (Draft)
status: live
part_of: repo-meta
doc_type: reference
---

# Git & GitHub CLI (`gh`) Guidebook (Draft)

This guidebook serves as a comprehensive reference for both foundational and advanced Git/GitHub workflows. 

---

## 1. Git Basics

### Repository & Branch Management
* **Clone a repository:** `git clone <url>`
* **Create a new branch:** `git checkout -b <branch-name>` or `git switch -c <branch-name>`
* **List branches:** `git branch` (local), `git branch -a` (all)
* **Switch branches:** `git switch <branch-name>`
* **Delete a branch:** `git branch -d <branch-name>` (safe) or `-D` (force)

### Staging & Committing
* **Check status:** `git status`
* **Stage changes:** `git add <file>` or `git add .` (all)
* **Commit changes:** `git commit -m "Your descriptive message"`

### Syncing with Remote
* **Fetch remote changes (without merging):** `git fetch`
* **Pull remote changes (fetch + merge):** `git pull origin <branch-name>`
* **Push local changes:** `git push origin <branch-name>`

### Merging, Rebasing & Squashing
* **Merge a branch into the current branch:** `git merge <branch-name>`
* **Rebase current branch onto another (e.g., main):** `git rebase main`
* **Squash commits:** Use interactive rebase `git rebase -i HEAD~N` (where N is the number of commits) and change `pick` to `squash` for the commits you want to fold into the previous one. Alternatively, `git merge --squash <branch>`.

### Chaining Commands (Time Savers)
* **Add, commit, and push:** `git add . && git commit -m "update" && git push`
* **Create, switch, and push a new branch:** `git switch -c new-feature && git push -u origin new-feature`
* **Fetch, rebase, and push:** `git fetch && git rebase origin/main && git push --force-with-lease`

---

## 2. Advanced Git Workflows (10+ Additional Key Topics)

1. **Managing Upstream & Remote Branches**
   * View remotes: `git remote -v`
   * Add an upstream remote: `git remote add upstream <url>`
   * Sync a fork: `git fetch upstream && git rebase upstream/main`
   * Track an upstream branch: `git branch -u origin/<branch-name>`

2. **Stashing (Saving Work in Progress)**
   * Save uncommitted work: `git stash`
   * Apply and remove stash: `git stash pop`
   * List stashes: `git stash list`

3. **Cherry-Picking (Applying Specific Commits)**
   * Apply a specific commit to your current branch: `git cherry-pick <commit-hash>`

4. **Git Reflog (Disaster Recovery)**
   * View the history of your HEAD (even deleted branches/lost commits): `git reflog`
   * Restore a lost state: `git reset --hard <reflog-hash>`

5. **Resetting vs. Reverting (Undoing Changes)**
   * Revert (creates a new commit undoing the changes, safe for shared history): `git revert <commit-hash>`
   * Reset (moves the branch pointer backward, rewrites history): `git reset --hard <commit-hash>` (destructive) or `git reset --soft <commit-hash>` (keeps changes staged).

6. **Interactive Rebase (`git rebase -i`)**
   * Edit, reorder, reword, drop, or squash older commits to clean up your history before pushing.

7. **Git Bisect (Bug Hunting)**
   * Perform a binary search to find the exact commit that introduced a bug:
     `git bisect start`, `git bisect bad`, `git bisect good <commit-hash>`

8. **Git Worktrees (Multiple Active Branches)**
   * Check out multiple branches simultaneously in different directories without switching contexts: `git worktree add ../new-dir <branch>`

9. **Git Tags & Versioning**
   * Create a lightweight tag: `git tag v1.0.0`
   * Create an annotated tag: `git tag -a v1.0.0 -m "Version 1.0.0"`
   * Push tags: `git push --tags`

10. **Git Hooks (Automation)**
    * Run scripts automatically on specific events (e.g., `pre-commit`, `pre-push`). Scripts live in `.git/hooks/` (or a custom directory like `.githooks/`).

11. **Git Aliases & Configuration**
    * Create shortcuts for long commands: `git config --global alias.co checkout`
    * View config: `git config --list`

12. **Submodules (Repos inside Repos)**
    * Add a submodule: `git submodule add <url>`
    * Update submodules: `git submodule update --init --recursive`

---

## 3. GitHub CLI (`gh`) & CI/CD Workflows

### Pull Requests
* **Create a PR:** `gh pr create --title "My PR" --body "Description"`
* **List PRs:** `gh pr list`
* **Checkout a PR locally:** `gh pr checkout <pr-number>`
* **Review/Merge PR:** `gh pr review` and `gh pr merge`

### Managing CI & GitHub Actions Workflows
* **View running workflows:** `gh run list`
* **Watch a specific run:** `gh run watch <run-id>`
* **Manually trigger a workflow:** `gh workflow run <workflow-name>.yml`
* **Editing Workflows:** Workflows live in `.github/workflows/`. They are defined in YAML and handle automated testing, building, and deployment upon triggers like `push` or `pull_request`.

### Issues & Releases
* **Create an issue:** `gh issue create`
* **Create a release:** `gh release create v1.0.0 --notes "Release notes"`
