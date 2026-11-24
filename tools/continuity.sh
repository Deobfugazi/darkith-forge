#!/usr/bin/env bash
# Continuity: create a guarded local checkpoint. Remote publication is separate.
#   tools/continuity.sh [commit message] [--publish]
# --publish delegates to sync.sh --publish and requires current authorization under NEVER #21.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

REMOTE="${DARKITH_REMOTE:-origin}"
BRANCH="${DARKITH_BRANCH:-$(git symbolic-ref --short HEAD 2>/dev/null || echo main)}"
PUBLISH=0
if [ "${1:-}" = "--publish" ]; then PUBLISH=1; shift; fi
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

if [ "$PUBLISH" -eq 1 ]; then
  exec "$(git rev-parse --show-toplevel)/tools/sync.sh" --publish
fi
echo "continuity: local checkpoint complete; no remote publication performed"
