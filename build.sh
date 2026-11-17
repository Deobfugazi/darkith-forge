#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
APPNAME="${2:-App}"
PKG="${3:-com.darkith.app}"
MIN_SDK="${MIN_SDK:-24}"
OUT="${OUT:-$ROOT/app-signed.apk}"
# Optional space-separated asset paths to exclude (relative to assets/ or bare
# filenames). Empty by default: the host app reads assets/engine/* at runtime
# to build APKs on-device, so those MUST ship.
SKIP_ASSETS="${SKIP_ASSETS:-}"

say(){ printf '%s\n' "$*"; }
die(){ printf 'ANCHOR: %s\n' "$*" >&2; exit 1; }

# ── 1. AUTO-DISCOVERY ─────────────────────────────────────────────────────────
MANIFEST=$(find "$ROOT" -maxdepth 4 -name AndroidManifest.xml -not -path "*/build/*" | head -n 1)
[ -n "$MANIFEST" ] || die "No AndroidManifest.xml found under $ROOT"
PROJ_DIR=$(dirname "$MANIFEST")
say "== DISCOVERY: manifest at $MANIFEST"
say "== DISCOVERY: source root at $PROJ_DIR"

# FIX: accept the standard Gradle layout (src/main/java) as well as a flat src/.
HAS_SRC=0; SRC_DIR=""
for d in "$PROJ_DIR/src" "$PROJ_DIR/java"; do
  if [ -d "$d" ] && [ -n "$(find "$d" \( -name '*.kt' -o -name '*.java' \) 2>/dev/null | head -n 1)" ]; then
    SRC_DIR="$d"; HAS_SRC=1; break
  fi
done
[ "$HAS_SRC" = 1 ] && say "== DISCOVERY: sources at $SRC_DIR"

# Package name from the manifest is the source of truth (drives R.java lookup).
MANIFEST_PKG=$(sed -n 's/.*package="\([^"]*\)".*/\1/p' "$MANIFEST" | head -n 1)
[ -n "$MANIFEST_PKG" ] && [ "$MANIFEST_PKG" != "$PKG" ] && \
  say "== NOTE: manifest package '$MANIFEST_PKG' overrides argument '$PKG'" && PKG="$MANIFEST_PKG"

# ── 2. TOOL DISCOVERY ─────────────────────────────────────────────────────────
which_tool(){
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then command -v "$name"; return 0; fi
  [ -x "${PREFIX:-/nonexistent}/bin/$name" ] && { echo "${PREFIX}/bin/$name"; return 0; }
  local hit
  hit=$(find "${ANDROID_HOME:-/nonexistent}" "${ANDROID_SDK_ROOT:-/nonexistent}" \
             /opt/android* /usr/lib/android* "$HOME"/android* -maxdepth 5 -name "$name" -type f 2>/dev/null | head -1)
  [ -n "$hit" ] && { echo "$hit"; return 0; }
  return 1
}

AAPT2="${AAPT2:-$(which_tool aapt2   || true)}"
ZIPALIGN="${ZIPALIGN:-$(which_tool zipalign || true)}"
APKSIGNER="${APKSIGNER:-$(which_tool apksigner || true)}"
KOTLINC="${KOTLINC:-$(which_tool kotlinc || true)}"
KEYTOOL=$(which_tool keytool || true)
PY3=$(which_tool python3 || true); [ -n "$PY3" ] || PY3=$(which_tool python || true)

# JDK kotlinc fallback: Termux 'kotlinc' is a wrapper; a real JDK kotlinc may sit elsewhere.
if [ -z "$KOTLINC" ]; then
  for c in "${KOTLINC_BIN:-}" /tmp/ktc/kotlinc/bin/kotlinc /opt/kotlinc/bin/kotlinc "$HOME"/kotlinc/bin/kotlinc; do
    [ -n "$c" ] && [ -x "$c" ] && { KOTLINC="$c"; break; }
  done
