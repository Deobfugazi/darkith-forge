#!/usr/bin/env bash
# fetch_toolchain.sh — provision the NT IX raw-chain compilers into .tools/ (gitignored).
#
# "The compile is the proof" (MUST-11). CI cannot honestly report green on a §19 gate that
# skipped the compile, so it must have a real kotlinc + android.jar. This script fetches the
# exact tools the raw chain uses (no Gradle, SPI-1) and caches them in .tools/, which
# .gitignore already excludes. It is idempotent: a cached tool is never re-downloaded.
#
# After it runs, `tools/ci.sh` finds KOTLINC / ANDROID_JAR / EXTRA_CP in .tools/ and runs the
# real compile proof. If a JDK is already on PATH (GitHub's ubuntu runner, or Termux), the
# JDK download is skipped.
#
# Usage:  bash tools/fetch_toolchain.sh
# Exit:   0 = toolchain present in .tools/.  non-zero = could not provision.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/.tools"
mkdir -p "$DEST"
say() { printf '  %s\n' "$*"; }

KOTLIN_VER="1.9.24"
JDK_VER="17.0.12+7"
JDK_DIR="jdk-17.0.12+7"
ANDROID_JAR_NAME="android-all-14-robolectric-10818077.jar"
APKSIG_VER="8.1.1"

have_java() { command -v java >/dev/null 2>&1; }

# 1. JDK (only if none on PATH and none already fetched)
if have_java; then
  say "jdk: using $(command -v java)"
elif [ -x "$DEST/$JDK_DIR/bin/java" ]; then
  say "jdk: cached $DEST/$JDK_DIR"
else
  say "jdk: fetching Temurin $JDK_VER (~190 MB)"
  curl -fsSL -o "$DEST/jdk.tar.gz" \
    "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-${JDK_VER//+/%2B}/OpenJDK17U-jdk_x64_linux_hotspot_${JDK_VER//+/_}.tar.gz" \
    || { say "DEFICIT: jdk download failed"; exit 1; }
  tar -xzf "$DEST/jdk.tar.gz" -C "$DEST" && rm -f "$DEST/jdk.tar.gz"
fi
[ -x "$DEST/$JDK_DIR/bin/java" ] && export JAVA_HOME="$DEST/$JDK_DIR"
export PATH="${JAVA_HOME:-}/bin:$PATH"

# 2. kotlinc
if [ -x "$DEST/kotlinc/bin/kotlinc" ]; then
  say "kotlinc: cached"
else
  say "kotlinc: fetching $KOTLIN_VER (~91 MB)"
  curl -fsSL -o "$DEST/kotlinc.zip" \
    "https://github.com/JetBrains/kotlin/releases/download/v${KOTLIN_VER}/kotlin-compiler-${KOTLIN_VER}.zip" \
    || { say "DEFICIT: kotlinc download failed"; exit 1; }
  python3 - "$DEST/kotlinc.zip" "$DEST" <<'PY'
import sys, zipfile
zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])
PY
  rm -f "$DEST/kotlinc.zip"
  chmod +x "$DEST"/kotlinc/bin/* 2>/dev/null || true
fi

# 3. android.jar (API 34 platform stubs, Robolectric build)
if [ -r "$DEST/$ANDROID_JAR_NAME" ]; then
  say "android.jar: cached"
else
  say "android.jar: fetching ($ANDROID_JAR_NAME, ~137 MB)"
  curl -fsSL -o "$DEST/$ANDROID_JAR_NAME" \
    "https://repo1.maven.org/maven2/org/robolectric/android-all/14-robolectric-10818077/${ANDROID_JAR_NAME}" \
    || { say "DEFICIT: android.jar download failed"; exit 1; }
fi

# 4. apksig.jar (the signer the tree imports)
if [ -r "$DEST/apksig.jar" ]; then
  say "apksig.jar: cached"
else
  say "apksig.jar: fetching $APKSIG_VER"
  curl -fsSL -o "$DEST/apksig.jar" \
    "https://dl.google.com/dl/android/maven2/com/android/tools/build/apksig/${APKSIG_VER}/apksig-${APKSIG_VER}.jar" \
    || { say "DEFICIT: apksig.jar download failed"; exit 1; }
fi

# Validate
[ -x "$DEST/kotlinc/bin/kotlinc" ] || { say "DEFICIT: kotlinc missing"; exit 1; }
[ -r "$DEST/$ANDROID_JAR_NAME" ]   || { say "DEFICIT: android.jar missing"; exit 1; }
[ -r "$DEST/apksig.jar" ]          || { say "DEFICIT: apksig.jar missing"; exit 1; }
say "toolchain ready in $DEST"
