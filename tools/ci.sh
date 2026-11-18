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
  # Fracture Scout: offline proof its boolean parser, adapters, and ranker are correct.
  run "fracture scout self-test"          python3 tools/fracture_scout.py selftest
  # Kotlin syntax gate: fail if any source tree has an unclosed block comment.
  # A scanner, not kotlinc (W-023), but exact about the defect that silently
  # swallows the rest of a file. Runs only when the app tree is present.
  if [ -d app/src/main/java ]; then
    run "kotlin syntax gate"              python3 tools/syntax_gate.py app/src/main/java
    # API-level gate: a high-API call with no SDK_INT guard crashes the launcher on
    # older devices before the UI paints. Static, but exact about that defect.
    if [ -f tools/api_level_gate.py ]; then
      run "API-level gate"                python3 tools/api_level_gate.py app/src/main/java
    fi
    # Icon gate: a manifest with no android:icon ships a blank launcher tile.
    if [ -f tools/icon_gate.py ]; then
      run "icon gate"                     python3 tools/icon_gate.py
    fi
    # Board gate: the durable board must exist and every done item must carry evidence.
    if [ -f tools/board_gate.py ]; then
      run "board gate"                    python3 tools/board_gate.py
    fi
    # Law gate: SPI-15 — a law that is not an executable gate is a note. Enforces the
    # prime directive (DARKITH.md §30) and that every declared NEVER/MUST/SPI names a
    # gate that exists, or is explicitly marked as not-yet-gated.
    if [ -f tools/law_gate.py ]; then
      run "law gate (SPI-15/prime)"       python3 tools/law_gate.py
    fi
    # MUST #15 / #16 / NEVER #17 / §31 synchrony — the laws that were only notes until now.
    for g in circadian_gate download_gate stall_gate synchrony_gate synchrony_pulse convergence_gate; do
      if [ -f "tools/$g.py" ]; then
        run "$g"                          python3 "tools/$g.py"
      fi
    done
      # NT gate: run the noveltreatise corpus through SAVF and fail unless every
      # contradiction (claim kind C) is resolved to absolution by a re-run command.
      # A law cited but not carried, or a contradiction left unresolved, stops CI.
      if [ -f tools/nt_gate.py ]; then
        run "nt corpus reconciliation (SAVF)" python3 tools/nt_gate.py
      fi
      # NT XI progress-deficit indicator: the retention law W_in - E = S != 0 read off
      # the durable board + deficit ledger. Fails if the board's printed indicator is stale,
      # or if the ratio rose across a delivery with no new descope (M6 non-extractive).
      if [ -f tools/omega_deficit.py ]; then
        run "omega deficit (NT XI retention)" python3 tools/omega_deficit.py
      fi
    # the board must be pushed in REAL TIME so a parallel worker sees it (MUST #26)
    if [ -f tools/board_pulse.sh ]; then
      run "board pulse (real-time push)"    bash tools/board_pulse.sh --check
    fi
  fi
else
  echo "SKIP: python3 not found"; FAILED=1
fi

# The NT IX raw-chain gates. These are the laws that were "notes, not gates" (SPI-15):
# they existed but nothing invoked them. A gate that is never run is a note, so CI runs them.
# The §19 gate (fork_integrity_gate.sh) ENFORCES the compile proof (MUST-11); to keep CI
# honest it is given a real toolchain from .tools/ when one is present, and it FAILS (not
# skips) when there is none. The APK-dependent loopholes are deferred explicitly via
# --source-only, which is a named SKIP, never a silent pass.
if [ -d app/src/main/java ] && [ -f tools/fork_integrity_gate.sh ]; then
  TOOLCHAIN="$ROOT/.tools"
  if [ -x "$TOOLCHAIN/kotlinc/bin/kotlinc" ]; then
    export KOTLINC="$TOOLCHAIN/kotlinc/bin/kotlinc"
    export ANDROID_JAR="$TOOLCHAIN/android-all-14-robolectric-10818077.jar"
    export EXTRA_CP="$TOOLCHAIN/apksig.jar"
    [ -x "$TOOLCHAIN/jdk-17.0.12+7/bin/java" ] && export JAVA_HOME="$TOOLCHAIN/jdk-17.0.12+7"
    # aapt2 (R.java for the compile proof) and zipalign live in aapt2d/; put them on PATH
    # so both the §19 proof and the install gate find real tools on a fresh runner.
    export PATH="$TOOLCHAIN/aapt2d:${JAVA_HOME:+$JAVA_HOME/bin:}$PATH"
    run "§19 fork integrity gate (compile proof)" \
      bash tools/fork_integrity_gate.sh app/src/main/java/com/darkith/transliaison "$ANDROID_JAR" "$EXTRA_CP"
  else
    echo "SKIP: no toolchain in .tools/ (run: bash tools/fetch_toolchain.sh) — §19 compile proof NOT run"
    echo "      (the §19 gate itself fails closed without it; this line only records the local skip)"
    FAILED=1
  fi

  run "delivery gate (source laws)" \
    bash tools/delivery_gate.sh . --source-only
  run "bridge contract audit" \
    python3 tools/bridge_contract_audit.py "darkith home forge.html" app/src/main/java/com/darkith/transliaison/HomekeeperBridge.kt
  run "doc consolidation check" \
    bash tools/consolidate_docs.sh --check
