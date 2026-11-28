#!/usr/bin/env bash
# Replace the Homekeeper asset with the pinned uploaded source, build with Darkith's raw chain,
# verify the packaged bytes, copy the APK to Downloads, and open Android's package installer.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v termux-setup-storage >/dev/null 2>&1; then
  pkg install -y termux-tools
fi
if { [ ! -d "$HOME/storage/downloads" ] || [ ! -r "$HOME/storage/downloads" ] || [ ! -w "$HOME/storage/downloads" ]; } && command -v termux-setup-storage >/dev/null 2>&1; then
  termux-setup-storage
fi
DOWNLOAD_DIR="$HOME/storage/downloads"
if [ ! -d "$DOWNLOAD_DIR" ] || [ ! -r "$DOWNLOAD_DIR" ] || [ ! -w "$DOWNLOAD_DIR" ]; then
  DOWNLOAD_DIR="/sdcard/Download"
fi
[ -d "$DOWNLOAD_DIR" ] && [ -r "$DOWNLOAD_DIR" ] && [ -w "$DOWNLOAD_DIR" ] || {
  echo "Shared Downloads storage is unavailable. Grant Termux storage permission and rerun." >&2
  exit 1
}
SOURCE="${1:-$DOWNLOAD_DIR/homekeeper(2).html}"
SPEC="${2:-$DOWNLOAD_DIR/DARKITH-KEYBOARD-SINGULAR-INVARIANT(1).md}"
SPEC_SHA256="75c0058a83d71ad8593dadd0f4f0003448cc3cfbfb0558e2754e13efad91c4b2"
EXPECTED_SHA256="1482e152c1ff2d8bdf97cd52684c98f7224d58713b0b8735f902878aebb3405d"
ASSET="$ROOT/app/src/main/assets/homekeeper.html"
DEST_DIR="$DOWNLOAD_DIR"
DEST_APK="$DEST_DIR/Darkith-Homekeeper-OMEGA.apk"
PKG="com.darkith.transliaison"

die(){ echo "STOP: $*" >&2; exit 1; }
[ -f "$ROOT/build.sh" ] || die "Run this script from the Darkith Forge repository root."
[ -f "$ROOT/app/src/main/AndroidManifest.xml" ] || die "Native Android manifest is missing."
[ -f "$SOURCE" ] || die "Source HTML not found: $SOURCE"
[ -f "$SPEC" ] || die "Keyboard invariant source not found: $SPEC"
[ "$(sha256sum "$SPEC" | awk '{print $1}')" = "$SPEC_SHA256" ] || die "Keyboard invariant source SHA-256 mismatch."
[ -f "$ROOT/app/src/main/java/com/darkith/transliaison/HomekeeperBridge.kt" ] || die "Homekeeper native bridge source is missing."
grep -q 'addJavascriptInterface(HomekeeperBridge' "$ROOT/app/src/main/java/com/darkith/transliaison/HomekeeperActivity.kt" || die "HomekeeperActivity does not inject the native bridge."
grep -q 'OMEGA-BRIDGEDIAG' "$SOURCE" || die "Uploaded HTML lacks the bridge diagnostic block."
ACTUAL_SHA256="$(sha256sum "$SOURCE" | awk '{print $1}')"
[ "$ACTUAL_SHA256" = "$EXPECTED_SHA256" ] || die "Source SHA-256 mismatch. Expected $EXPECTED_SHA256, got $ACTUAL_SHA256. Refusing an unverified source."

BACKUP_DIR="${HOME}/.darkith-backups"
mkdir -p "$BACKUP_DIR"
if [ -f "$ASSET" ]; then
  cp "$ASSET" "$BACKUP_DIR/homekeeper.html.$(date +%Y%m%d-%H%M%S).bak"
fi
cp "$SOURCE" "$ASSET"
[ "$(sha256sum "$ASSET" | awk '{print $1}')" = "$EXPECTED_SHA256" ] || die "Copied asset does not match the pinned source."
echo "SOURCE SHA-256: $EXPECTED_SHA256"
echo "SOURCE BYTES:   $(wc -c < "$ASSET" | tr -d ' ')"

# Provision the correct ARM64-native toolchain. Do not call fetch_toolchain.sh here:
# its JDK and aapt2 downloads are x86_64 GNU/Linux binaries, not Android/ARM64 binaries.
bash "$ROOT/tools/setup_termux_toolchain.sh"
[ -f "$ROOT/.tools/termux.env" ] || die "Termux toolchain did not emit its environment file."
# shellcheck disable=SC1091
source "$ROOT/.tools/termux.env"

# Admit the keyboard invariant into the canonical KB and run the NT/citation witnesses.
bash "$ROOT/tools/admit_keyboard_spec.sh" "$SPEC"

mkdir -p "$ROOT/delivery" "$DEST_DIR"
APK="$ROOT/delivery/Darkith-Homekeeper-OMEGA.apk"
echo "BUILD: raw seven-step chain (aapt2 -> kotlinc -> D8 -> package -> zipalign -> sign)"
OUT="$APK" bash "$ROOT/build.sh" "$ROOT" "Darkith" "com.darkith.transliaison"
[ -s "$APK" ] || die "Raw build completed without an APK."

python3 - "$APK" "$ASSET" <<'PY'
import hashlib, sys, zipfile
apk, source = sys.argv[1:]
expected = open(source, "rb").read()
with zipfile.ZipFile(apk) as z:
    packed = z.read("assets/homekeeper.html")
if packed != expected:
    raise SystemExit("APK asset mismatch: packaged homekeeper.html is not byte-identical to the pinned source")
print("APK ASSET CHECK: PASS (byte-identical)")
print("APK ASSET SHA-256:", hashlib.sha256(packed).hexdigest())
PY

"$APKSIGNER" verify --verbose "$APK"

# Never uninstall an existing app or ask Android to replace it with a different signer.
if command -v pm >/dev/null 2>&1; then
  EXISTING_LINE="$(pm path "$PKG" 2>/dev/null | head -n 1 || true)"
  EXISTING_APK="${EXISTING_LINE#package:}"
  if [ -n "$EXISTING_APK" ] && [ -r "$EXISTING_APK" ]; then
    EXISTING_CERT="$("$APKSIGNER" verify --print-certs "$EXISTING_APK" 2>/dev/null | sed -n 's/.*Signer #1 certificate SHA-256 digest: //p' | head -n 1)"
    NEW_CERT="$("$APKSIGNER" verify --print-certs "$APK" 2>/dev/null | sed -n 's/.*Signer #1 certificate SHA-256 digest: //p' | head -n 1)"
    if [ -n "$EXISTING_CERT" ] && [ -n "$NEW_CERT" ] && [ "$EXISTING_CERT" != "$NEW_CERT" ]; then
      die "Installed $PKG has a different signing certificate. Refusing an update or uninstall; preserve the original keystore or plan a separate data-safe migration."
    fi
  fi
fi

cp "$APK" "$DEST_APK"
echo "APK SHA-256: $(sha256sum "$DEST_APK" | awk '{print $1}')"
echo "APK SIZE:    $(wc -c < "$DEST_APK" | tr -d ' ') bytes"
echo "APK READY:   $DEST_APK"

if command -v termux-open >/dev/null 2>&1; then
  echo "Opening Android package installer. Confirm the install on the phone."
  termux-open --content-type application/vnd.android.package-archive "$DEST_APK"
else
  echo "Package installer was not opened automatically."
  echo "Open this file in Android Files and confirm installation: $DEST_APK"
  echo "If Android blocks it, allow Termux to install unknown apps, then retry."
fi
