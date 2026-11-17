#!/usr/bin/env bash
# ci.sh — the repository's tests, in ONE provider-neutral place.
#
# This file is the source of truth for "do the tests pass". It knows nothing about
# GitHub, GitLab, Bitbucket, Jenkins or any other CI vendor: it runs the suites and
# exits 0 only if every one passes. Any CI system (or a phone in Termux) can call it:
#
#     bash tools/ci.sh
#
# A vendor's YAML (e.g. .github/workflows/*.yml) must stay a thin adapter that calls
# this script — never a second copy of the logic. Copying the logic into a vendor file
# is what makes a repo a hostage to one provider; this script is what makes it portable.
#
# Exit status: 0 = every check passed, non-zero = at least one failed.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 2

FAILED=0
run() {
  local name="$1"; shift
  printf '\n=== %s ===\n' "$name"
  if "$@"; then
    printf -- '--- %s: PASS\n' "$name"
  else
    printf -- '--- %s: FAIL (exit %s)\n' "$name" "$?"
    FAILED=1
  fi
}

# Each suite is skipped only when its runtime is genuinely absent, and a skip is
# announced loudly — a silent skip is how a broken tree ships looking green.
have() { command -v "$1" >/dev/null 2>&1; }

if have python3; then
  run "repo gate (build/verify.py --fast)" python3 build/verify.py --fast
  run "savf cli contract"                 python3 build/savf-cli-test.py
  run "darkbot self-test"                 python3 tools/darkbot.py selftest
else
  echo "SKIP: python3 not found"; FAILED=1
fi

if have node; then
  run "omega engine harness" node build/omega/omega-test.mjs
else
  echo "SKIP: node not found"; FAILED=1
fi

# Browser UI test needs playwright; run it only if importable, so a slim environment
# skips it honestly instead of reporting a false failure.
if have python3 && python3 -c 'import playwright' >/dev/null 2>&1; then
  run "omega headless ui" python3 build/omega/ui-test.py
else
  echo "SKIP: playwright not installed (python3 -m pip install -r requirements-dev.txt)"
fi

# Byte-security invariant: signing key material must never be tracked in git.
# This is the one check that must run even with no runtime installed, so it is
# plain git + grep and is never skipped.
printf '\n=== no signing material tracked ===\n'
if have git && git rev-parse --git-dir >/dev/null 2>&1; then
  hits="$(git ls-files | grep -Ei '(^|/)(release_key|release_cert)$|\.(keystore|jks|p12|pfx|pem|key)$' || true)"
  if [ -n "$hits" ]; then
    printf -- '--- no signing material tracked: FAIL\n%s\n' "$hits"
    FAILED=1
  else
    printf -- '--- no signing material tracked: PASS\n'
  fi
else
  echo "SKIP: not a git checkout"
fi

printf '\nCI: %s\n' "$([ "$FAILED" -eq 0 ] && echo PASS || echo FAIL)"
exit "$FAILED"
