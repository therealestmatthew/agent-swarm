#!/usr/bin/env bash
# Save the run you just did as the parachute, and print the seek URLs for it.
#
#     tools/save-parachute.sh                    # runs/current -> logs/backup-live.jsonl
#     tools/save-parachute.sh runs/other
#
# 04-TOMORROW-RUNBOOK.md's T+75 checklist is "full run end to end, saved to
# logs/backup-live.jsonl" — this is that step. Once you have a real run, THIS file is the
# parachute, not logs/golden.jsonl: the synthetic log shows Payload A's findings whatever
# you actually demoed.
set -euo pipefail

SRC="${1:-runs/current}/events.jsonl"
DEST="logs/backup-live.jsonl"

cd "$(dirname "$0")/.."

if [[ ! -f "$SRC" ]]; then
  echo "no log at $SRC — run the swarm first, or pass the run directory" >&2
  exit 1
fi

COUNT=$(grep -c '' "$SRC" || true)
if [[ "$COUNT" -lt 2 ]]; then
  echo "$SRC has $COUNT lines — that is not a run. Refusing to overwrite the parachute." >&2
  exit 1
fi

mkdir -p logs
# Keep the previous parachute: two are better than one, and this is the file you fall back
# to on stage. Never leave yourself with zero because a bad run overwrote a good one.
if [[ -f "$DEST" ]]; then
  cp "$DEST" "logs/backup-live.prev.jsonl"
  echo "previous parachute kept at logs/backup-live.prev.jsonl"
fi

cp "$SRC" "$DEST"
echo "saved $COUNT events: $SRC -> $DEST"
echo
python3 tools/beats.py "$DEST"

cat <<'EOF'
Now do the thing that actually matters: copy logs/backup-live.jsonl off this machine.
A parachute that only exists on the laptop you are demoing from is not a parachute.
EOF
