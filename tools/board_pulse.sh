#!/usr/bin/env bash
# board_pulse.sh — local checks by default; remote publication requires --publish.
#   --check     verify local TASKS.md matches HEAD
#   --ping      print last pulse
#   --publish   commit and push current branch; governed by DARKITH.md NEVER #21
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
if [ "${1:-}" = "--publish" ] && command -v flock >/dev/null 2>&1; then
  exec 9>"$(git rev-parse --git-dir)/darkith-board-pulse.lock"
  flock -w 120 9 || { echo "board_pulse: FAIL — another pulse held the lock >120s; not pushing blind"; exit 1; }
fi

case "${1:-}" in
  --ping)
    if [ -f "$PING" ]; then cat "$PING"; else echo '{"note":"no board ping yet"}'; fi
    exit 0
    ;;
  --check)
    if ! git diff --quiet HEAD -- "$BOARD"; then
      echo "board_pulse: FAIL — TASKS.md has local changes not included in HEAD"; exit 1
    fi
    echo "board_pulse: PASS — TASKS.md matches the local commit"; exit 0
    ;;
  --publish) ;;
  *)
    echo "board_pulse: no publication performed. Use --check, --ping, or --publish."
    echo "--publish requires current authorization under DARKITH.md NEVER #21."
    exit 2
    ;;
esac

# explicit --publish: commit the complete tree, then publish the current branch.
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
