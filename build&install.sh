#!/usr/bin/env bash
# build&install.sh — DARKITH Forge one-shot: stage toolchain, build the host APK,
# install it. Runs in Termux (arm64) and on any Linux/macOS desktop.
#
# NOTE ON THE NAME: the '&' means an unquoted `bash build&install.sh` is parsed
# by the shell as two jobs. Quote it:
#
#     bash 'build&install.sh'                 # build + install
#     bash 'build&install.sh' --no-install    # build only
#     bash 'build&install.sh' --dir ~/darkith-project
#
# After this installs the host APK once, you never need Termux again: the app
# carries its own aapt2 + zipalign (lib/*.so) and its own engine assets, so
# "aegis://forgetest" in the Forge terminal builds and installs a child APK
# on-device.
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PROJ="${SELF_DIR}"
INSTALL=1
TOOLCHAIN="${DARKITH_TOOLCHAIN:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    --no-install) INSTALL=0 ;;
    --install-only) INSTALL=2 ;;
    --dir) PROJ="$2"; shift ;;
    --toolchain) TOOLCHAIN="$2"; shift ;;
    -h|--help)
      sed -n '2,20p' "${BASH_SOURCE[0]:-$0}"; exit 0 ;;
    *) printf 'unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

say(){ printf '\033[1;36m[*]\033[0m %s\n' "$*"; }
ok(){  printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die(){ printf '\033[1;31m[FATAL]\033[0m %s\n' "$*" >&2; exit 1; }

# ── 0. where are we? ─────────────────────────────────────────────────────────
IS_TERMUX=0
case "${PREFIX:-}" in */com.termux/files/usr) IS_TERMUX=1 ;; esac
if [ "$IS_TERMUX" = 0 ] && [ -d /data/data/com.termux/files/usr ]; then
  IS_TERMUX=1; PREFIX=/data/data/com.termux/files/usr
fi
PREFIX="${PREFIX:-/usr/local}"
[ "$IS_TERMUX" = 1 ] && say "environment: Termux ($PREFIX)" || say "environment: desktop"

# ── 1. locate the project (holds app/src/main/AndroidManifest.xml) ───────────
find_project(){
  local d
  for d in "$PROJ" "$PROJ/app" "$HOME/darkith-project" "$HOME/darkith-forge"; do
    [ -f "$d/app/src/main/AndroidManifest.xml" ] && { printf '%s' "$d"; return 0; }
    [ -f "$d/AndroidManifest.xml" ] && { printf '%s' "$d"; return 0; }
  done
  return 1
}
PROJ="$(find_project || true)"
[ -n "$PROJ" ] || die "no Android project found. Unzip the source tree and pass --dir <dir>."
say "project: $PROJ"

# ── 2. toolchain ─────────────────────────────────────────────────────────────
# Termux: install what the store ships; zipalign has no package, build.sh falls
# back to the bundled pure-Python zipalign.py.
if [ "$IS_TERMUX" = 1 ]; then
  missing=""
  for t in aapt2 apksigner kotlinc java python3; do
    command -v "$t" >/dev/null 2>&1 || missing="$missing $t"
  done
  if [ -n "$missing" ]; then
    say "installing Termux packages:$missing"
    pkg install -y aapt2 apksigner d8 kotlin openjdk-17 python unzip zip >/dev/null 2>&1 \
      || pkg install -y aapt2 apksigner d8 kotlin openjdk-21 python unzip zip >/dev/null 2>&1 \
      || warn "pkg install had trouble; continuing and checking tools"
  fi
fi

# d8: Termux package, or the R8 jar, or Android build-tools.
D8_BIN="$(command -v d8 2>/dev/null || true)"
R8_JAR="${R8_JAR:-}"
if [ -z "$D8_BIN" ] && [ -z "$R8_JAR" ]; then
  for c in "$SELF_DIR/libs/r8.jar" "$PROJ/libs/r8.jar" "$HOME/.darkith/toolchain/r8.jar" /tmp/r8.jar; do
    [ -r "$c" ] && { R8_JAR="$c"; break; }
  done
