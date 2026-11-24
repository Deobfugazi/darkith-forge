#!/usr/bin/env bash
# sync.sh — CONVERGE this tab with the authoritative history on the remote.
#
# Two (or more) OpenHands tabs run in separate ephemeral sandboxes that share
# ONLY the git remote. The remote branch is the single authoritative history;
# a tab is just a checkout of it. This script is the executable form of that
# law: integrate the other tab's commits, then publish ours — and never lose a
# commit, because the push is never forced.
#
#   tools/sync.sh            converge (fetch + rebase-if-diverged + push)
#   tools/sync.sh --check    report only; non-zero if not in sync (a gate)
#
# Provider-neutral: it uses the `origin` remote (or $DARKITH_REMOTE /
# $DARKITH_REMOTE_URL). No hosting provider is named. Auth is whatever your git
# credential helper provides (token, SSH key, or nothing for a local bare repo).
#
# Exit: 0 in sync / 3 divergence needs a human (same lines edited) / 2 no remote.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

REMOTE="${DARKITH_REMOTE:-origin}"
# Default to the branch you are actually on. This used to default to `main`
# unconditionally, so a bare `tools/sync.sh` on a feature branch fetched main, rebased
# against main, and pushed `HEAD:main` — publishing whatever branch you happened to be on
# onto main. Publishing is not an implicit side effect of syncing.
BRANCH="${DARKITH_BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

# main is the Operator's branch. Syncing onto it requires the Operator to say so, per call.
if [ "$BRANCH" = "main" ] && [ "${DARKITH_ALLOW_MAIN_PUSH:-0}" != "1" ]; then
  if [ "$CHECK" = 1 ]; then
    echo "sync: will not check main without DARKITH_ALLOW_MAIN_PUSH=1" >&2
    exit 3
  fi
  echo "sync: refusing to publish to main." >&2
  echo "      main is the Operator's branch; publishing to it is not a sync side effect." >&2
  echo "      to publish on purpose: DARKITH_ALLOW_MAIN_PUSH=1 tools/sync.sh" >&2
  exit 3
fi

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
    git push -q "$URL" "HEAD:${BRANCH}"; mark_synced
    echo "sync: pushed ${LOCAL_SHA:0:7} (was ahead)"
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
    git push -q "$URL" "HEAD:${BRANCH}"; mark_synced
    echo "sync: rebased onto ${REMOTE_SHA:0:7} and pushed ${LOCAL_SHA:0:7}"
    ;;
esac
