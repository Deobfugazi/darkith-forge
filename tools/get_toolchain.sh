#!/usr/bin/env bash
# get_toolchain.sh — stage the compile toolchain so MUST-11 is a REAL proof, not a skip.
#
# Fetches, into $DEST (default /tmp/darkith-toolchain), exactly the inputs the raw
# chain needs to compile the app tree:
#   android.jar  the Android 14 (API 34) platform reference classes
#   apksig.jar   the build dependency ApkSignerRunner.kt imports (com.android.apksig)
#   aapt2        the resource compiler + linker (generates R.java)
#   kotlinc      the Kotlin compiler
# Then prints the env to source. Nothing is committed; this is CI/desktop staging only.
#
#   . tools/get_toolchain.sh          # fetch (idempotent) and export the vars
#   bash tools/get_toolchain.sh       # fetch only; prints the export lines
#
# Idempotent and offline-safe: if a component is already staged it is left alone.
# If a download fails, the vars are simply not exported and the s19 gate reports a
# SKIP (never a false green) — see build/s19_compile.py.
set -u

DEST="${DEST:-/tmp/darkith-toolchain}"
mkdir -p "$DEST"
say() { printf '[toolchain] %s\n' "$*"; }

ANDROID_JAR="$DEST/android.jar"
APKSIG_JAR="$DEST/apksig.jar"
AAPT2_BIN="$DEST/aapt2"
KOTLINC_BIN="$DEST/kotlinc/bin/kotlinc"

fetch() { # fetch <url> <dest> <label>
  [ -s "$2" ] && { say "$3 already staged"; return 0; }
  say "fetching $3"
  curl -fsSL --retry 3 --retry-delay 2 -o "$2.part" "$1" && mv "$2.part" "$2" \
    || { say "WARN: could not fetch $3 ($1)"; rm -f "$2.part"; return 1; }
}

# android.jar — public mirror of the API 34 platform classes (NOT an SDK install).
fetch "https://github.com/Sable/android-platforms/raw/master/android-34/android.jar" \
      "$ANDROID_JAR" "android.jar (API 34)"
# apksig — the exact coordinate the project's own RESUME.md documents.
fetch "https://dl.google.com/dl/android/maven2/com/android/tools/build/apksig/8.1.1/apksig-8.1.1.jar" \
      "$APKSIG_JAR" "apksig.jar"
# aapt2 — Google's build-tools binary for linux (jar wrapping the executable).
if [ ! -x "$AAPT2_BIN" ]; then
  if fetch "https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2/8.5.2-11315950/aapt2-8.5.2-11315950-linux.jar" "$DEST/aapt2.jar" "aapt2"; then
    python3 -c "import zipfile,sys; zipfile.ZipFile('$DEST/aapt2.jar').extractall('$DEST/aapt2x')" 2>/dev/null
    [ -f "$DEST/aapt2x/aapt2" ] && cp "$DEST/aapt2x/aapt2" "$AAPT2_BIN" && chmod +x "$AAPT2_BIN"
  fi
fi
# kotlinc — the Kotlin compiler (needs a JDK on PATH).
if [ ! -x "$KOTLINC_BIN" ]; then
  if fetch "https://github.com/JetBrains/kotlin/releases/download/v2.0.21/kotlin-compiler-2.0.21.zip" "$DEST/kotlin.zip" "kotlinc"; then
    python3 -c "import zipfile; zipfile.ZipFile('$DEST/kotlin.zip').extractall('$DEST')" 2>/dev/null
    chmod +x "$DEST/kotlinc/bin/"* 2>/dev/null
  fi
fi

[ -s "$ANDROID_JAR" ] && export ANDROID_JAR
[ -s "$APKSIG_JAR" ] && export EXTRA_CP="$APKSIG_JAR"
[ -x "$AAPT2_BIN" ] && export AAPT2="$AAPT2_BIN"
[ -x "$KOTLINC_BIN" ] && export KOTLINC="$KOTLINC_BIN"

say "ANDROID_JAR=${ANDROID_JAR:-<absent>}"
say "EXTRA_CP=${EXTRA_CP:-<absent>}"
say "AAPT2=${AAPT2:-<absent>}"
say "KOTLINC=${KOTLINC:-<absent>}"
