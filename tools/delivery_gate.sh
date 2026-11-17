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

# --source-only: run on a box with no APK and no Android toolchain (CI). Checks that
# genuinely require a built APK are recorded as SKIP (named, never silently passed) and
# do not fail the run; every source-level law is still enforced. Without the flag the
# gate is strict: an absent APK leaves those loopholes OPEN.
SOURCE_ONLY=0
POS=()
for a in "$@"; do case "$a" in --source-only) SOURCE_ONLY=1 ;; *) POS+=("$a") ;; esac; done

ROOT="${POS[0]:-.}"
APK="${POS[1]:-}"
ANDROID_JAR="${POS[2]:-${ANDROID_JAR:-}}"
EXTRA_CP="${POS[3]:-${EXTRA_CP:-}}"
KOTLINC="${KOTLINC:-kotlinc}"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"

# loopholes that cannot be evaluated without a built APK: deferred (SKIP) in --source-only.
ARTIFACT_CHECKS=" L-02-apk-version L-04-artifact-built L-05-artifact-signed L-06-artifact-aligned L-09-asset-parity L-12-one-surface L-14-family-whole L-15-signer-identity L-16-arsc-stored L-17-native-tools "

OPEN=0; SKIP=0
# absolute APK path: several checks cd into other dirs, so a relative path would break
if [ -n "$APK" ] && [ -e "$APK" ]; then APK="$(cd "$(dirname "$APK")" && pwd)/$(basename "$APK")"; fi
declare -a NAME STATUS NOTE
rec() {
  local n="$1" st="$2" note="$3"
  if [ "$SOURCE_ONLY" = 1 ] && [ "$st" = OPEN ] && [ -z "$APK" ]; then
    case "$ARTIFACT_CHECKS" in *" $n "*) st=SKIP; note="deferred: needs a built APK (--source-only)";; esac
  fi
  NAME+=("$n"); STATUS+=("$st"); NOTE+=("$note")
  [ "$st" = OPEN ] && OPEN=$((OPEN+1))
  [ "$st" = SKIP ] && SKIP=$((SKIP+1))
  return 0
}

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
  if [ -n "$AV" ] && [ "$AV" = "$MV" ]; then rec L-02-apk-version CLOSED "apk=$AV == manifest=$MV"
  else rec L-02-apk-version OPEN "apk='$AV' != manifest='$MV'"; fi
else rec L-02-apk-version OPEN "no apk or no aapt (cannot prove version)"; fi

