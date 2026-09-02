---
title: Detailed Git & GitHub CLI (`gh`) Guidebook
status: live
part_of: repo-meta
doc_type: reference
---

# Detailed Git & GitHub CLI (`gh`) Guidebook

This detailed guidebook explains not just *how* to run Git and GitHub CLI commands, but *why* and *when* you should use them. It covers fundamental version control workflows, advanced techniques, and time-saving shortcuts.

---

## 1. Core Git Workflows

### 1.1 Repository & Branch Management
Branches are fundamental to Git. They represent independent lines of development.
* **`git clone <url>`**: Downloads a repository and its entire history to your local machine.
* **`git branch`**: Lists all your local branches. Use `-a` to see remote branches as well.
* **`git switch -c <branch-name>`**: Creates a new branch and switches to it in one step (a more modern and safer alternative to `git checkout -b`).
* **`git switch <branch-name>`**: Moves you to an existing branch.

### 1.2 Staging & Committing
Git operates on a three-stage system: Working Directory (your files), Staging Area (what you plan to commit), and the Repository (committed history).
* **`git status`**: Your most used command. It tells you what files are modified, staged, or untracked.
* **`git add <file>`** or **`git add .`**: Moves changes from your working directory to the staging area.
* **`git commit -m "Message"`**: Permanently saves the staged changes into the repository's history. **Tip:** Write clear, imperative commit messages like "Add login button".

### 1.3 Syncing with Remotes
To collaborate, you must synchronize your local repository with a remote repository (like GitHub).
* **`git fetch`**: Downloads new data from a remote repository but *does not* integrate it into your working files. It’s safe and allows you to inspect changes first.
* **`git pull`**: Fetches changes *and* merges them into your current branch. It’s equivalent to running `git fetch` followed by `git merge`.
* **`git push`**: Uploads your local commits to the remote repository.

### 1.4 Merging, Rebasing & Squashing
When a feature is complete, it needs to be integrated.
* **`git merge <branch>`**: Takes the contents of a source branch and integrates them with a target branch. This preserves history exactly as it happened, but can create "merge commits" that clutter the timeline.
* **`git rebase <branch>`**: Moves your current branch's base to the tip of another branch. This rewrites history to create a clean, linear progression without merge commits. *Caution: Never rebase commits that have already been pushed to a public branch.*
* **Squashing (`git rebase -i HEAD~N`):** An interactive rebase allows you to fold multiple messy "work in progress" commits into a single, cohesive commit before merging.

### 1.5 Chaining Commands (Time Savers)
You can use standard bash operators like `&&` to combine commands. If the first command succeeds, the next runs automatically.
* **Rapid Commit & Push:** `git add . && git commit -m "update" && git push`
* **Create, Switch & Push Upstream:** `git switch -c new-feature && git push -u origin new-feature`
* **Update, Rebase & Push Cleanly:** `git fetch && git rebase origin/main && git push --force-with-lease` (Forces a push safely by ensuring no one else has pushed in the meantime).

---

## 2. Advanced Git Concepts

### 2.1 Managing Upstream & Remote Branches
When working on forks, you often need to track the original repository (the "upstream").
* **`git remote add upstream <url>`**: Links the original repository so you can pull its latest changes.
* **`git fetch upstream && git rebase upstream/main`**: A common workflow to keep your fork up-to-date with the original repository.

### 2.2 Git Stash (Saving Work in Progress)
Sometimes you are working on a feature, but need to quickly switch branches to fix a bug. You don't want to commit half-finished work.
* **`git stash`**: Shelves your uncommitted changes temporarily.
* **`git stash pop`**: Restores your shelved changes to your working directory.

### 2.3 Cherry-Picking
If a colleague makes a great commit on another branch and you want *just that commit* without merging the whole branch:
* **`git cherry-pick <commit-hash>`**: Copies the specified commit and applies it to your current branch.

### 2.4 Git Reflog (Disaster Recovery)
If you accidentally delete a branch, perform a bad rebase, or reset too far, Git actually keeps a hidden log of everywhere your HEAD pointer has been.
* **`git reflog`**: Displays this history. Find the hash of where you want to be, and run `git reset --hard <hash>` to recover it.

### 2.5 Resetting vs. Reverting
When you make a mistake and need to undo a commit:
* **`git revert <commit-hash>`**: Creates a *new* commit that applies the exact inverse of the bad commit. This is the only safe way to undo a push on a public branch.
* **`git reset --hard <commit-hash>`**: Erases history by moving the branch pointer backward. This is great for local mistakes but disastrous if pushed, as it overwrites shared history.

### 2.6 Git Bisect (Bug Hunting)
When a bug surfaces but you don't know which commit caused it:
* Run `git bisect start`, tag a known bad commit (`git bisect bad`), and a known good one (`git bisect good <hash>`). Git will perform a binary search, checking out commits in the middle, asking you to test until you find the exact culprit.

### 2.7 Git Worktrees
If you need to work on two branches simultaneously (e.g., waiting for tests to pass on one while coding on another), checking out branches back-and-forth is slow.
* **`git worktree add ../new-dir <branch>`**: Checks out a branch into an entirely separate directory, sharing the `.git` folder but giving you two independent working directories.

### 2.8 Git Hooks
Git can run custom scripts automatically at different stages.
* By placing scripts in `.git/hooks/` (like `pre-commit` or `pre-push`), you can enforce linting, run tests, or block bad commits before they happen.

### 2.9 Submodules
If your project relies on another Git repository, you can embed it.
* **`git submodule add <url>`**: Embeds a repo. When cloning a repo with submodules, you must use `git submodule update --init --recursive` to pull down the embedded code.

---

## 3. GitHub CLI (`gh`) Integrations

The GitHub CLI brings pull requests, issues, and actions to your terminal.

### 3.1 Pull Requests
* **`gh pr create`**: Opens a prompt to create a PR directly from the terminal. You can bypass the prompt with flags: `gh pr create --title "Fix bug" --body "Details"`.
* **`gh pr checkout <number>`**: Instantly checks out a colleague's PR branch to test locally.
* **`gh pr review`**: Review and approve a PR without opening the browser.

### 3.2 Managing CI & Actions Workflows
* **`gh run list`**: See the status of your recent GitHub Actions.
* **`gh run watch`**: Follow the live progress of a CI run in your terminal.
* **`gh workflow run <name>`**: Manually trigger a workflow (like a deployment).

### 3.3 Releases & Issues
* **`gh issue create`**: File an issue directly from the terminal.
* **`gh release create <tag>`**: Generate a new release on GitHub, automatically attaching release notes and binaries.
