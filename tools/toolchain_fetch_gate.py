#!/usr/bin/env python3
"""Detect/repair single-mirror android.jar downloads that fail on transient HTTP 429."""
import argparse, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
SOURCE=ROOT/"tools"/"fetch_toolchain.sh"
HELPER='''fetch_artifact() {
  local label="$1" dest="$2"; shift 2
  local tmp="${dest}.part"
  rm -f "$tmp"
  for url in "$@"; do
    say "$label: trying mirror ${url%%/maven2/*}"
    if curl -fsSL --retry 5 --retry-all-errors --retry-delay 3 --retry-max-time 90 --connect-timeout 30 --max-time 900 -o "$tmp" "$url" && [ -s "$tmp" ]; then
      mv -f "$tmp" "$dest"
      return 0
    fi
    rm -f "$tmp"
  done
  return 1
}
'''
BLOCK='''  say "android.jar: fetching ($ANDROID_JAR_NAME, ~137 MB)"
  fetch_artifact "android.jar" "$DEST/$ANDROID_JAR_NAME" "https://repo.maven.apache.org/maven2/org/robolectric/android-all/14-robolectric-10818077/${ANDROID_JAR_NAME}" "https://maven-central.storage-download.googleapis.com/maven2/org/robolectric/android-all/14-robolectric-10818077/${ANDROID_JAR_NAME}" "https://repo1.maven.org/maven2/org/robolectric/android-all/14-robolectric-10818077/${ANDROID_JAR_NAME}" || { say "DEFICIT: android.jar download failed from all configured mirrors"; exit 1; }
'''
def patch_text(text):
    if "fetch_artifact() {" not in text:
        p=text.index("say() { printf"); e=text.index(chr(10),p)+1
        text=text[:e]+chr(10)+HELPER+chr(10)+text[e:]
    a=text.index('  say "android.jar: fetching'); b=text.index(chr(10)+"fi",a)
    return text[:a]+BLOCK.rstrip(chr(10))+text[b:]
def check(text):
    return all(x in text for x in ("fetch_artifact() {","repo.maven.apache.org/maven2/org/robolectric","maven-central.storage-download.googleapis.com/maven2/org/robolectric","repo1.maven.org/maven2/org/robolectric","--retry-all-errors","--max-time 900","local tmp=","dest}.part","mv -f","android.jar download failed from all configured mirrors"))

def selftest():
    fixture='''say() { printf '  %s\n' "$*"; }
if [ -r "$DEST/$ANDROID_JAR_NAME" ]; then
  say "android.jar: cached"
else
  say "android.jar: fetching ($ANDROID_JAR_NAME, ~137 MB)"
  curl -fsSL -o "$DEST/$ANDROID_JAR_NAME" \\
    "https://repo1.maven.org/maven2/org/robolectric/android-all/14-robolectric-10818077/${ANDROID_JAR_NAME}" \\
    || { say "DEFICIT: android.jar download failed"; exit 1; }
fi
'''
    try:
        fixed=patch_text(fixture); ok=check(fixed) and patch_text(fixed)==fixed
    except Exception: ok=False
    print("toolchain fetch gate selftest: "+("PASS" if ok else "FAIL")); return 0 if ok else 1
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--check",action="store_true"); ap.add_argument("--fix",action="store_true"); ap.add_argument("--selftest",action="store_true"); a=ap.parse_args()
    if a.selftest: return selftest()
    text=SOURCE.read_text(encoding="utf-8")
    if a.fix: text=patch_text(text); SOURCE.write_text(text,encoding="utf-8")
    ok=check(text); print("toolchain download resilience: "+("PASS" if ok else "FAIL")); return 0 if ok else 1
if __name__=="__main__": sys.exit(main())