# L-03 the app can report its own installed version at runtime
if [ -n "$SRC" ] && grep -rq 'fun apkVersion' "$SRC" && grep -rq 'const val VERSION' "$SRC"; then
  rec L-03-self-report CLOSED "$(grep -rho 'VERSION = "[^"]*"' "$SRC" | head -1)"
else rec L-03-self-report OPEN "no apkVersion()/VERSION in source"; fi

# L-04 an artifact was actually produced (not just source)
if [ -n "$APK" ] && [ -s "$APK" ]; then rec L-04-artifact-built CLOSED "$(stat -c%s "$APK") bytes"
else rec L-04-artifact-built OPEN "no APK built"; fi

# L-05 the artifact is signed and verifies
if [ -n "$APK" ] && [ -f "$APK" ] && command -v apksigner >/dev/null 2>&1; then
  if apksigner verify "$APK" >/dev/null 2>&1; then rec L-05-artifact-signed CLOSED "apksigner verify ok"
  else rec L-05-artifact-signed OPEN "apksigner verify FAILED"; fi
else rec L-05-artifact-signed OPEN "no apk or no apksigner"; fi

# L-06 the artifact is zip-aligned
if [ -n "$APK" ] && [ -f "$APK" ] && command -v zipalign >/dev/null 2>&1; then
  if zipalign -c 4 "$APK" >/dev/null 2>&1; then rec L-06-artifact-aligned CLOSED "4-byte aligned"
  else rec L-06-artifact-aligned OPEN "not 4-byte aligned"; fi
else rec L-06-artifact-aligned OPEN "no apk or no zipalign"; fi

# L-07 one authoritative tree + no androidx/foreign symbols (the §19 gate).
# The §19 gate is run ONCE here; L-10 reuses the same result (one compiler, one truth).
# A SKIPPED compile proof is not a pass: when kotlinc/android_jar are absent the §19 gate is
# run with --no-compile and both L-07 and L-10 are forced OPEN, so a skipped proof can never
# masquerade as a closed loophole (W-040).
L19LOG=/tmp/l19.$$; L19_PASS=0; L19_SKIP=0
if [ -n "$SRC" ] && [ -f "$SELF_DIR/fork_integrity_gate.sh" ]; then
  if [ -z "$ANDROID_JAR" ] || ! command -v "$KOTLINC" >/dev/null 2>&1; then
    bash "$SELF_DIR/fork_integrity_gate.sh" "$SRC" "$ANDROID_JAR" "$EXTRA_CP" --no-compile >"$L19LOG" 2>&1 || true
  else
    bash "$SELF_DIR/fork_integrity_gate.sh" "$SRC" "$ANDROID_JAR" "$EXTRA_CP" >"$L19LOG" 2>&1 || true
  fi
  grep -q 'MUST-11: SKIPPED' "$L19LOG" && L19_SKIP=1
  grep -q 'PASS: all' "$L19LOG" && L19_PASS=1
fi
if [ "$L19_PASS" = 1 ] && [ "$L19_SKIP" = 0 ]; then
  rec L-07-fork-singularity CLOSED "§19 gate PASS (compile proof ran)"
elif [ "$L19_SKIP" = 1 ]; then
  rec L-07-fork-singularity OPEN "compile proof SKIPPED (no kotlinc/android_jar) — §19 result untrusted"
else
  rec L-07-fork-singularity OPEN "$(grep -m1 DEFICIT "$L19LOG" 2>/dev/null | sed 's/^ *//' || echo 'no source tree or no §19 gate')"
fi

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
  if [ -z "$MISSING" ]; then rec L-09-asset-parity CLOSED "all assets present"
  else rec L-09-asset-parity OPEN "not in apk: $(printf '%s ' $MISSING)"; fi
else rec L-09-asset-parity OPEN "no apk/manifest/assets/aapt"; fi

# L-10 the tree compiles clean (currency is proven, not asserted) — same §19 result.
if [ "$L19_PASS" = 1 ] && grep -q 'kotlinc clean' "$L19LOG"; then
  rec L-10-currency CLOSED "$(grep -m1 'kotlinc clean' "$L19LOG" | sed 's/^ *//')"
elif [ "$L19_SKIP" = 1 ]; then
  rec L-10-currency OPEN "compile proof SKIPPED (no kotlinc/android_jar) — currency UNPROVEN"
else rec L-10-currency OPEN "$(grep -m1 -E 'DEFICIT' "$L19LOG" 2>/dev/null | sed 's/^ *//' || echo 'compile not clean')"; fi
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
      rec L-17-native-tools CLOSED "lib/*/libaapt2.so+libzipalign.so shipped; extractNativeLibs=true"
    else rec L-17-native-tools OPEN "native libs shipped but extractNativeLibs!=true -> nativeLibraryDir stays empty"; fi
  else rec L-17-native-tools OPEN "handcoded binaries absent from lib/<abi>/ (forge cannot exec them)"; fi
else rec L-17-native-tools OPEN "no APK to inspect"; fi

# L-16 arsc-stored: resources.arsc must be STORED (uncompressed) or Android 11+ refuses install
if [ -n "$APK" ] && [ -s "$APK" ]; then
  if python3 -c "import zipfile,sys; z=zipfile.ZipFile('$APK'); i=z.getinfo('resources.arsc'); sys.exit(0 if i.compress_type==0 else 1)" 2>/dev/null; then
    rec L-16-arsc-stored CLOSED "resources.arsc uncompressed (API30+ installable)"
  else rec L-16-arsc-stored OPEN "resources.arsc is DEFLATED -> INSTALL_PARSE_FAILED (App not installed)"; fi
else rec L-16-arsc-stored OPEN "no APK to inspect"; fi

# L-15 signer-identity: signer-coupled nanosecond-nonce signature present in the dex
if [ -n "$APK" ] && [ -s "$APK" ]; then
  if python3 -c "import zipfile,sys; d=zipfile.ZipFile('$APK').read('classes.dex'); sys.exit(0 if (b'signerSignature' in d and b'HmacSHA256' in d) else 1)"; then
    rec L-15-signer-identity CLOSED "signerSignature+verifySignerSignature (HMAC-SHA256, ns nonce) in dex"
  else rec L-15-signer-identity OPEN "signer identity API missing from dex"; fi
else rec L-15-signer-identity OPEN "no APK to inspect"; fi

# L-14 family-whole: every member of the shell* family must be present IN THE DEX (MUST #20/SPI-19)
if [ -n "$APK" ] && [ -s "$APK" ]; then
  DEXOK=1; MISSF=""
  for m in shell shellExec shellSetCwd shellSetEnv shellEnv shellHistory; do
    if ! python3 -c "import zipfile,sys; d=zipfile.ZipFile('$APK').read('classes.dex'); sys.exit(0 if b'$m' in d else 1)"; then
      DEXOK=0; MISSF="$MISSF $m"
    fi
  done
  if [ "$DEXOK" = 1 ]; then rec L-14-family-whole CLOSED "shell* family (6/6) present in dex"
  else rec L-14-family-whole OPEN "shell* family incomplete in dex:$MISSF"; fi
else rec L-14-family-whole OPEN "no APK to inspect"; fi

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
  if [ -z "$MISS" ]; then rec L-12-one-surface CLOSED "hub lists all artifacts (download)"
  else rec L-12-one-surface OPEN "hub missing:$MISS"; fi
else rec L-12-one-surface OPEN "no dist/index.html hub (delivery is fragmented)"; fi

# L-18 install gate: the package installer accepts the APK (no "App not installed").
# The exhaustive registry of install blockers (version, sdk range, v2 signature, align,
# arsc/so STORED, extractNativeLibs, dup entries, testOnly, launcher, components-in-dex,
# ABI, label), read from the APK's OWN manifest. N/A when the artifact tools are absent,
# so a box without aapt2/apksigner still evaluates every other law honestly.
IG="$SELF_DIR/install_gate.py"
if [ -n "$APK" ] && [ -s "$APK" ] && [ -f "$IG" ] \
   && command -v aapt2 >/dev/null 2>&1 && command -v apksigner >/dev/null 2>&1; then
  if python3 "$IG" "$APK" "$ROOT" >/tmp/ig.$$ 2>&1; then
    rec L-18-install-gate CLOSED "install_gate: INSTALLABLE (no known blocker)"
  else
    rec L-18-install-gate OPEN "$(grep -m1 OPEN /tmp/ig.$$ | sed 's/^ *//')"
  fi
  rm -f /tmp/ig.$$
else rec L-18-install-gate N/A "no APK or no aapt2/apksigner (install not proven here)"; fi

# L-19 runtime render: the launcher surface actually PAINTS — the UI the OS hands to
# Zygote/AMS/WMS. Loads assets/homekeeper.html at 360x800 with and without the native
# bridge; fails on any console/page error, blank body, empty DOM, or overflow. N/A when
# playwright or the asset is absent — never a false OPEN.
RG="$SELF_DIR/runtime_gate.py"
UI_ASSET="$(find "$ROOT/app/src/main/assets" -maxdepth 1 -name homekeeper.html 2>/dev/null | head -1)"
if [ -n "$UI_ASSET" ] && [ -f "$RG" ] && python3 -c 'import playwright' >/dev/null 2>&1; then
  if python3 "$RG" >/tmp/rg.$$ 2>&1; then
    rec L-19-runtime-render CLOSED "launcher UI renders at 360x800, 0 JS errors"
  else
    rec L-19-runtime-render OPEN "render defect: $(grep -m1 FAIL /tmp/rg.$$ | sed 's/^ *//')"
  fi
  rm -f /tmp/rg.$$
else rec L-19-runtime-render N/A "no launcher asset or playwright (render not proven here)"; fi

# L-11 self-check: the registry is non-empty (a gate with no checks gates nothing)
[ "${#NAME[@]}" -ge 18 ] && rec L-11-registry-nonempty CLOSED "${#NAME[@]} loophole checks" || rec L-11-registry-nonempty OPEN "registry empty"

echo "  #  loophole                      status  note"
for i in "${!NAME[@]}"; do printf '  %-2s %-28s %-7s %s\n' "$((i+1))" "${NAME[$i]}" "${STATUS[$i]}" "${NOTE[$i]}"; done
echo
if [ "$OPEN" -eq 0 ]; then
  if [ "$SKIP" -gt 0 ]; then
    echo "SOURCE-OK — 0 loophole(s) OPEN; $SKIP deferred (no APK here). Artifact laws are NOT yet proven."
  else
    echo "DELIVERED — every known loophole is closed or gated."
  fi
  exit 0
fi
echo "REFUSED — $OPEN loophole(s) OPEN. Do not call this delivered."; exit 1
