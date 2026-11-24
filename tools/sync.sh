#!/usr/bin/env bash
# sync.sh — fetch and reconcile locally by default; never publish implicitly.
#   --check = read-only; no args = local reconcile; --publish = explicit remote push.
# Publication is governed by DARKITH.md NEVER #21.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

REMOTE="${DARKITH_REMOTE:-origin}"
BRANCH="${DARKITH_BRANCH:-main}"
CHECK=0
PUBLISH=0
for arg in "$@"; do
  [ "$arg" = "--check" ] && CHECK=1
  [ "$arg" = "--publish" ] && PUBLISH=1
done

# ---- resolve the remote URL, without naming a vendor ---------------------
if [ -n "${DARKITH_REMOTE_URL:-}" ]; then
  URL="$DARKITH_REMOTE_URL"
elif git remote get-url "$REMOTE" >/dev/null 2>&1; then
  URL="$(git remote get-url "$REMOTE")"
else
  echo "sync: no remote '$REMOTE' found (set DARKITH_REMOTE_URL to the clone URL)" >&2
  exit 2
fi

# Refuse to sync a dirty tree: an uncommitted edit would be lost in a rebase.
if [ "$CHECK" = 0 ] && [ -n "$(git status --porcelain)" ]; then
  echo "sync: working tree is dirty — commit first (tools/continuity.sh)." >&2
  git status --short >&2
  exit 1
fi

git fetch -q "$URL" "$BRANCH:refs/remotes/origin/$BRANCH"
REMOTE_SHA="$(git rev-parse "refs/remotes/origin/$BRANCH")"
LOCAL_SHA="$(git rev-parse HEAD)"
# Keep the tracking ref honest: `git push <url>` moves the remote branch but not
# our origin/* ref, so a stale ref would misreport the truth to the next reader.
mark_synced() { git update-ref "refs/remotes/origin/$BRANCH" HEAD; }

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  echo "sync: in sync at ${LOCAL_SHA:0:7}"
  exit 0
fi

if git merge-base --is-ancestor "$LOCAL_SHA" "$REMOTE_SHA"; then
  STATE=behind
elif git merge-base --is-ancestor "$REMOTE_SHA" "$LOCAL_SHA"; then
  STATE=ahead
else
  STATE=diverged
fi

if [ "$CHECK" = 1 ]; then
  counts="$(git rev-list --left-right --count HEAD...FETCH_HEAD)"
  echo "sync: NOT in sync (${STATE}); ahead/behind = ${counts}"
  exit 1
fi

case "$STATE" in
  behind)
    git merge --ff-only -q "$REMOTE_SHA"; mark_synced
    echo "sync: fast-forwarded to ${REMOTE_SHA:0:7}"
    ;;
  ahead)
    if [ "$PUBLISH" -eq 1 ]; then git push -q "$URL" "HEAD:${BRANCH}"; mark_synced; echo "sync: published ${LOCAL_SHA:0:7}"; else echo "sync: local branch is ahead; publication not performed"; fi
    ;;
  diverged)
    # The other tab published while we were working. Replay our commits on top
    # of theirs. A conflict means both tabs edited the SAME lines: stop and let
    # a human decide — never auto-resolve, never force.
    if ! git rebase "$REMOTE_SHA" >/dev/null 2>&1; then
      echo "sync: CONFLICT — both tabs changed the same lines. Nothing pushed." >&2
      git --no-pager diff --name-only --diff-filter=U >&2 || true
      echo "      Resolve by hand, then: git rebase --continue  (or git rebase --abort)" >&2
      exit 3
    fi
    if [ "$PUBLISH" -eq 1 ]; then git push -q "$URL" "HEAD:${BRANCH}"; mark_synced; echo "sync: rebased and published"; else echo "sync: rebased locally; publication not performed"; fi
    ;;
esac
