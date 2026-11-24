#!/usr/bin/env bash
# Reconcile local branches only. This helper never pushes to a remote.
#   --check = read-only status; no args = fetch/reconcile locally.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
if [[ " $* " == *" --publish "* ]]; then
  echo "sync: REFUSED — remote publication is outside this helper; follow DARKITH.md NEVER #21"
  exit 2
fi
REMOTE="${DARKITH_REMOTE:-origin}"
BRANCH="${DARKITH_BRANCH:-$(git symbolic-ref --short HEAD 2>/dev/null || echo main)}"
CHECK=0
[[ " $* " == *" --check "* ]] && CHECK=1
if [ -n "${DARKITH_REMOTE_URL:-}" ]; then URL="$DARKITH_REMOTE_URL"
elif git remote get-url "$REMOTE" >/dev/null 2>&1; then URL="$(git remote get-url "$REMOTE")"
else echo "sync: no remote '$REMOTE' found" >&2; exit 2; fi
if [ "$CHECK" = 0 ] && [ -n "$(git status --porcelain)" ]; then
  echo "sync: working tree is dirty — checkpoint locally first" >&2
  git status --short >&2
  exit 1
fi
git fetch -q "$URL" "$BRANCH:refs/remotes/origin/$BRANCH"
REMOTE_SHA="$(git rev-parse "refs/remotes/origin/$BRANCH")"
LOCAL_SHA="$(git rev-parse HEAD)"
if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  echo "sync: in sync at ${LOCAL_SHA:0:7}"; exit 0
fi
if git merge-base --is-ancestor "$LOCAL_SHA" "$REMOTE_SHA"; then STATE=behind
elif git merge-base --is-ancestor "$REMOTE_SHA" "$LOCAL_SHA"; then STATE=ahead
else STATE=diverged
fi
if [ "$CHECK" = 1 ]; then
  counts="$(git rev-list --left-right --count HEAD...FETCH_HEAD)"
  echo "sync: NOT in sync (${STATE}); ahead/behind = ${counts}"
  exit 1
fi
case "$STATE" in
  behind)
    git merge --ff-only -q "$REMOTE_SHA"
    echo "sync: fast-forwarded locally to ${REMOTE_SHA:0:7}"
    ;;
  ahead)
    echo "sync: local branch is ahead; no remote publication performed"
    ;;
  diverged)
    if ! git rebase "$REMOTE_SHA" >/dev/null 2>&1; then
      echo "sync: CONFLICT — both branches changed overlapping lines; nothing published" >&2
      git --no-pager diff --name-only --diff-filter=U >&2 || true
      echo "Resolve manually, then git rebase --continue or --abort" >&2
      exit 3
    fi
    echo "sync: rebased locally; no remote publication performed"
    ;;
esac
