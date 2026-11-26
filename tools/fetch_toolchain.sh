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

fetch_artifact() {
  local label="$1" dest="$2"; shift 2
  local tmp="${dest}.part"
  rm -f "$tmp"
  for url in "$@"; do
    say "$label: trying mirror ${url%%/maven2/*}"
    if curl -fsSL --retry 5 --retry-all-errors --retry-delay 3 --retry-max-time 90 --connect-timeout 30 --max-time 900 -o "$tmp" "$url" && [ -s "$tmp" ]; then
      mv -f "$tmp" "$dest"
      return 0
    fi
    rm -f "$tmp"
  done
  return 1
}

KOTLIN_VER="1.9.24"
JDK_VER="17.0.12+7"
JDK_DIR="jdk-17.0.12+7"
ANDROID_JAR_NAME="android-all-14-robolectric-10818077.jar"
APKSIG_VER="8.1.1"
AAPT2_VER="8.5.2-11315950"

have_java() { command -v java >/dev/null 2>&1; }

# 1. JDK. The Kotlin compiler launcher is sensitive to the runtime JDK: a mismatched
#    version (or a JRE-only system java) makes kotlinc abort before it prints any 'error:'
#    line — a crash the §19 gate would otherwise read as "0 errors". Pin to Temurin 17 for
#    reproducibility; use a system JDK only when it is already 17.x.
need_jdk=1
if [ -x "$DEST/$JDK_DIR/bin/java" ]; then
  say "jdk: cached $DEST/$JDK_DIR"
  need_jdk=0
elif command -v java >/dev/null 2>&1 && java -version 2>&1 | head -1 | grep -q '"17\.'; then
  say "jdk: using system $(command -v java) ($(java -version 2>&1 | head -1))"
  need_jdk=0
fi
if [ "$need_jdk" = 1 ]; then
  say "jdk: fetching Temurin $JDK_VER (~190 MB)"
  curl -fsSL -o "$DEST/jdk.tar.gz" \
    "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-${JDK_VER//+/%2B}/OpenJDK17U-jdk_x64_linux_hotspot_${JDK_VER//+/_}.tar.gz" \
    || { say "DEFICIT: jdk download failed"; exit 1; }
  tar -xzf "$DEST/jdk.tar.gz" -C "$DEST" && rm -f "$DEST/jdk.tar.gz"
fi
[ -x "$DEST/$JDK_DIR/bin/java" ] && export JAVA_HOME="$DEST/$JDK_DIR"
export PATH="${JAVA_HOME:-}/bin:$PATH"
say "jdk: java -> $(command -v java) ($(java -version 2>&1 | head -1))"

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
  fetch_artifact "android.jar" "$DEST/$ANDROID_JAR_NAME" "https://repo.maven.apache.org/maven2/org/robolectric/android-all/14-robolectric-10818077/${ANDROID_JAR_NAME}" "https://maven-central.storage-download.googleapis.com/maven2/org/robolectric/android-all/14-robolectric-10818077/${ANDROID_JAR_NAME}" "https://repo1.maven.org/maven2/org/robolectric/android-all/14-robolectric-10818077/${ANDROID_JAR_NAME}" || { say "DEFICIT: android.jar download failed from all configured mirrors"; exit 1; }
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

# 5. aapt2 — the resource compiler + linker. The §19 compile proof needs it to generate
#    R.java (aapt2 link --java) before kotlinc runs; without it R.* does not resolve and
#    the proof fails. Shipped as a jar wrapping the linux executable. Placed in aapt2d/
#    so tools/ci.sh can put it on PATH.
if [ -x "$DEST/aapt2d/aapt2" ]; then
  say "aapt2: cached"
else
  say "aapt2: fetching ($AAPT2_VER)"
  mkdir -p "$DEST/aapt2d"
  curl -fsSL -o "$DEST/aapt2.jar" \
    "https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2/${AAPT2_VER}/aapt2-${AAPT2_VER}-linux.jar" \
    || { say "DEFICIT: aapt2 download failed"; exit 1; }
  python3 - "$DEST/aapt2.jar" "$DEST/aapt2d" <<'PY'
import sys, zipfile
zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])
PY
  chmod +x "$DEST/aapt2d/aapt2" 2>/dev/null || true
fi

# 6. zipalign is NOT fetched here: it is not a Maven artifact, and alignment is checked
#    in pure Python by tools/install_gate.py (I-04), so no binary is required.

# Validate
[ -x "$DEST/kotlinc/bin/kotlinc" ] || { say "DEFICIT: kotlinc missing"; exit 1; }
[ -r "$DEST/$ANDROID_JAR_NAME" ]   || { say "DEFICIT: android.jar missing"; exit 1; }
[ -r "$DEST/apksig.jar" ]          || { say "DEFICIT: apksig.jar missing"; exit 1; }
[ -x "$DEST/aapt2d/aapt2" ]        || { say "DEFICIT: aapt2 missing"; exit 1; }

# 7. admission (SPI-40 P2, MUST #41 R1): a fresh machine is admission-controlled by
#    default. The pre-push hook rehearses the REAL suite on the EXACT bytes in an isolated
#    worktree and refuses a known-red push, so the rehearsal law no longer depends on any
#    agent remembering to install it. Bypass once with ADMISSION_BYPASS=1, by design.
if [ -f tools/admission.py ]; then
  if python3 tools/admission.py --install-hook; then
    say "admission: pre-push rehearsal hook installed (SPI-40 P2)"
  else
    say "admission: DEFICIT: hook could not be installed — rehearsal still enforced manually"
  fi
fi

say "toolchain ready in $DEST"
