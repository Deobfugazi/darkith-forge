#!/usr/bin/env bash
# delivery_gate.sh — the enforceable answer to "you keep delivering without knowing your own loopholes".
#
# Every loophole this project has EVER been bitten by is a NAMED check below. The gate refuses to
# print DELIVERED while any check is open. A loophole with no check is a reopened loophole (SPI-15).
#
# Usage:
#   tools/delivery_gate.sh <project_root> [apk_path] [android_jar] [extra_cp]
# Exit 0 = DELIVERED (every loophole closed or explicitly named). Non-zero = at least one open.
#
# This file IS the loophole registry. Adding a new failure without adding a check here is a defect.
set -u

ROOT="."
APK=""; ANDROID_JAR="${ANDROID_JAR:-}"; EXTRA_CP="${EXTRA_CP:-}"; STATIC=0
while [ $# -gt 0 ]; do
  case "$1" in
    --static) STATIC=1 ;;
    *) if [ "$ROOT" = "." ] && [ -e "$1" ]; then ROOT="$1"
       elif [ -z "$APK" ]; then APK="$1"
       elif [ -z "$ANDROID_JAR" ]; then ANDROID_JAR="$1"
       elif [ -z "$EXTRA_CP" ]; then EXTRA_CP="$1"; fi ;;
  esac
  shift
done
KOTLINC="${KOTLINC:-kotlinc}"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"

OPEN=0
# absolute APK path: several checks cd into other dirs, so a relative path would break
if [ -n "$APK" ] && [ -e "$APK" ]; then APK="$(cd "$(dirname "$APK")" && pwd)/$(basename "$APK")"; fi
declare -a NAME STATUS NOTE
rec() { NAME+=("$1"); STATUS+=("$2"); NOTE+=("$3"); [ "$2" = "OPEN" ] && OPEN=$((OPEN+1)); return 0; }
# recapk: an APK/artifact-dependent check. Under --static those cannot be evaluated
# (no artifact is built in a source-only run), so they are recorded N/A — never a
# green they did not earn, and never a failure for a check that never ran.
recapk() { if [ "$STATIC" = 1 ]; then rec "$1" N/A "$3 (needs an artifact; none in this run)"; else rec "$1" "$2" "$3"; fi; }

MANIFEST=$(find "$ROOT" -maxdepth 5 -name AndroidManifest.xml -not -path '*/build/*' 2>/dev/null | head -1)
# the authoritative tree is the superset: the transliaison dir with the most .kt files
SRC=""
for d in $(find "$ROOT" -type d -name transliaison 2>/dev/null | grep '/com/darkith/'); do
  n=$(find "$d" -name '*.kt' 2>/dev/null | wc -l)
  [ "$n" -gt "${SRC_N:-0}" ] && { SRC="$d"; SRC_N="$n"; }
done

echo "== DELIVERY GATE — loophole registry =="
echo "root: $ROOT   apk: ${APK:-<none>}"
echo

