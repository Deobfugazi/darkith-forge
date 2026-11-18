#!/usr/bin/env bash
# rebuild_template_dex.sh — regenerate assets/engine/template.dex from the tracked sources.
#
# template.dex is the child's classes.dex: the host app reads it at runtime and stamps it into
# every forged child (ChimeraBuilder.forgeChimera step 5). It is a build product of
# app/src/main/java, so when the sources change it MUST be rebuilt — otherwise the forge ships
# a stale engine. (The committed copy had gone stale: it was missing NativeTools.kt.)
#
# This is the same chain build.sh runs (kotlinc -> d8), reduced to just the dex the forge needs.
# Gradle-free (SPI-1). It reuses the .tools/ toolchain staged by tools/fetch_toolchain.sh.
#
# Usage:  bash tools/rebuild_template_dex.sh
# Exit:   0 = template.dex regenerated.  non-zero = a tool is missing (it names which).
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/app/src/main/java"
MANIFEST="$ROOT/app/src/main/AndroidManifest.xml"
RES="$ROOT/app/src/main/res"
OUT="$ROOT/app/src/main/assets/engine/template.dex"
MIN_SDK="${MIN_SDK:-24}"
say() { printf '  %s\n' "$*"; }
die() { printf 'DEFICIT: %s\n' "$*" >&2; exit 1; }

find_tool() {  # name [.tools/relative-candidates...]
  local n="$1"; shift
  command -v "$n" 2>/dev/null && return 0
  for c in "$@"; do [ -x "$c" ] && { echo "$c"; return 0; }; done
  return 1
}

JAVA="$(command -v java || echo "$ROOT/.tools/jdk-17.0.12+7/bin/java")"
[ -x "$JAVA" ] || die "no java (install a JDK, or run tools/fetch_toolchain.sh)"
JAVA_HOME="$(dirname "$(dirname "$JAVA")")"; export JAVA_HOME
KOTLINC="$(find_tool kotlinc "$ROOT/.tools/kotlinc/bin/kotlinc")" || die "no kotlinc (run tools/fetch_toolchain.sh)"
AAPT2="$(find_tool aapt2 "$ROOT/.tools/aapt2d/aapt2")" || die "no aapt2 (run tools/fetch_toolchain.sh)"
ANDROID_JAR=""
for c in "${ANDROID_JAR:-}" "$ROOT/.tools/android-all-14-robolectric-10818077.jar" "$ROOT/.tools/android.jar"; do
  [ -r "$c" ] && { ANDROID_JAR="$c"; break; }
done
[ -n "$ANDROID_JAR" ] || die "no android.jar (run tools/fetch_toolchain.sh)"
R8_JAR=""
for c in "${R8_JAR:-}" "$ROOT/.tools/r8.jar" "$ROOT/.tools/r8-"*.jar; do
  [ -r "$c" ] && { R8_JAR="$c"; break; }
done
[ -n "$R8_JAR" ] || die "no r8.jar (needed for d8; run tools/fetch_toolchain.sh)"
APKSIG="$ROOT/.tools/apksig.jar"

W="$ROOT/.forge_work"; rm -rf "$W"; mkdir -p "$W/gen" "$W/classes" "$W/dex"

# R.java (build.sh step 2) — the app's resource ids.
if [ -d "$RES" ] && [ -f "$MANIFEST" ]; then
  "$AAPT2" compile --dir "$RES" -o "$W/res.zip" >/dev/null 2>&1 || die "aapt2 compile failed"
  "$AAPT2" link -o "$W/gen.apk" -I "$ANDROID_JAR" --manifest "$MANIFEST" "$W/res.zip" --java "$W/gen" >/dev/null 2>&1 \
    || die "aapt2 link failed"
fi
RJ="$(find "$W/gen" -name R.java 2>/dev/null | head -1)"
CP="$ANDROID_JAR"; [ -n "$APKSIG" ] && CP="$CP:$APKSIG"

say "kotlinc: compiling $SRC"
"$KOTLINC" "$SRC" ${RJ:+"$RJ"} -classpath "$CP" -J-Xmx1500m -d "$W/classes" -nowarn 2>"$W/kotlinc.log" \
  || { grep -E 'error:' "$W/kotlinc.log" | head -20; die "kotlinc failed (see $W/kotlinc.log)"; }
[ -n "$(ls -A "$W/classes" 2>/dev/null)" ] || die "kotlinc produced no classes"
say "kotlinc: ok ($(find "$W/classes" -name '*.class' | wc -l) classes)"

mapfile -t CLASSES < <(find "$W/classes" -name '*.class')
"$JAVA" -cp "$R8_JAR" com.android.tools.r8.D8 --min-api "$MIN_SDK" --lib "$ANDROID_JAR" --output "$W/dex" "${CLASSES[@]}" \
  || die "d8 failed"
[ -f "$W/dex/classes.dex" ] || die "d8 produced no classes.dex"

cp "$W/dex/classes.dex" "$OUT"
rm -rf "$W"
say "template.dex: ok -> ${OUT#$ROOT/} ($(du -h "$OUT" | cut -f1))"
say "verify: python3 tools/forge_child_gate.py"
