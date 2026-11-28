#!/usr/bin/env bash
# Replace the Homekeeper asset with the pinned uploaded source, build with Darkith's raw chain,
# verify the packaged bytes, copy the APK to Downloads, and open Android's package installer.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${1:-/sdcard/Download/homekeeper(2).html}"
EXPECTED_SHA256="1482e152c1ff2d8bdf97cd52684c98f7224d58713b0b8735f902878aebb3405d"
ASSET="$ROOT/app/src/main/assets/homekeeper.html"
DEST_DIR="/sdcard/Download"
DEST_APK="$DEST_DIR/Darkith-Homekeeper-OMEGA.apk"

die(){ echo "STOP: $*" >&2; exit 1; }
[ -f "$ROOT/build.sh" ] || die "Run this script from the Darkith Forge repository root."
[ -f "$ROOT/app/src/main/AndroidManifest.xml" ] || die "Native Android manifest is missing."
[ -f "$SOURCE" ] || die "Source HTML not found: $SOURCE"
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
