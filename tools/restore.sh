#!/usr/bin/env bash
# Continuity: restore the project into a fresh (ephemeral) VM.
#
#   tools/restore.sh [target-dir]
#
# If the workspace already holds the repo, it just pulls. Otherwise it clones from the
# configured remote. Run this FIRST in any new session.
#
# Provider-neutral: uses the `origin` remote (or $DARKITH_REMOTE / $DARKITH_REMOTE_URL).
# No host is named here. Auth is whatever your git credential helper provides.
set -euo pipefail

REMOTE="${DARKITH_REMOTE:-origin}"
BRANCH="${DARKITH_BRANCH:-main}"
TARGET="${1:-$PWD}"

# ---- resolve the remote URL, without naming a vendor ---------------------
if [ -n "${DARKITH_REMOTE_URL:-}" ]; then
  URL="$DARKITH_REMOTE_URL"
elif git -C "$TARGET" remote get-url "$REMOTE" >/dev/null 2>&1; then
  URL="$(git -C "$TARGET" remote get-url "$REMOTE")"
elif git remote get-url "$REMOTE" >/dev/null 2>&1; then
  URL="$(git remote get-url "$REMOTE")"
else
  echo "restore: no remote '$REMOTE' found; set DARKITH_REMOTE_URL to the clone URL." >&2
  exit 2
fi

if git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "restore: existing work tree at $TARGET — converging via tools/sync.sh"
  # One convergence path: integrate the other tab's commits, then publish ours.
  ( cd "$TARGET" && DARKITH_BRANCH="$BRANCH" DARKITH_REMOTE="$REMOTE" \
      bash tools/sync.sh ) || true
  git -C "$TARGET" --no-pager log --oneline -5
else
  echo "restore: cloning into $TARGET"
  git clone -q "$URL" "$TARGET"
  git -C "$TARGET" --no-pager log --oneline -5
fi
echo "restore: done"
