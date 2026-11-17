#!/usr/bin/env bash
# DARKITH ONE-SHOT — build + install the Keeper Forge host APK. Termux, no Gradle.
#
#   bash build&install.sh              provision, build, install
#   bash build&install.sh --build      build only (leave the APK on disk)
#   bash build&install.sh --verify     provision + build, install nothing
#   bash build&install.sh --no-install alias for --build
#
# SPI-1: the raw 7-step chain only (aapt2 -> kotlinc -> d8 -> zip -> zipalign ->
# apksigner). Gradle is never invoked. Run this from the project root in Termux; the
# built APK also builds the same tree on-device from the app's own forge terminal.
set -uo pipefail

MODE="install"
case "${1:-}" in
  --build|--no-install) MODE="build"  ;;
  --verify)             MODE="verify" ;;
  --install|"")         MODE="install" ;;
  *) printf 'unknown flag: %s\n' "$1" >&2; exit 2 ;;
esac

say(){ printf '  %s\n' "$*"; }
die(){ printf 'DEFICITS: {(%s, "%s")}\n' "${1:-M0}" "${2:-failed}" >&2; exit 1; }

SELF="${BASH_SOURCE[0]:-$0}"
ROOT="$(cd "$(dirname "$SELF")" && pwd)"
cd "$ROOT" || die M0 "cannot enter $ROOT"
[ -f build.sh ] || die M0 "build.sh not found in $ROOT (run from the project root)"

# ── 1. provision the raw chain (idempotent; cached under .tools/) ───────────────
if [ -x tools/fetch_toolchain.sh ]; then
  say "toolchain: provisioning (cached under .tools/)"
  bash tools/fetch_toolchain.sh || die M2 "toolchain provisioning failed"
  [ -d .tools/jdk ] && export JAVA_HOME="${JAVA_HOME:-$ROOT/.tools/jdk}"
  [ -x .tools/kotlinc/bin/kotlinc ] && export KOTLINC="$ROOT/.tools/kotlinc/bin/kotlinc"
  for j in "$ROOT"/.tools/android*.jar "$ROOT"/.tools/android.jar; do [ -r "$j" ] && export ANDROID_JAR="$j"; done
  export PATH="$JAVA_HOME/bin:$ROOT/.tools:$PATH"
else
  say "toolchain: tools/fetch_toolchain.sh absent — using PATH tools"
fi

# ── 2. stage the child-forge engine inputs (android.jar + signing pair) ─────────
if [ -x tools/stage_engine_inputs.sh ]; then
  say "engine: staging child-forge inputs into assets/engine"
  bash tools/stage_engine_inputs.sh || say "engine: staging skipped (non-fatal)"
fi

# ── 3. build with the raw 7-step chain ──────────────────────────────────────────
say "build: running the 7-step raw chain"
bash build.sh . Darkith com.darkith.transliaison || die M3 "build failed"
APK="$ROOT/app-signed.apk"
[ -f "$APK" ] || die M3 "no APK produced at $APK"
say "build: $(wc -c <"$APK") B -> $APK"

# ── 4. install (skipped for --build/--verify) ───────────────────────────────────
if [ "$MODE" = "install" ]; then
  if command -v termux-open >/dev/null 2>&1; then
    termux-open --content-type application/vnd.android.package-archive "$APK" \
      || die M4 "termux-open failed"
    say "install: handed to the package installer — confirm the prompt"
  elif command -v pm >/dev/null 2>&1; then
    pm install -r "$APK" || die M4 "pm install failed"
    say "install: installed via pm"
  else
    say "install: no termux-open/pm — APK left at $APK"
    say "         open it from the app's forge terminal, or: termux-open $APK"
  fi
else
  say "mode=$MODE: APK left at $APK"
fi

say "done. The forge terminal inside the app can now build on-device."
exit 0
