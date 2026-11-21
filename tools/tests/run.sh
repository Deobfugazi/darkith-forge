#!/usr/bin/env bash
# Offline verification for the alert layer. No Gradle, no network, no device.
# Usage: tools/tests/run.sh [<source-root>]
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SRC="$ROOT/app/src/main/java/com/darkith/transliaison/core"
[ $# -ge 1 ] && SRC="$1"
WORK="${TMPDIR:-/tmp}/darkith-alert-verify"
rm -rf "$WORK"; mkdir -p "$WORK"

command -v kotlinc >/dev/null || { echo "kotlinc not on PATH"; exit 2; }

echo "== compiling pure layer =="
kotlinc "$SRC/CommentScan.kt" "$SRC/Alert.kt" "$SRC/Formulary.kt" \
  -d "$WORK/pure" -nowarn 2>"$WORK/pure.log"
if [ $? -ne 0 ]; then echo "COMPILE FAILED"; cat "$WORK/pure.log"; exit 1; fi
echo "   ok"

echo "== compiling tests =="
kotlinc "$HERE/CommentScanTest.kt" -classpath "$WORK/pure" -d "$WORK/t" -nowarn 2>"$WORK/t.log"
if [ $? -ne 0 ]; then echo "TEST COMPILE FAILED"; cat "$WORK/t.log"; exit 1; fi
echo "   ok"

echo "== running tests =="
kotlin -classpath "$WORK/pure:$WORK/t" CommentScanTestKt || exit 1

echo
echo "== scanning the real tree =="
kotlinc "$HERE/ScanTree.kt" -classpath "$WORK/pure" -d "$WORK/s" -nowarn 2>"$WORK/s.log"
if [ $? -ne 0 ]; then echo "SCANNER COMPILE FAILED"; cat "$WORK/s.log"; exit 1; fi
kotlin -classpath "$WORK/pure:$WORK/s" ScanTreeKt "$ROOT/app" || exit 1

echo
echo "ALL CHECKS PASSED"
