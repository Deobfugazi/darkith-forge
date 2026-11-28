#!/data/data/com.termux/files/usr/bin/bash
# Replace Homekeeper's packaged page, build through NT IX's raw chain, and verify bytes.
# Default is RELEASE: never silently generate a new debug identity for an update APK.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="${1:-${HOMEKEEPER_SRC:-}}"
if [ -z "$SRC" ]; then
  for candidate in "/sdcard/Download/homekeeper(2).html" "/sdcard/Download/homekeeper.html"; do
    if [ -f "$candidate" ]; then SRC="$candidate"; break; fi
  done
fi
DEST="$ROOT/app/src/main/assets/homekeeper.html"
ACT="$ROOT/app/src/main/java/com/darkith/transliaison/HomekeeperActivity.kt"
SIGNING_MODE="${SIGNING_MODE:-release}"

[ -f "$ROOT/build.sh" ] || { echo "FAIL: raw build.sh missing at $ROOT" >&2; exit 1; }
[ -f "$ROOT/app/src/main/AndroidManifest.xml" ] || { echo "FAIL: Android manifest missing" >&2; exit 1; }
[ -f "$SRC" ] || { echo "FAIL: source page not found: $SRC" >&2; exit 1; }
[ -f "$ACT" ] || { echo "FAIL: HomekeeperActivity missing" >&2; exit 1; }
grep -q 'addJavascriptInterface(HomekeeperBridge' "$ACT" || {
  echo "FAIL: HomekeeperBridge is not injected by HomekeeperActivity" >&2; exit 1;
}

mkdir -p /sdcard/Darkith/backups
BACKUP="/sdcard/Darkith/backups/homekeeper.$(date +%Y%m%d_%H%M%S).html"
cp -f "$DEST" "$BACKUP"
COMMITTED=0
restore_source(){
  if [ "$COMMITTED" -ne 1 ] && [ -f "$BACKUP" ]; then cp -f "$BACKUP" "$DEST"; fi
}
trap restore_source EXIT

cp -f "$SRC" "$DEST"
# A page without the repository's version-of-record stamp is not an admissible source.
python3 "$ROOT/tools/update_gate.py"
python3 "$ROOT/tools/bridge_contract_audit.py" "$DEST" "$ROOT/app/src/main/java/com/darkith/transliaison/HomekeeperBridge.kt"
python3 "$ROOT/tools/device_runtime_contract_gate.py"

# The seven NT IX stages produce a signed APK. Release mode requires the original key
# and expected certificate; debug is permitted only when explicitly requested.
SIGNING_MODE="$SIGNING_MODE" OUT="$ROOT/app-signed.apk" bash "$ROOT/build.sh" "$ROOT" "Darkith" "com.darkith.transliaison"
APK="$ROOT/app-signed.apk"
unzip -p "$APK" assets/homekeeper.html | cmp - "$SRC"
aapt2 dump badging "$APK" | head -1
apksigner verify --verbose --print-certs "$APK"
cp -f "$APK" /sdcard/Download/Homekeeper_OMEGA.apk
sha256sum "$APK"
COMMITTED=1
echo "BUILD VERIFIED. APK: /sdcard/Download/Homekeeper_OMEGA.apk"
echo "NOT DEVICE-ACCEPTED: install/update and lifecycle gates must still run on the TECNO target."
echo "Do not uninstall the existing app to bypass a signing mismatch."
