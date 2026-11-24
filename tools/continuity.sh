#!/usr/bin/env bash
# Create a guarded local checkpoint only. Remote publication is a separate human action.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
if [ "${1:-}" = "--publish" ]; then
  echo "continuity: REFUSED — local checkpointing cannot publish; follow DARKITH.md NEVER #21"
  exit 2
fi
MSG="${1:-checkpoint $(date -u +%Y-%m-%dT%H:%M:%SZ)}"
SECRETS_RE='(^|/)(release_key|release_cert)$|\.(keystore|jks|p8|p12|pfx|pem|key)$'
if git ls-files | grep -qiE "$SECRETS_RE"; then
  echo "REFUSING: secret material is tracked in git:" >&2
  git ls-files | grep -iE "$SECRETS_RE" >&2
  exit 1
fi
git add -A
KEY_RE='BEGIN (RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY'
keyhit="$(git diff --cached --name-only -z | xargs -0 -r grep -lE "$KEY_RE" 2>/dev/null || true)"
if [ -n "$keyhit" ]; then
  echo "REFUSING: a staged file contains a PRIVATE KEY block:" >&2
  printf '  %s\n' $keyhit >&2
  exit 1
fi
if git diff --cached --quiet; then
  echo "continuity: nothing new to commit"
else
  git commit -q -m "$MSG"
  echo "continuity: committed local checkpoint $(git rev-parse --short HEAD) — $MSG"
fi
echo "continuity: no remote publication performed"
