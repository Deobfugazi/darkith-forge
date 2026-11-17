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
  # Kotlin syntax gate: fail if any source tree has an unclosed block comment.
  # A scanner, not kotlinc (W-023), but exact about the defect that silently
  # swallows the rest of a file. Runs only when the app tree is present.
  if [ -d app/src/main/java ]; then
    run "kotlin syntax gate"              python3 tools/syntax_gate.py app/src/main/java
  fi
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

printf '\n=== discrepancy detectors (two tabs must agree) ===\n'
if have git && git rev-parse --git-dir >/dev/null 2>&1; then

  # D-1 uncommitted work: with two tabs, an uncommitted edit is invisible to the
  # other tab and can be lost. Warn loudly (do not fail: CI is runnable pre-commit).
  if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    printf -- '--- working tree clean: WARN (uncommitted edits are invisible to the other tab)\n'
    git status --short | sed 's/^/      /'
  else
    printf -- '--- working tree clean: PASS\n'
  fi

  # D-2 fork singularity (AGENTS.md NEVER #11 / SPI-12, the missing W-040 gate):
  # an authority file that exists at two tracked paths is two live copies. Fail.
  forks="$(git ls-files | awk -F/ '{print $NF}' | sort | uniq -d \
            | grep -E '^(AGENTS\.md|build\.sh|verify\.py)$|\.kt$' || true)"
  if [ -n "$forks" ]; then
    printf -- '--- fork singularity (NEVER #11): FAIL\n'
    for f in $forks; do
      printf '      %s tracked at:\n' "$f"
      git ls-files | grep -E "(^|/)$f\$" | sed 's/^/        /'
    done
    FAILED=1
  else
    printf -- '--- fork singularity (NEVER #11): PASS\n'
  fi

  # D-3 version truth: if the AndroidManifest is versioned (MUST #12), the
  # versionName it declares must be the one AGENTS.md states. A tab that bumps
  # one but not the other is a discrepancy.
  man="$(git ls-files | grep -E '(^|/)AndroidManifest\.xml$' | head -1 || true)"
  if [ -n "$man" ] && [ -f AGENTS.md ]; then
    vn="$(sed -n 's/.*versionName="\([^"]*\)".*/\1/p' "$man" | head -1)"
    if [ -n "$vn" ] && ! grep -qF "$vn" AGENTS.md; then
      printf -- '--- version truth: FAIL (manifest says %s, AGENTS.md does not)\n' "$vn"
      FAILED=1
    else
      printf -- '--- version truth: PASS (%s)\n' "${vn:-n/a}"
    fi
  else
    printf -- '--- version truth: skipped (no tracked AndroidManifest.xml)\n'
  fi

else
  printf -- '--- discrepancy detectors: SKIP (not a git checkout)\n'
fi

printf '\nCI: %s\n' "$([ "$FAILED" -eq 0 ] && echo PASS || echo FAIL)"
exit "$FAILED"