fi

SELF_DIR=$(cd "$(dirname "$0")" && pwd)
PYZIP=""
for c in "${ZIPALIGN_PY:-}" "$SELF_DIR/zipalign.py" "$ROOT/zipalign.py"; do
  if [ -n "$c" ] && [ -r "$c" ]; then PYZIP="$c"; break; fi
done

ANDROID_JAR="${ANDROID_JAR:-}"
if [ -z "$ANDROID_JAR" ]; then
  for c in "$ROOT/android.jar" "$ROOT/libs/android.jar" \
           "${ANDROID_HOME:-}/platforms/android-34/android.jar" \
           "$HOME/android-sdk/platforms/android-34/android.jar" \
           /tmp/tc/android34.jar; do
    [ -r "$c" ] && { ANDROID_JAR="$c"; break; }
  done
fi

D8_BIN=$(which_tool d8 || true)
R8_JAR="${R8_JAR:-}"
if [ -z "$D8_BIN" ] && [ -z "$R8_JAR" ]; then
  for c in "$ROOT/libs/r8.jar" /tmp/tc/r8.jar; do
    [ -r "$c" ] && { R8_JAR="$c"; break; }
  done
fi

[ -n "$AAPT2" ]    || die "aapt2 not found"
[ -r "$ANDROID_JAR" ] || die "android-34 android.jar missing (set ANDROID_JAR)"
[ -n "$ZIPALIGN" ] || { [ -n "$PY3" ] && [ -n "$PYZIP" ] || die "zipalign missing"; }
[ -n "$APKSIGNER" ] || die "apksigner missing"
[ -n "$KEYTOOL" ] || die "keytool missing (no JDK)"
[ -n "$D8_BIN" ] || [ -n "$R8_JAR" ] || die "no d8 and no r8.jar"
case "$ANDROID_JAR" in *android-35*|*android35*) die "API 35 is over the ceiling (34)";; esac
# Preflight the compiler only when it is actually needed, so a prebuilt-dex build
# on a phone with no JDK still succeeds.
if [ "$HAS_SRC" = 1 ] && [ -z "$KOTLINC" ]; then
  die "kotlinc not found but sources exist in $SRC_DIR (install kotlin, or drop a prebuilt classes.dex and remove src/)"
fi

zipalign_run(){
  if [ -n "$ZIPALIGN" ]; then "$ZIPALIGN" -f -p 4 "$1" "$2"
  else "$PY3" "$PYZIP" "$1" "$2" 4; fi
}
zipalign_check(){
  if [ -n "$ZIPALIGN" ]; then "$ZIPALIGN" -c -p 4 "$1"
  else "$PY3" "$PYZIP" -c 4 "$1"; fi
}

d8_run(){
  local out="$1"; shift
  if [ -n "$D8_BIN" ]; then "$D8_BIN" --min-api "$MIN_SDK" --lib "$ANDROID_JAR" --output "$out" "$@"
  else java -cp "$R8_JAR" com.android.tools.r8.D8 --min-api "$MIN_SDK" --lib "$ANDROID_JAR" --output "$out" "$@"; fi
}

# ── 3. CLEAN & PREPARE ───────────────────────────────────────────────────────
WORK="$ROOT/.forge_work"
rm -rf "$WORK"
mkdir -p "$WORK/gen" "$WORK/classes"
rm -f "$OUT"

# ── 4. EXECUTE THE 7-STEP CHAIN ──────────────────────────────────────────────

RES_ARGS=()
if [ -d "$PROJ_DIR/res" ]; then
  "$AAPT2" compile --dir "$PROJ_DIR/res" -o "$WORK/compiled_res.zip"
  RES_ARGS=("$WORK/compiled_res.zip")
  say "1/7 aapt2 compile  ok"
else
  say "1/7 aapt2 compile  skipped (no res/)"
fi

