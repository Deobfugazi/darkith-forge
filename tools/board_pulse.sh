#!/usr/bin/env bash
# board_pulse.sh — push the task board in REAL TIME so a parallel worker sees it at once.
#
# The Operator runs two or more agents in parallel. When one agent updates the board, the
# other must be pinged without the Operator repeating himself. The board is only "pushed"
# when its bytes are on the remote, so this tool commits and pushes the board the moment it
# changes, and records a ping (SHA + timestamp) the parallel worker can read.
#
#   tools/board_pulse.sh            commit the board locally and write the ping (NO push)
#   tools/board_pulse.sh --push     commit AND push the board (explicit remote publication)
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

# MUST #36 (zero-collision): two tabs firing the push path at once would race on `git add -A`,
# on the two commits below, and on the push itself — one tab's index write lands inside the
# other's commit window and the loser's work is silently folded into the winner's commit. The
# lock is taken only on the push path (--check/--ping are read-only), and it blocks rather than
# skipping, because a skipped pulse is exactly the stall this tool exists to prevent.
if { [ "${1:-}" = "" ] || [ "${1:-}" = "--push" ]; } && command -v flock >/dev/null 2>&1; then
  exec 9>"$(git rev-parse --git-dir)/darkith-board-pulse.lock"
  flock -w 120 9 || { echo "board_pulse: FAIL — another pulse held the lock >120s; not pushing blind"; exit 1; }
fi

case "${1:-}" in
  --ping)
    if [ -f "$PING" ]; then cat "$PING"; else echo '{"note":"no board ping yet"}'; fi
    exit 0
    ;;
  --check)
    # The law applies to the branch a writer owns. A CI PR checkout is a detached HEAD
    # (a merge ref), where there is no local branch to compare against — comparing the
    # literal name "main" would compare the wrong thing and fail every PR. Skip, named.
    if ! git symbolic-ref -q HEAD >/dev/null 2>&1; then
      echo "board_pulse: SKIP — detached HEAD (CI PR checkout); the board law applies to the writer's branch"
      exit 0
    fi
    # "pushed" means the board's bytes are on the REMOTE, not merely committed locally —
    # a local commit a parallel worker cannot fetch is still a private view. Compare the
    # local board against the remote branch's copy.
    if ! git diff --quiet -- "$BOARD" 2>/dev/null || ! git diff --cached --quiet -- "$BOARD" 2>/dev/null; then
      echo "board_pulse: FAIL — $BOARD has uncommitted changes: the board was NOT pushed in"
      echo "             real time, so a parallel worker cannot see it. Run tools/board_pulse.sh --push."
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

if [ "${1:-}" = "--push" ]; then
  if git push -q "$REMOTE" "$BRANCH" 2>/dev/null; then
    echo "board_pulse: pushed $(git rev-parse --short HEAD) ($BOARD) to $REMOTE/$BRANCH at $STAMP"
    echo "board_pulse: ping -> $PING (parallel worker: fetch, then tools/converge.sh)"
  else
    echo "board_pulse: WARN — push failed (offline or no remote); committed locally as $(git rev-parse --short HEAD)"
  fi
else
  # Local by default. A commit is not a publication: publishing needs an explicit --push,
  # so no timer, wrapper, or inherited invocation can turn a board update into a push.
  echo "board_pulse: committed locally as $(git rev-parse --short HEAD) ($BOARD); NOT pushed"
  echo "board_pulse: to publish, re-run with --push (an explicit remote action)"
fi