fi

if have python3 && [ -f tools/doc_path_gate.py ]; then
  run "doc path gate" python3 tools/doc_path_gate.py
fi

if have python3 && [ -f tools/kb_index.py ]; then
  # Universal index of the readable knowledge-skill base (SPI-15). Fails if the index is
  # stale, if a readable file is unfiled, if two files share a hash without a declared
  # mirror, or if a declared mirror has drifted (NEVER #11 / #15 / #16, §22).
  run "knowledge-base index + dedup" python3 tools/kb_index.py
fi

if have node && [ -f tools/test_darktools.js ]; then
  run "darktools unit tests" node tools/test_darktools.js
fi

# The inscriber studio: boots in jsdom, engines present, terminal + toolkits live. Needs
# jsdom (an npm dev dep, not always installed), so it is skipped honestly when absent.
if have node && [ -f tools/test_inscriber.js ]; then
  if node -e 'require("jsdom")' >/dev/null 2>&1; then
    run "inscriber studio tests" node tools/test_inscriber.js
  else
    echo "SKIP: jsdom not installed (npm install jsdom) — inscriber studio test NOT run"
  fi
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

printf '\n=== APK store rule (SPI-21 repack law) ===\n'
apks="$(ls delivery/*.apk 2>/dev/null || true)"
if have python3 && [ -n "$apks" ]; then
  # resources.arsc and lib/*.so MUST be STORED; DEFLATED means API 30+ install
  # fails with a bare "App not installed". delivery/ is regenerable output and
  # not committed, so an absent APK is a skip, never a failure. Check EVERY APK:
  # the defect is systemic (both shipped APKs had it), not a one-file accident.
  for apk in $apks; do
    if python3 - "$apk" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
bad = [n for n in z.namelist()
       if (n == "resources.arsc" or n.endswith(".so")) and z.getinfo(n).compress_type != 0]
if bad:
    print("      " + sys.argv[1] + " DEFLATED (must be STORED): " + ", ".join(bad)); sys.exit(1)
print("      ok: " + sys.argv[1] + " (arsc + lib/*.so STORED)")
PY
    then printf -- '--- APK store rule: PASS (%s)\n' "$apk"
    else printf -- '--- APK store rule: FAIL (%s)\n' "$apk"; FAILED=1; fi
  done
else
  printf -- '--- APK store rule: skipped (no delivery/*.apk)\n'
fi

printf '\n=== install gate (no "App not installed") ===\n'
# The two failures a user actually feels are (1) the package installer refusing the APK
# and (2) the UI not painting once the OS launches it. Both are gated explicitly. The
# install gate needs aapt2 (manifest) + apksigner (signature); absent them it is a named
# SKIP, never a false pass. zipalign is optional (I-04 is N/A without it).
if have python3 && command -v aapt2 >/dev/null 2>&1 && command -v apksigner >/dev/null 2>&1; then
  gate_apks="$apks"
  [ -f app-signed.apk ] && gate_apks="$gate_apks app-signed.apk"
  if [ -n "${gate_apks// /}" ]; then
    for apk in $gate_apks; do
      run "install gate ($apk)" python3 tools/install_gate.py "$apk" .
    done
  else
    printf -- '--- install gate: skipped (no APK to check)\n'
  fi
else
  printf -- '--- install gate: SKIP (no APK, or aapt2/apksigner absent; build an APK and stage tools with: bash tools/fetch_toolchain.sh)\n'
fi

printf '\n=== runtime render gate (the UI the OS hands to Zygote) ===\n'
# Loads the real launcher asset at 360x800 with and without the native bridge and fails on
# any console/page error, blank body, empty DOM, or overflow. Self-skips (exit 0) when
# playwright is absent, so a slim environment is honest, not red.
if have python3; then
  run "runtime render gate" python3 tools/runtime_gate.py