fi

# android.jar — the ONE locked input. Prefer a staged copy, then the app's own
# engine asset (which the host APK ships), then download platform-34.
ANDROID_JAR="${ANDROID_JAR:-}"
if [ -z "$ANDROID_JAR" ]; then
  for c in "$PROJ/app/src/main/assets/engine/android.jar" \
           "$PROJ/assets/engine/android.jar" \
           "${TOOLCHAIN:-}/android.jar" "$HOME/.darkith/toolchain/android.jar" \
           /tmp/darkith-toolchain/android.jar; do
    [ -r "$c" ] && { ANDROID_JAR="$c"; break; }
  done
fi
if [ -z "$ANDROID_JAR" ]; then
  TC="${TOOLCHAIN:-$HOME/.darkith/toolchain}"
  mkdir -p "$TC"
  say "fetching android.jar (API 34) -> $TC"
  curl -fsSL --retry 3 -o "$TC/platform34.zip" \
    "https://dl.google.com/android/repository/platform-34-ext7_r03.zip" \
    || die "could not download android.jar; set ANDROID_JAR=/path/to/android.jar"
  python3 -c "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); [z.extract(n,sys.argv[2]) for n in z.namelist() if n.endswith('android.jar')]" \
    "$TC/platform34.zip" "$TC"
  ANDROID_JAR="$(find "$TC" -name android.jar | head -1)"
  rm -f "$TC/platform34.zip"
fi
[ -r "$ANDROID_JAR" ] || die "android.jar not found"
say "android.jar: $ANDROID_JAR"

# apksig jar (ApkSignerRunner imports com.android.apksig) -> app/libs
if [ ! -f "$PROJ/app/libs/apksig-8.5.2.jar" ] && [ ! -f "$PROJ/app/libs/apksig.jar" ]; then
  mkdir -p "$PROJ/app/libs"
  if [ -r "${TOOLCHAIN:-}/apksig.jar" ]; then
    cp "${TOOLCHAIN}/apksig.jar" "$PROJ/app/libs/apksig-8.5.2.jar"
  elif [ -r /tmp/darkith-toolchain/apksig.jar ]; then
    cp /tmp/darkith-toolchain/apksig.jar "$PROJ/app/libs/apksig-8.5.2.jar"
  else
    say "fetching apksig.jar"
    curl -fsSL --retry 3 -o "$PROJ/app/libs/apksig-8.5.2.jar" \
      "https://dl.google.com/dl/android/maven2/com/android/tools/build/apksig/8.5.2/apksig-8.5.2.jar" \
      || warn "could not fetch apksig; on-device signing will need it"
  fi
fi

export ANDROID_JAR
[ -n "$D8_BIN" ] && say "d8: $D8_BIN"
[ -n "$R8_JAR" ] && { say "r8.jar: $R8_JAR"; export R8_JAR; }

# ── 3. build ─────────────────────────────────────────────────────────────────
OUT="${OUT:-$PROJ/app-signed.apk}"
if [ "$INSTALL" = 2 ]; then
  say "install-only requested; skipping build"
else
  BUILDER=""
  for c in "$PROJ/build.sh" "$SELF_DIR/build.sh" "$PROJ/delivery/build.sh"; do
    [ -r "$c" ] && { BUILDER="$c"; break; }
  done
  [ -n "$BUILDER" ] || die "build.sh not found next to the project"
  say "building with $BUILDER"
  OUT="$OUT" bash "$BUILDER" "$PROJ" "Darkith Homekeeper" com.darkith.transliaison
fi
[ -f "$OUT" ] || die "no APK at $OUT"

