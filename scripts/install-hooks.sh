#!/usr/bin/env bash
# One-time setup: point git at the tracked .githooks/ directory instead of the untracked,
# per-clone .git/hooks/ -- so the pre-commit hook is version-controlled and every clone gets
# it automatically rather than each contributor copying a file by hand.
#
#     scripts/install-hooks.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

chmod +x .githooks/pre-commit
git config core.hooksPath .githooks

echo "core.hooksPath set to .githooks -- the pre-commit hook is now active."
echo "It runs scripts/check_frontmatter.py and scripts/sync_counts.py on every commit."