else
  printf -- '--- runtime render gate: SKIP (no python3)\n'
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

  # D-2 fork singularity (AGENTS.md NEVER #11 / SPI-12, the missing W-040 gate).
  # NEVER #11 forbids two *divergent* live copies. A basename at more than one tracked path
  # is only a violation when the copies DIFFER; byte-identical copies are mirrors, and this
  # gate keeps them honest by failing the moment one drifts. (The old gate used a hardcoded
  # name list, so it never saw `darkith forge.html` vs `darkith home forge.html`, nor
  # `darkith_ui.html` vs `darkith-inscriber.html`.)
  if ! python3 - <<'PYGATE'
import hashlib, subprocess, sys, collections
files = subprocess.run(["git","ls-files","-z"], capture_output=True, text=True).stdout.split("\0")[:-1]
by = collections.defaultdict(list)
for f in files:
    # EXEMPT Android resource-qualifier dirs: the SAME basename in different
    # buckets (mipmap-mdpi vs mipmap-hdpi, values vs values-night) is REQUIRED
    # to differ — that is what the qualifier means. A false positive here trains
    # people to ignore the gate.
    if "/res/" in f:
        continue
    by[f.rsplit("/",1)[-1]].append(f)
divergent, mirrors = {}, {}
for name, paths in sorted(by.items()):
    if len(paths) < 2:
        continue
    hashes = {}
    for pth in paths:
        try:
            hashes[pth] = hashlib.sha256(open(pth,"rb").read()).hexdigest()
        except OSError:
            hashes[pth] = "?"
    (divergent if len(set(hashes.values())) > 1 else mirrors)[name] = hashes if len(set(hashes.values()))>1 else paths
for name, paths in mirrors.items():
    print(f"      mirror (identical): {name} at {', '.join(paths)}")
if divergent:
    print("--- fork singularity (NEVER #11): FAIL (divergent copies)")
    for name, hashes in divergent.items():
        print(f"      {name} tracked at {len(hashes)} paths with DIFFERENT bytes:")
        for pth, h in hashes.items():
            print(f"        {h[:12]}  {pth}")
    sys.exit(1)
print("--- fork singularity (NEVER #11): PASS (no divergent copies)")
PYGATE
  then FAILED=1; fi

  # D-2b explicit mirror pairs: one surface under two names by design. They must stay
  # byte-identical — drift is a fork (NEVER #11) even though the basenames differ, which the
  # basename-based D-2 above cannot see. The app ships assets/darkith_ui.html; the repo-root
  # studio is the same page for browser use, and tools/test_inscriber.js drives the studio.
  for pair in "app/src/main/assets/darkith_ui.html:darkith-inscriber.html"; do
    a="${pair%%:*}"; b="${pair##*:}"
    if [ -f "$a" ] && [ -f "$b" ]; then
      if cmp -s "$a" "$b"; then
        printf -- '--- mirror pair identical: %s == %s\n' "$a" "$b"
      else
        printf -- '--- mirror pair DRIFT (NEVER #11): %s != %s\n' "$a" "$b"
        FAILED=1
      fi
    fi
  done

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

# ── the one-shot installer: the Operator's single build+install entrypoint ──────
# It must exist, be tracked, carry a payload that matches the tree, and contain the
# native toolchain libs the on-device forge execs. Without this check the one-shot
# can silently vanish again (it did: it was referenced by three packagers and absent).
if have python3 && [ -f build/make-oneshot.py ]; then
  if python3 build/make-oneshot.py --check >/tmp/oneshot_check.$$ 2>&1; then
    printf -- '--- one-shot installer: PASS (%s)\n' "$(tail -1 /tmp/oneshot_check.$$ | sed 's/^ *//')"
  else
    printf -- '--- one-shot installer: FAIL (payload stale or missing)\n'
    cat /tmp/oneshot_check.$$ | sed 's/^/    /'
    FAILED=1
  fi
  rm -f /tmp/oneshot_check.$$
fi

# The Operator's one-shot entrypoint (build&install.sh) must exist, be valid bash,
# invoke the raw chain (never Gradle: SPI-1), and be reachable. It is the "drop
# Termux" surface; it has silently gone missing before, so it is gated.
if [ -f 'build&install.sh' ]; then
  if bash -n 'build&install.sh' 2>/dev/null && grep -q 'build.sh' 'build&install.sh' \
     && ! grep -Eq '^\s*gradle|gradlew|gradle\.bat' 'build&install.sh'; then
    printf -- '--- build&install.sh entrypoint: PASS (valid, Gradle-free)\n'
  else
    printf -- '--- build&install.sh entrypoint: FAIL (syntax error or Gradle reference)\n'
    FAILED=1
  fi
else
  printf -- '--- build&install.sh entrypoint: FAIL (missing — the one-shot is the deliverable)\n'
  FAILED=1
fi

printf '\nCI: %s\n' "$([ "$FAILED" -eq 0 ] && echo PASS || echo FAIL)"
exit "$FAILED"


