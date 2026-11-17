#!/usr/bin/env bash
# board_pulse.sh — push the task board in REAL TIME so a parallel worker sees it at once.
#
# The Operator runs two or more agents in parallel. When one agent updates the board, the
# other must be pinged without the Operator repeating himself. The board is only "pushed"
# when its bytes are on the remote, so this tool commits and pushes the board the moment it
# changes, and records a ping (SHA + timestamp) the parallel worker can read.
#
#   tools/board_pulse.sh            push the board now (commit + push); write the ping
#   tools/board_pulse.sh --check    gate: fail if the board has uncommitted changes (not
#                                   pushed in real time)
#   tools/board_pulse.sh --ping     print the last ping (SHA + when) so a worker can react
#
# Provider-neutral: pushes to `origin` (or $DARKITH_REMOTE). Auth is whatever the git
# credential helper already provides. The ping is a tracked file so it travels with the
# push and is visible to every checkout.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2

ROOT="$(git rev-parse --show-toplevel)"
REMOTE="${DARKITH_REMOTE:-origin}"
BRANCH="${DARKITH_BRANCH:-$(git symbolic-ref --short HEAD 2>/dev/null || echo main)}"
BOARD="TASKS.md"
PING="proof/board_pulse.json"

# the board's own clock — the generated runtime, so the ping time matches every other surface
STAMP="$(python3 -c 'import sys;sys.path.insert(0,"build/gen");import omega_time_runtime as t;print(t.iso())' 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"

case "${1:-}" in
  --ping)
    if [ -f "$PING" ]; then cat "$PING"; else echo '{"note":"no board ping yet"}'; fi
    exit 0
    ;;
  --check)
    # "pushed" means the board's bytes are on the REMOTE, not merely committed locally —
    # a local commit a parallel worker cannot fetch is still a private view. Compare the
    # local board against the remote branch's copy.
    if ! git diff --quiet -- "$BOARD" 2>/dev/null || ! git diff --cached --quiet -- "$BOARD" 2>/dev/null; then
      echo "board_pulse: FAIL — $BOARD has uncommitted changes: the board was NOT pushed in"
      echo "             real time, so a parallel worker cannot see it. Run tools/board_pulse.sh."
      exit 1
    fi
    git fetch -q "$REMOTE" "$BRANCH" 2>/dev/null || { echo "board_pulse: WARN — remote unreachable; local board clean but push unverified"; exit 0; }
    LOCAL="$(git rev-parse "$BRANCH" 2>/dev/null)"
    REMOTE_SHA="$(git rev-parse "$REMOTE/$BRANCH" 2>/dev/null)"
    if [ "$LOCAL" != "$REMOTE_SHA" ]; then
      echo "board_pulse: FAIL — local $BRANCH ($LOCAL) != $REMOTE/$BRANCH ($REMOTE_SHA):"
      echo "             the board is not on the remote, so a parallel worker is blind."
      exit 1
    fi
    echo "board_pulse: PASS — the board is pushed to $REMOTE/$BRANCH ($(git rev-parse --short HEAD))"
    exit 0
    ;;
esac

# default: push the board now — with the whole tree, so the push is a consistent snapshot a
# parallel worker can converge onto (a board that names a commit whose tree is elsewhere is
# not a ping, it is noise).
python3 - "$STAMP" <<'PY' > "$PING"
import json, sys
print(json.dumps({"pushed_at": sys.argv[1], "agent": "primary",
                  "note": "board updated; parallel worker should fetch and converge"}, indent=2))
PY

git add -A
if git diff --cached --quiet 2>/dev/null; then
  echo "board_pulse: nothing to commit"
else
  git commit -q -m "board: real-time pulse — board pushed at $STAMP" || { echo "board_pulse: commit failed"; exit 1; }
fi
NEW="$(git rev-parse --short HEAD)"
python3 - "$NEW" "$STAMP" <<'PY' > "$PING"
import json, sys
print(json.dumps({"board_commit": sys.argv[1], "pushed_at": sys.argv[2], "agent": "primary",
                  "note": "board updated; parallel worker should fetch and converge"}, indent=2))
PY
git add "$PING"
# a second, tiny commit for the ping — never an amend, which could rewrite an unrelated commit
git commit -q -m "board: ping $NEW at $STAMP" >/dev/null 2>&1 || true

if git push -q "$REMOTE" "$BRANCH" 2>/dev/null; then
  echo "board_pulse: pushed $(git rev-parse --short HEAD) ($BOARD) to $REMOTE/$BRANCH at $STAMP"
  echo "board_pulse: ping -> $PING (parallel worker: fetch, then tools/converge.sh)"
else
  echo "board_pulse: WARN — push failed (offline or no remote); committed locally as $(git rev-parse --short HEAD)"
fi
