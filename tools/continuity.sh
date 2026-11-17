#!/usr/bin/env bash
# Continuity: persist ALL progress to the private repo so nothing is lost when
# the agent VM is recycled. The VM filesystem is ephemeral; only pushed bytes
# survive.
#
#   tools/continuity.sh ["commit message"]
#
# Safe by design: refuses to push if signing key material ever becomes tracked.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

REPO="${DARKITH_REPO:-Deobfugazi/darkith-forge}"
BRANCH="${DARKITH_BRANCH:-main}"
MSG="${1:-checkpoint $(date -u +%Y-%m-%dT%H:%M:%SZ)}"

# ---- guard: never commit the signing identity ---------------------------
if git ls-files | grep -qiE '(^|/)(release_key|release_cert)$|\.(keystore|p8|pem)$'; then
  echo "REFUSING: secret material is tracked in git:" >&2
  git ls-files | grep -iE '(^|/)(release_key|release_cert)$|\.(keystore|p8|pem)$' >&2
  echo "Remove it (git rm --cached) and add it to .gitignore first." >&2
  exit 1
fi

git add -A
if git diff --cached --quiet; then
  echo "continuity: nothing new to commit"
else
  git commit -q -m "$MSG"
  echo "continuity: committed $(git rev-parse --short HEAD) — $MSG"
fi

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "continuity: GITHUB_TOKEN not set; commit is local only." >&2
  echo "             the VM may be recycled — set the token and re-run." >&2
  exit 2
fi

# Convergence lives in ONE place: tools/sync.sh integrates the other tab's
# commits and publishes ours (never forced). Do not duplicate that logic here.
exec "$(git rev-parse --show-toplevel)/tools/sync.sh"
