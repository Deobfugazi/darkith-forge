#!/usr/bin/env bash
# Continuity: restore the project into a fresh (ephemeral) VM.
#
#   tools/restore.sh [target-dir]
#
# If the workspace already holds the repo, it just pulls. Otherwise it clones
# from the private repo. Run this FIRST in any new session.
set -euo pipefail

REPO="${DARKITH_REPO:-Deobfugazi/darkith-forge}"
BRANCH="${DARKITH_BRANCH:-main}"
TARGET="${1:-$PWD}"

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "restore: GITHUB_TOKEN not set" >&2
  exit 2
fi

URL="https://${GITHUB_TOKEN}@github.com/${REPO}.git"

if git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "restore: existing work tree at $TARGET — fetching $BRANCH"
  git -C "$TARGET" remote get-url origin >/dev/null 2>&1 \
    || git -C "$TARGET" remote add origin "$URL"
  git -C "$TARGET" fetch -q "$URL" "$BRANCH"
  git -C "$TARGET" merge -q --ff-only FETCH_HEAD 2>/dev/null \
    || echo "restore: local commits diverge; inspect before merging"
  git -C "$TARGET" --no-pager log --oneline -5
else
  echo "restore: cloning $REPO into $TARGET"
  git clone -q "$URL" "$TARGET"
  git -C "$TARGET" --no-pager log --oneline -5
fi
echo "restore: done"