# L-01 version declared in the manifest (the thing that was unknowable)
if [ -n "$MANIFEST" ] && grep -q 'android:versionCode' "$MANIFEST" && grep -q 'android:versionName' "$MANIFEST"; then
  rec L-01-manifest-version CLOSED "$(grep -o 'versionName="[^"]*"' "$MANIFEST" | head -1)"
else rec L-01-manifest-version OPEN "no versionCode/versionName in manifest"; fi

# L-02 the APK's real version matches the manifest (badging is the truth)
if [ -n "$APK" ] && [ -f "$APK" ] && command -v aapt >/dev/null 2>&1; then
  MV=$(grep -o 'versionName="[^"]*"' "$MANIFEST" | head -1 | cut -d'"' -f2)
  AV=$(aapt dump badging "$APK" 2>/dev/null | grep -o "versionName='[^']*'" | head -1 | cut -d"'" -f2)
  if [ -n "$AV" ] && [ "$AV" = "$MV" ]; then recapk L-02-apk-version CLOSED "apk=$AV == manifest=$MV"
  else recapk L-02-apk-version OPEN "apk='$AV' != manifest='$MV'"; fi
else recapk L-02-apk-version OPEN "no apk or no aapt (cannot prove version)"; fi

# L-03 the app can report its own installed version at runtime
if [ -n "$SRC" ] && grep -rq 'fun apkVersion' "$SRC" && grep -rq 'const val VERSION' "$SRC"; then
  rec L-03-self-report CLOSED "$(grep -rho 'VERSION = "[^"]*"' "$SRC" | head -1)"
else rec L-03-self-report OPEN "no apkVersion()/VERSION in source"; fi

# L-04 an artifact was actually produced (not just source)
if [ -n "$APK" ] && [ -s "$APK" ]; then recapk L-04-artifact-built CLOSED "$(stat -c%s "$APK") bytes"
else recapk L-04-artifact-built OPEN "no APK built"; fi

# L-05 the artifact is signed and verifies
if [ -n "$APK" ] && [ -f "$APK" ] && command -v apksigner >/dev/null 2>&1; then
  if apksigner verify "$APK" >/dev/null 2>&1; then recapk L-05-artifact-signed CLOSED "apksigner verify ok"
  else recapk L-05-artifact-signed OPEN "apksigner verify FAILED"; fi
else recapk L-05-artifact-signed OPEN "no apk or no apksigner"; fi

# L-06 the artifact is zip-aligned
if [ -n "$APK" ] && [ -f "$APK" ] && command -v zipalign >/dev/null 2>&1; then
  if zipalign -c 4 "$APK" >/dev/null 2>&1; then recapk L-06-artifact-aligned CLOSED "4-byte aligned"
  else recapk L-06-artifact-aligned OPEN "not 4-byte aligned"; fi
else recapk L-06-artifact-aligned OPEN "no apk or no zipalign"; fi

# L-07 one authoritative tree + no androidx/foreign symbols (the §19 gate).
# The §19 gate is run ONCE here; L-10 reuses the same result (one compiler, one truth).
L19LOG=/tmp/l19.$$; L19_PASS=0
if [ -n "$SRC" ] && [ -f "$SELF_DIR/fork_integrity_gate.sh" ] \
   && bash "$SELF_DIR/fork_integrity_gate.sh" "$SRC" "$ANDROID_JAR" "$EXTRA_CP" >"$L19LOG" 2>&1 \
   && grep -q 'PASS: all' "$L19LOG"; then
  L19_PASS=1; rec L-07-fork-singularity CLOSED "§19 gate PASS"
else rec L-07-fork-singularity OPEN "$(grep -m1 DEFICIT "$L19LOG" 2>/dev/null | sed 's/^ *//' || echo 'no source tree or no §19 gate')"; fi

# L-08 the UI<->bridge contract is complete (no phantom calls)
UI=$(find "$ROOT" -maxdepth 4 -name '*.html' 2>/dev/null | grep -iE 'home forge|homekeeper' | head -1)
BR=$(find "$SRC" -name HomekeeperBridge.kt 2>/dev/null | head -1)
if [ -n "$UI" ] && [ -n "$BR" ] && [ -f "$SELF_DIR/bridge_contract_audit.py" ]; then
  if python3 "$SELF_DIR/bridge_contract_audit.py" "$UI" "$BR" 2>/dev/null | grep -q 'MISSING (UI needs, bridge lacks) -> NONE'; then
    rec L-08-bridge-contract CLOSED "0 missing"
  else rec L-08-bridge-contract OPEN "bridge contract has missing methods"; fi
else rec L-08-bridge-contract OPEN "no UI/bridge/tool to audit"; fi

# L-09 every tree asset ships inside the APK (no orphaned assets)
if [ -n "$APK" ] && [ -f "$APK" ] && [ -d "$(dirname "$MANIFEST")/assets" ] && command -v aapt >/dev/null 2>&1; then
  MISSING=$(cd "$(dirname "$MANIFEST")" && find assets -type f | while read -r f; do aapt list "$APK" 2>/dev/null | grep -q "^$f\$" || echo "$f"; done)
  if [ -z "$MISSING" ]; then recapk L-09-asset-parity CLOSED "all assets present"
  else recapk L-09-asset-parity OPEN "not in apk: $(printf '%s ' $MISSING)"; fi
else recapk L-09-asset-parity OPEN "no apk/manifest/assets/aapt"; fi

# L-10 the tree compiles clean (currency is proven, not asserted) — same §19 result.
if [ "$L19_PASS" = 1 ]; then
  rec L-10-currency CLOSED "$(grep -m1 'kotlinc clean' "$L19LOG" | sed 's/^ *//')"
elif [ -n "$ANDROID_JAR" ]; then
  rec L-10-currency OPEN "$(grep -m1 -E 'DEFICIT' "$L19LOG" 2>/dev/null | sed 's/^ *//' || echo 'compile not clean')"
else rec L-10-currency OPEN "no android_jar/kotlinc (cannot prove currency)"; fi
rm -f "$L19LOG"

# L-17 native-tools: handcoded binaries ship in lib/<abi>/ AND the OS is told to extract them
if [ -n "$APK" ] && [ -s "$APK" ]; then
  if python3 -c "
import zipfile,sys
z=zipfile.ZipFile('$APK'); names=z.namelist()
libs=[n for n in names if n.startswith('lib/') and n.endswith('.so')]
sys.exit(0 if (any('libaapt2.so' in n for n in libs) and any('libzipalign.so' in n for n in libs)) else 1)
" 2>/dev/null; then
    if aapt2 dump xmltree --file AndroidManifest.xml "$APK" 2>/dev/null | grep -q 'extractNativeLibs(0x010104ea)=true'; then
      recapk L-17-native-tools CLOSED "lib/*/libaapt2.so+libzipalign.so shipped; extractNativeLibs=true"
    else recapk L-17-native-tools OPEN "native libs shipped but extractNativeLibs!=true -> nativeLibraryDir stays empty"; fi
  else recapk L-17-native-tools OPEN "handcoded binaries absent from lib/<abi>/ (forge cannot exec them)"; fi
else recapk L-17-native-tools OPEN "no APK to inspect"; fi

# L-16 arsc-stored: resources.arsc must be STORED (uncompressed) or Android 11+ refuses install
if [ -n "$APK" ] && [ -s "$APK" ]; then
  if python3 -c "import zipfile,sys; z=zipfile.ZipFile('$APK'); i=z.getinfo('resources.arsc'); sys.exit(0 if i.compress_type==0 else 1)" 2>/dev/null; then
    recapk L-16-arsc-stored CLOSED "resources.arsc uncompressed (API30+ installable)"
  else recapk L-16-arsc-stored OPEN "resources.arsc is DEFLATED -> INSTALL_PARSE_FAILED (App not installed)"; fi
else recapk L-16-arsc-stored OPEN "no APK to inspect"; fi

# L-15 signer-identity: signer-coupled nanosecond-nonce signature present in the dex
if [ -n "$APK" ] && [ -s "$APK" ]; then
  if python3 -c "import zipfile,sys; d=zipfile.ZipFile('$APK').read('classes.dex'); sys.exit(0 if (b'signerSignature' in d and b'HmacSHA256' in d) else 1)"; then
    recapk L-15-signer-identity CLOSED "signerSignature+verifySignerSignature (HMAC-SHA256, ns nonce) in dex"
  else recapk L-15-signer-identity OPEN "signer identity API missing from dex"; fi
else recapk L-15-signer-identity OPEN "no APK to inspect"; fi

# L-14 family-whole: every member of the shell* family must be present IN THE DEX (MUST #20/SPI-19)
if [ -n "$APK" ] && [ -s "$APK" ]; then
  DEXOK=1; MISSF=""
  for m in shell shellExec shellSetCwd shellSetEnv shellEnv shellHistory; do
    if ! python3 -c "import zipfile,sys; d=zipfile.ZipFile('$APK').read('classes.dex'); sys.exit(0 if b'$m' in d else 1)"; then
      DEXOK=0; MISSF="$MISSF $m"
    fi
  done
  if [ "$DEXOK" = 1 ]; then recapk L-14-family-whole CLOSED "shell* family (6/6) present in dex"
  else recapk L-14-family-whole OPEN "shell* family incomplete in dex:$MISSF"; fi
else recapk L-14-family-whole OPEN "no APK to inspect"; fi

# L-13 no document duplication: the four docs DARKITH.md replaces must not exist
DUP=$(cd "$ROOT" && find . -not -path './.git/*' -not -path './node_modules/*' \
  \( -name 'VERSION.md' -o -name 'RECONCILIATION.md' -o -name 'DEFICIT_LEDGER.md' \
     -o -name 'singularity_progressive_continuum.md' \) 2>/dev/null)
if [ -z "$DUP" ]; then rec L-13-no-doc-dup CLOSED "one canonical doc (DARKITH.md); no overlapping copies"
else rec L-13-no-doc-dup OPEN "overlapping docs still present:$(printf ' %s' $DUP)"; fi

# L-12 one-surface delivery: a hub page exists listing every artifact as a forced download
HUB="$ROOT/dist/index.html"
if [ -f "$HUB" ]; then
  MISS=""
  for f in $(cd "$ROOT/dist" && ls *.apk *.zip *.md 2>/dev/null); do
    grep -q "href=\"$f\" download" "$HUB" || MISS="$MISS $f"
  done
  if [ -z "$MISS" ]; then recapk L-12-one-surface CLOSED "hub lists all artifacts (download)"
  else recapk L-12-one-surface OPEN "hub missing:$MISS"; fi
else recapk L-12-one-surface OPEN "no dist/index.html hub (delivery is fragmented)"; fi

# L-11 self-check: the registry is non-empty (a gate with no checks gates nothing)
[ "${#NAME[@]}" -ge 16 ] && rec L-11-registry-nonempty CLOSED "${#NAME[@]} loophole checks" || rec L-11-registry-nonempty OPEN "registry empty"

echo "  #  loophole                      status  note"
for i in "${!NAME[@]}"; do printf '  %-2s %-28s %-7s %s\n' "$((i+1))" "${NAME[$i]}" "${STATUS[$i]}" "${NOTE[$i]}"; done
echo
if [ "$OPEN" -eq 0 ]; then
  if [ "$STATIC" = 1 ]; then
    echo "STATIC OK — every statically-checkable loophole is closed."
    echo "            artifact loopholes are N/A here; run without --static against a built APK to close them."
  else
    echo "DELIVERED — every known loophole is closed or gated."
  fi
  exit 0
fi
echo "REFUSED — $OPEN loophole(s) OPEN. Do not call this delivered."; exit 1
