#!/usr/bin/env bash
# ARM64 Termux toolchain for Darkith's raw seven-step build. No Gradle; no x86 Linux binaries.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/.tools"
ENV_FILE="$TOOLS/termux.env"
mkdir -p "$TOOLS"

[ -n "${PREFIX:-}" ] && [ "$(uname -o 2>/dev/null || true)" = "Android" ] || {
  echo "This provisioner is for Termux on Android. Use tools/fetch_toolchain.sh on Linux." >&2
  exit 2
}
[ "$(uname -m)" = "aarch64" ] || {
  echo "Unsupported device architecture: $(uname -m). This profile is pinned to ARM64." >&2
  exit 2
}
command -v pkg >/dev/null 2>&1 || { echo "Termux pkg command not found." >&2; exit 2; }

# These are native Termux packages. Never run Google's glibc aapt2/apksigner binaries on Android.
pkg update -y
pkg install -y openjdk-21 aapt2 apksigner zipalign python curl unzip git termux-tools

JAVA_BIN="$(command -v java)"
JAVA_HOME_REAL="$(dirname "$(dirname "$(readlink -f "$JAVA_BIN")")")"
export JAVA_HOME="$JAVA_HOME_REAL"
export PATH="$JAVA_HOME/bin:$PREFIX/bin:$PATH"

if [ ! -x "$TOOLS/kotlinc/bin/kotlinc" ]; then
  echo "Fetching portable Kotlin compiler 1.9.24..."
  curl -fL --retry 3 -o "$TOOLS/kotlin-compiler.zip" \
    "https://github.com/JetBrains/kotlin/releases/download/v1.9.24/kotlin-compiler-1.9.24.zip"
  unzip -oq "$TOOLS/kotlin-compiler.zip" -d "$TOOLS"
  rm -f "$TOOLS/kotlin-compiler.zip"
fi

if [ ! -s "$TOOLS/android.jar" ]; then
  echo "Fetching API 34 Android framework stubs..."
  curl -fL --retry 3 -o "$TOOLS/android.jar" \
    "https://repo.maven.apache.org/maven2/org/robolectric/android-all/14-robolectric-10818077/android-all-14-robolectric-10818077.jar"
fi

if [ ! -s "$TOOLS/r8.jar" ]; then
  echo "Fetching D8/R8 Java tool..."
  curl -fL --retry 3 -o "$TOOLS/r8.jar" \
    "https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.1.56/r8-8.1.56.jar"
fi

KOTLINC="$TOOLS/kotlinc/bin/kotlinc"
AAPT2="$(command -v aapt2)"
APKSIGNER="$(command -v apksigner)"
ZIPALIGN="$(command -v zipalign)"
PY3="$(command -v python3)"
for item in "$KOTLINC" "$AAPT2" "$APKSIGNER" "$ZIPALIGN" "$PY3" "$TOOLS/android.jar" "$TOOLS/r8.jar"; do
  [ -e "$item" ] || { echo "Missing required toolchain item: $item" >&2; exit 1; }
done
"$AAPT2" version >/dev/null
"$APKSIGNER" --version >/dev/null
"$ZIPALIGN" -h >/dev/null 2>&1 || true
"$KOTLINC" -version >/dev/null 2>&1

cat > "$ENV_FILE" <<EOF
export JAVA_HOME="$JAVA_HOME"
export PATH="$JAVA_HOME/bin:$PREFIX/bin:\$PATH"
export KOTLINC="$KOTLINC"
export AAPT2="$AAPT2"
export APKSIGNER="$APKSIGNER"
export ZIPALIGN="$ZIPALIGN"
export ANDROID_JAR="$TOOLS/android.jar"
export R8_JAR="$TOOLS/r8.jar"
export PY3="$PY3"
export KOTLINC_XMX="512m"
EOF
echo "ARM64 Termux raw toolchain ready: $ENV_FILE"
