#!/usr/bin/env bash
# Continuity: persist ALL progress to a git remote so nothing is lost when the agent
# VM is recycled. The VM filesystem is ephemeral; only pushed bytes survive.
#
#   tools/continuity.sh ["commit message"]
#
# Provider-neutral: it pushes to whatever git remote is configured as `origin` (or
# $DARKITH_REMOTE). No hosting provider is named here. Auth is whatever your git
# credential helper already provides (token, SSH key, or nothing for a local bare repo).
# To pin a specific URL for one run, set DARKITH_REMOTE_URL.
#
# Safe by design: refuses to push if signing key material ever becomes tracked.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

REMOTE="${DARKITH_REMOTE:-origin}"
BRANCH="${DARKITH_BRANCH:-$(git symbolic-ref --short HEAD 2>/dev/null || echo main)}"
MSG="${1:-checkpoint $(date -u +%Y-%m-%dT%H:%M:%SZ)}"

# ---- guard: never commit the signing identity ---------------------------
SECRETS_RE='(^|/)(release_key|release_cert)$|\.(keystore|jks|p8|p12|pfx|pem|key)$'
if git ls-files | grep -qiE "$SECRETS_RE"; then
  echo "REFUSING: secret material is tracked in git:" >&2
  git ls-files | grep -iE "$SECRETS_RE" >&2
  echo "Remove it (git rm --cached) and add it to .gitignore first." >&2
  exit 1
fi

git add -A

# ---- guard: never commit a private key even if the filename looks innocent ----
# Scan what is STAGED (including files just added), not just what was already tracked.
KEY_RE='BEGIN (RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY'
keyhit="$(git diff --cached --name-only -z | xargs -0 -r grep -lE "$KEY_RE" 2>/dev/null || true)"
if [ -n "$keyhit" ]; then
  echo "REFUSING: a staged file contains a PRIVATE KEY block:" >&2
  printf '  %s\n' $keyhit >&2
  echo "Unstage it (git restore --staged <file>) and add it to .gitignore." >&2
  exit 1
fi

if git diff --cached --quiet; then
  echo "continuity: nothing new to commit"
else
  git commit -q -m "$MSG"
  echo "continuity: committed $(git rev-parse --short HEAD) — $MSG"
fi

# ---- commit locally (guarded above), then converge via the ONE path ---------
# Convergence lives in ONE place: tools/sync.sh integrates the other tab's
# commits and publishes ours (never forced). Do not duplicate that logic here.
exec "$(git rev-parse --show-toplevel)/tools/sync.sh"