# ── 3b. re-sign with the app's own release identity when it is present ────────
# build.sh signs with a throwaway debug key, which is fine for a fresh device but
# will NOT install over an app already signed with the Darkith Release identity
# (INSTALL_FAILED_UPDATE_INCOMPATIBLE). The identity ships INSIDE the host APK as
# assets/engine/{release_key,release_cert}; when those are on disk, reuse them so
# the result is an upgrade-installable release APK.
REL_SIGNED=0
for eng in "$PROJ/app/src/main/assets/engine" "$PROJ/assets/engine"; do
  [ -f "$eng/release_key" ] && [ -f "$eng/release_cert" ] || continue
  command -v apksigner >/dev/null 2>&1 || break
  command -v openssl   >/dev/null 2>&1 || break
  tmp="$(mktemp -d)"
  # release_key is PKCS#8 DER, release_cert is X.509 DER: openssl pkcs12 wants PEM.
  if openssl pkey -inform DER -in "$eng/release_key" -out "$tmp/key.pem" >/dev/null 2>&1 \
     && openssl x509 -inform DER -in "$eng/release_cert" -outform PEM -out "$tmp/cert.pem" >/dev/null 2>&1 \
     && openssl pkcs12 -export -inkey "$tmp/key.pem" -in "$tmp/cert.pem" \
          -name darkith -out "$tmp/rel.p12" -passout pass:darkith >/dev/null 2>&1; then
    if apksigner sign --ks "$tmp/rel.p12" --ks-key-alias darkith \
          --ks-pass pass:darkith --key-pass pass:darkith \
          --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
          --out "$tmp/religned.apk" "$OUT" >/dev/null 2>&1; then
      mv "$tmp/religned.apk" "$OUT"; REL_SIGNED=1
      say "re-signed with the Darkith Release identity (upgrade-installable)"
    fi
  fi
  rm -rf "$tmp"
  break
done
[ "$REL_SIGNED" = 0 ] && warn "release identity not found beside the tree; APK carries the debug signature"

APK_SHA="$(sha256sum "$OUT" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "$OUT" | cut -d' ' -f1)"
ok "APK: $OUT"
ok "size: $(wc -c < "$OUT") B   sha256: $APK_SHA"

# ── 4. install ───────────────────────────────────────────────────────────────
if [ "$INSTALL" = 0 ]; then
  say "--no-install: stopping after the build"
  exit 0
fi

install_via_adb(){
  command -v adb >/dev/null 2>&1 || return 1
  adb get-state >/dev/null 2>&1 || return 1
  say "installing over adb"
  adb install -r -d "$OUT"
}
install_via_package_installer(){
  # Trigger the system package installer for the APK. Works when the file is in
  # shared storage and an activity-manager entry point is reachable.
  local dst="/sdcard/Download/DarkithHomekeeper.apk"
  if [ -d /sdcard/Download ]; then
    cp -f "$OUT" "$dst" || return 1
    say "copied to $dst"
  else
    dst="$OUT"
  fi
  if command -v termux-open >/dev/null 2>&1; then
    say "opening the package installer (termux-open)"
    termux-open --content-type application/vnd.android.package-archive "$dst"
    return 0
  fi
  if command -v am >/dev/null 2>&1; then
    say "opening the package installer (am start)"
    am start -a android.intent.action.VIEW -d "file://$dst" \
      -t application/vnd.android.package-archive >/dev/null 2>&1 && return 0
  fi
  warn "install it by tapping: $dst"
  return 0
}

if install_via_adb; then
  ok "installed via adb"
elif install_via_package_installer; then
  ok "package installer launched — confirm the install on screen"
else
  warn "could not auto-install. The APK is at: $OUT"
fi

echo
echo "DONE"
echo "  apk    : $OUT"
echo "  sha256 : $APK_SHA"
echo
echo "Termux is no longer required. Open the app, then in the Forge terminal run:"
echo "  aegis://forgetest     # builds + installs a child APK entirely on-device"
