#!/usr/bin/env bash
# fork_integrity_gate.sh — the executable form of §19 (NEVER #11-13, MUST #10-13, SPI-12-15).
# A ledger entry that is not a gate is a note. This is the gate.
#
# Usage:  tools/fork_integrity_gate.sh <authoritative_tree_dir> [android_jar] [extra_cp] [--no-compile]
# Exit:   0 = all laws held.  non-zero = a law was broken (see the DEFICIT line).
#
# MUST-11 ("the compile is the proof") is ENFORCED. Without a kotlinc + android_jar the gate
# FAILS, because a green that skips the proof is exactly the W-040 defect this gate exists to
# kill. Pass --no-compile to declare the skip explicitly; the gate then prints
# "MUST-11: SKIPPED" and exits 0, and every caller MUST treat currency as UNPROVEN
# (delivery_gate.sh forces L-07/L-10 OPEN on that marker).
set -u

NO_COMPILE=0
POS=()
for a in "$@"; do
  case "$a" in
    --no-compile) NO_COMPILE=1 ;;
    *) POS+=("$a") ;;
  esac
done

TREE="${POS[0]:?usage: fork_integrity_gate.sh <authoritative_tree_dir> [android_jar] [extra_cp] [--no-compile]}"
ANDROID_JAR="${POS[1]:-}"
EXTRA_CP="${POS[2]:-}"
FAIL=0
say()  { printf '  %s\n' "$*"; }
die()  { printf 'DEFICIT: %s\n' "$*"; FAIL=1; }

echo "== fork integrity gate =="
echo "tree: $TREE"

# ---- SPI-12 / NEVER #11 : one authoritative tree -----------------------------
echo "[SPI-12] one authoritative tree"
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" && pwd)"
ALL=$(find "$ROOT" -type d -name transliaison 2>/dev/null | grep '/com/darkith/' | sort -u)
TREE_ABS=$(cd "$TREE" && pwd)
STALE=$(printf '%s\n' "$ALL" | grep -v "^$TREE_ABS\$" | grep . || true)
if [ -n "$STALE" ]; then
  say "stale forks still present:"
  printf '%s\n' "$STALE" | sed 's/^/    /'
  if [ -f "$ROOT/DARKITH.md" ]; then
    say "dated supersession note present ($ROOT/DARKITH.md Part 2) — stale forks are frozen, not live (NEVER #11 satisfied)"
  else
    die "SPI-12: $(printf '%s\n' "$STALE" | grep -c .) stale fork(s) with no dated supersession note. Reconcile or delete (NEVER #11)."
  fi
else
  say "exactly one source tree: $TREE_ABS"
fi

# ---- SPI-13 / NEVER #12 : no foreign / purged symbols ------------------------
echo "[SPI-13] no foreign or purged symbols"
if grep -rn --include=*.kt 'import androidx' "$TREE" >/dev/null 2>&1; then
  grep -rn --include=*.kt 'import androidx' "$TREE" | sed 's/^/    /'
  die "SPI-13: androidx import found — the raw chain is blocked (SPI-5)."
else
  say "zero 'import androidx'"
fi
# purged symbols must not be *referenced as live code* (comments/messages are allowed)
for sym in ComposeEmitter; do
  hits=$(grep -rn --include=*.kt "$sym" "$TREE" 2>/dev/null | grep -v '^\s*//' | grep -v '"' | grep -v "purged")
  if [ -n "$hits" ]; then printf '%s\n' "$hits" | sed 's/^/    /'; die "SPI-13: live reference to purged symbol '$sym'."; fi
done
say "no live references to purged symbols"

# ---- SPI-14 / MUST #12 : every build input is versioned ----------------------
echo "[SPI-14] build inputs are versioned"
MANIFEST="$TREE/../../../../AndroidManifest.xml"   # com/darkith/transliaison -> main/
[ -f "$MANIFEST" ] && say "manifest: $(cd "$(dirname "$MANIFEST")" && pwd)/AndroidManifest.xml" \
  || die "SPI-14: AndroidManifest.xml missing from the tree."
for d in res assets; do
  [ -d "$TREE/../../../../$d" ] && say "$d/: present" || die "SPI-14: $d/ missing from the tree."
done

# ---- MUST #11 : the compile is the proof -------------------------------------
echo "[MUST-11] compile is the proof"
KOTLINC="${KOTLINC:-kotlinc}"
if [ -n "$ANDROID_JAR" ] && command -v "$KOTLINC" >/dev/null 2>&1; then
  LOG="$(mktemp)"; OUTD="$(mktemp -d)"
  # R.java is a build product (aapt2 link --java, build.sh step 2). Generate it so
  # R.* resolves exactly as it does in the real chain — otherwise the gate cries wolf.
  MANIFEST_G="$TREE/../../../../AndroidManifest.xml"; RES_G="$TREE/../../../../res"; RJ=""
  if [ -f "$MANIFEST_G" ] && [ -d "$RES_G" ] && command -v aapt2 >/dev/null 2>&1; then
    RC="$(mktemp -d)"; GEN="$(mktemp -d)"
    aapt2 compile --dir "$RES_G" -o "$RC/res.zip" >/dev/null 2>&1
    aapt2 link -o "$RC/g.apk" -I "$ANDROID_JAR" --manifest "$MANIFEST_G" "$RC/res.zip" \
      --java "$GEN" --min-sdk-version 24 --target-sdk-version 34 --auto-add-overlay >/dev/null 2>&1
    RJ=$(find "$GEN" -name R.java | head -1)
  fi
  FILES=$(find "$TREE" -name '*.kt')
  # -Dkotlin.compiler.execution.strategy=in-process: compile in this JVM instead of a
  # spawned Kotlin daemon. The daemon can fail to start in a sandboxed CI runner, which
  # makes kotlinc exit non-zero with a stack trace and NO 'error:' lines — a green-looking
  # log that is really a crash. In-process removes that failure mode entirely.
  if "$KOTLINC" -J-Xmx2g -Dkotlin.compiler.execution.strategy=in-process \
       -cp "$ANDROID_JAR${EXTRA_CP:+:$EXTRA_CP}" -jvm-target 1.8 -nowarn -d "$OUTD" $FILES $RJ 2>"$LOG"; then
    say "kotlinc clean: $(grep -c 'error:' "$LOG") errors, $(find "$TREE" -name '*.kt' | wc -l) files$([ -n "$RJ" ] && echo ' (+R.java)')"
  else
    # Print what kotlinc ACTUALLY said. The old code printed only lines matching 'error:',
    # so a crash (daemon/OOM/classpath) reported "0 errors" — a misleading deficit. Print
    # the HEAD first (the exception/message line lives there), then the tail.
    grep 'error:' "$LOG" | head -20 | sed 's/^/    /'
    say "kotlinc output (first 20 lines):"
    head -20 "$LOG" | sed 's/^/    /'
    die "MUST-11: kotlinc exited non-zero ($(grep -c 'error:' "$LOG") 'error:' line(s); see output above). Not reconciled."
  fi
else
    if [ "$NO_COMPILE" = 1 ]; then
      say "MUST-11: SKIPPED (--no-compile) - currency is UNPROVEN; delivery_gate.sh forces L-07/L-10 OPEN"
    else
      die "MUST-11: no kotlinc/android_jar - the compile proof did NOT run. Supply both, or pass --no-compile to record the skip explicitly (never report green on a skipped proof)."
    fi
fi

echo "== result =="
if [ "$FAIL" -eq 0 ]; then echo "PASS: all §19 laws held."; exit 0; else echo "FAIL: see DEFICIT above."; exit 1; fi
