#!/usr/bin/env bash
# DARKITH ONE-SHOT — build + install the native Android host. No Gradle.
set -euo pipefail
MODE="${1:---install}"
case "$MODE" in --build|--no-install) MODE="build";; --verify) MODE="verify";; --install|"") MODE="install";; *) echo "Usage: bash build&install.sh [--build|--verify|--install]" >&2; exit 2;; esac
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
[ -f build.sh ] || { echo "build.sh missing"; exit 1; }

if [ -n "${PREFIX:-}" ] && [ "$(uname -o 2>/dev/null || true)" = "Android" ]; then
  bash tools/setup_termux_toolchain.sh
  # shellcheck disable=SC1091
  source "$ROOT/.tools/termux.env"
else
  bash tools/fetch_toolchain.sh
  [ -x "$ROOT/.tools/jdk-17.0.12+7/bin/java" ] && export JAVA_HOME="$ROOT/.tools/jdk-17.0.12+7"
  [ -x "$ROOT/.tools/kotlinc/bin/kotlinc" ] && export KOTLINC="$ROOT/.tools/kotlinc/bin/kotlinc"
  for jar in "$ROOT"/.tools/android*.jar "$ROOT"/.tools/android.jar; do [ -r "$jar" ] && export ANDROID_JAR="$jar"; done
  [ -r "$ROOT/.tools/r8.jar" ] && export R8_JAR="$ROOT/.tools/r8.jar"
  export PATH="${JAVA_HOME:-/nonexistent}/bin:$ROOT/.tools:$PATH"
fi

if [ -x tools/stage_engine_inputs.sh ]; then
  bash tools/stage_engine_inputs.sh || echo "Engine input staging skipped; host build continues."
fi

echo "Running the raw seven-step build; Gradle is not invoked."
bash build.sh "$ROOT" "Darkith" "com.darkith.transliaison"
APK="$ROOT/app-signed.apk"
[ -s "$APK" ] || { echo "No signed APK produced"; exit 1; }
echo "APK: $APK ($(wc -c < "$APK") bytes)"

if [ "$MODE" = "install" ]; then
  if command -v termux-open >/dev/null 2>&1; then
    termux-open --content-type application/vnd.android.package-archive "$APK"
    echo "Android package installer opened; user confirmation is required."
  else
    echo "APK built. Open it manually: $APK"
  fi
else
  echo "Mode $MODE: build complete; APK left at $APK"
fi