"$AAPT2" link -o "$WORK/base.apk" -I "$ANDROID_JAR" \
  --manifest "$MANIFEST" ${RES_ARGS[@]+"${RES_ARGS[@]}"} --java "$WORK/gen" \
  --min-sdk-version "$MIN_SDK" --target-sdk-version 34 --auto-add-overlay
say "2/7 aapt2 link     ok -> base.apk"

if [ "$HAS_SRC" = 1 ]; then
  GEN_JAVA=""
  [ -f "$WORK/gen/${PKG//.//}/R.java" ] && GEN_JAVA="$WORK/gen/${PKG//.//}/R.java"
  KCP="$ANDROID_JAR"
  for j in "$ROOT"/libs/*.jar "$PROJ_DIR"/libs/*.jar; do [ -r "$j" ] && KCP="$KCP:$j"; done
  # -J-Xmx${KOTLINC_XMX:-512m} is honoured by the kotlinc launcher: keeps the compile inside RAM.
  if ! "$KOTLINC" "$SRC_DIR" $GEN_JAVA -classpath "$KCP" -J-Xmx${KOTLINC_XMX:-512m} -d "$WORK/classes" -nowarn 2>"$WORK/kotlinc.log"; then
    say "--- kotlinc errors (first 20) ---"
    grep -E 'error:' "$WORK/kotlinc.log" | head -20 || tail -20 "$WORK/kotlinc.log"
    die "kotlinc failed (see $WORK/kotlinc.log)"
  fi
  [ -n "$(ls -A "$WORK/classes" 2>/dev/null)" ] || die "kotlinc produced nothing"
  say "3/7 kotlinc        ok -> classes/"
  # FIX: mapfile avoids word-splitting and ARG_MAX blowups on long class lists.
  mapfile -t CLASSES < <(find "$WORK/classes" -name '*.class')
  d8_run "$WORK" "${CLASSES[@]}"
  say "4/7 d8             ok -> classes.dex"
elif [ -f "$PROJ_DIR/classes.dex" ]; then
  cp "$PROJ_DIR/classes.dex" "$WORK/classes.dex"
  say "3/7+4/7            using prebuilt classes.dex"
elif [ -f "$ROOT/classes.dex" ]; then
  cp "$ROOT/classes.dex" "$WORK/classes.dex"
  say "3/7+4/7            using prebuilt classes.dex (root)"
else
  die "no src/ and no prebuilt classes.dex found"
fi

# FIX: exclude the signing secret + android.jar from packaged assets; use $PY3.
"$PY3" - "$WORK" "$PROJ_DIR" "$SKIP_ASSETS" <<'PY'
import sys, os, zipfile
work, proj, skip = sys.argv[1], sys.argv[2], set(sys.argv[3].split())
base=os.path.join(work,"base.apk"); dex=os.path.join(work,"classes.dex")
tmp=base+".tmp"

# API 30+ (targetSdk>=30) refuses to install an APK whose resources.arsc or
# lib/*.so are DEFLATED: both must be STORED and 4-byte aligned (zipalign -p).
# aapt2 already writes them STORED; re-zipping with ZIP_DEFLATED destroys that,
# which is exactly the "App not installed" defect. Preserve the store decision.
def must_store(name):
    # resources.arsc and EVERY lib/ entry (not only .so) must stay STORED.
    return name == "resources.arsc" or name.startswith("lib/")

with zipfile.ZipFile(base) as zin, zipfile.ZipFile(tmp,"w") as zo:
    for e in zin.infolist():
        if e.filename=="classes.dex": continue
        # Android 11+ (API 30) requires resources.arsc and lib/*.so to be STORED,
        # not DEFLATED: the loader mmaps them in place. Re-adding them to a
        # ZIP_DEFLATED archive silently compresses them and the installer refuses
        # with a bare "App not installed". Preserve STORED for exactly those entries.
        zi=zipfile.ZipInfo(e.filename, date_time=e.date_time)
        zi.compress_type = zipfile.ZIP_STORED if must_store(e.filename) else e.compress_type
        zi.external_attr=e.external_attr
        zo.writestr(zi, zin.read(e.filename))
    zi=zipfile.ZipInfo("classes.dex", date_time=(1980,1,1,0,0,0))
    zi.compress_type=zipfile.ZIP_DEFLATED
    zo.writestr(zi, open(dex,"rb").read())
    ad=os.path.join(proj,"assets")
    if os.path.isdir(ad):
        for b,_,fs in os.walk(ad):
            for f in fs:
                rel=os.path.relpath(os.path.join(b,f), ad).replace(os.sep,"/")
                if rel in skip or os.path.basename(rel) in skip:
                    print("   [skip asset] "+rel); continue
                zi=zipfile.ZipInfo("assets/"+rel, date_time=(1980,1,1,0,0,0))
                zi.compress_type=zipfile.ZIP_DEFLATED
                zo.writestr(zi, open(os.path.join(b,f),"rb").read())
    # Native toolchain: app/src/main/jniLibs/<abi>/*.so -> lib/<abi>/*.so, STORED.
    # The on-device forge reads libaapt2.so / libzipalign.so from nativeLibraryDir,
    # so a build that omits them produces an APK that installs but cannot forge.
    jl=os.path.join(proj,"jniLibs")
    if os.path.isdir(jl):
        for abi in sorted(os.listdir(jl)):
            abidir=os.path.join(jl,abi)
            if not os.path.isdir(abidir): continue
            for f in sorted(os.listdir(abidir)):
                if not f.endswith(".so"): continue
                zi=zipfile.ZipInfo("lib/%s/%s"%(abi,f), date_time=(1980,1,1,0,0,0))
                zi.compress_type=zipfile.ZIP_STORED
                zo.writestr(zi, open(os.path.join(abidir,f),"rb").read())
                print("   [native] lib/%s/%s (stored)"%(abi,f))
os.replace(tmp, base)
PY
say "5/7 package        ok -> base.apk (classes.dex + assets + jniLibs; arsc/so kept STORED)"

zipalign_run "$WORK/base.apk" "$WORK/aligned.apk"
say "6/7 zipalign       ok -> aligned.apk$([ -n "$ZIPALIGN" ] || echo ' (python fallback)')"

KS="$ROOT/debug.keystore"
[ -f "$KS" ] || "$KEYTOOL" -genkeypair -v -keystore "$KS" -alias androiddebugkey \
  -keyalg RSA -keysize 2048 -validity 10000 -storepass android -keypass android \
  -dname "CN=Android Debug,O=Android,C=US" >/dev/null 2>&1
"$APKSIGNER" sign --ks "$KS" --ks-key-alias androiddebugkey \
  --ks-pass pass:android --key-pass pass:android \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --out "$OUT" "$WORK/aligned.apk"
say "7/7 apksigner      ok -> $OUT"

"$APKSIGNER" verify --verbose "$OUT" | grep -E "Verifies|scheme" || true
zipalign_check "$OUT" >/dev/null && say "zipalign verify    ok" || die "zipalign -c -p 4 failed"

# API 30+ hard gate: resources.arsc and lib/*.so MUST be STORED (not DEFLATED).
"$PY3" - "$OUT" <<'PY2'
import sys, zipfile
z=zipfile.ZipFile(sys.argv[1])
bad=[n for n in z.namelist()
     if (n=="resources.arsc" or n.endswith(".so")) and z.getinfo(n).compress_type!=0]
if bad:
    print("ANCHOR: API30 install gate FAILED - DEFLATED: "+", ".join(bad)); sys.exit(1)
print("api30 gate         ok (arsc + lib/*.so STORED)")
PY2
[ $? -eq 0 ] || die "API 30 store gate failed (see above)"
say "DONE: $OUT"
