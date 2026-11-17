#!/usr/bin/env python3
"""Build `delivery/darkith-one-shot.sh` — the single self-contained Termux installer.

The output is one executable file: a POSIX-sh header, then the marker line
`__DARKITH_PAYLOAD_BELOW__`, then a ZIP payload of the whole tree. On the phone it
extracts itself, builds the host APK with the raw 7-step chain (no Gradle, SPI-1),
and installs it — so the Operator drops Termux after one command.

  python3 build/make-oneshot.py            # write the one-shot
  python3 build/make-oneshot.py --check    # verify an existing one-shot is current

The payload is the authoritative tree: app/ (Kotlin + engine assets + jniLibs),
build.sh, the webapps, and the tools the build needs. Signing key material is NOT
packaged unless it already sits in app/src/main/assets/engine (it is gitignored).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import pathlib
import stat
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DELIVERY = ROOT / "delivery"
ONESHOT = DELIVERY / "darkith-one-shot.sh"
MARKER = b"\n__DARKITH_PAYLOAD_BELOW__\n"
PREFIX = "darkith-forge/"

# The tree the payload carries: everything build.sh reads, nothing it does not.
INCLUDE_DIRS = ("app", "tools", "libs")
INCLUDE_FILES = (
    "build.sh",
    "build&install.sh",
    "zipalign.py",
    "savf.py",
    "AGENTS.md",
    "DARKITH.md",
    "RESUME.md",
)
WEBAPPS = (
    "darkith home forge.html",
    "darkith code studio.html",
    "savf.html",
    "omega.html",
)
# Build residue and caches that must never ride along.
EXCLUDE_DIR_PARTS = {
    ".git", ".forge_work", "__pycache__", ".tools", ".shell-harness",
    "delivery", "node_modules", ".openhands",
}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".log", ".bak", ".orig")


HEADER = r"""#!/data/data/com.termux/files/usr/bin/bash
# DARKITH ONE-SHOT — build + install the Keeper Forge host APK on Termux, no Gradle.
#
#   bash darkith-one-shot.sh            build + install
#   bash darkith-one-shot.sh --build    build only (leave the APK on disk)
#   bash darkith-one-shot.sh --verify   extract + run the gates, install nothing
#
# Self-contained: the payload below this header is the whole tree. SPI-1: the raw
# aapt2 -> kotlinc -> d8 -> zip -> zipalign -> apksigner chain only. No Gradle.
set -uo pipefail

EXPECT_SHA256="__EXPECT_SHA256__"
PAYLOAD_MARKER="__DARKITH_PAYLOAD_BELOW__"
MODE="install"
case "${1:-}" in
  --build)  MODE="build"  ;;
  --verify) MODE="verify" ;;
  --install|"") MODE="install" ;;
  *) printf 'unknown flag: %s\n' "$1" >&2; exit 2 ;;
esac

say(){ printf '  %s\n' "$*"; }
die(){ printf 'DEFICITS: {(%s, "%s")}\n' "${1:-M0}" "${2:-failed}" >&2; exit 1; }

# ── 0. locate our own bytes and the payload ─────────────────────────────────────
SELF="${BASH_SOURCE[0]:-$0}"
[ -r "$SELF" ] || die M0 "cannot read $SELF"
LINE=$(awk '$0=="__DARKITH_PAYLOAD_BELOW__"{print NR+1; exit}' "$SELF")
[ -n "$LINE" ] || die M0 "payload marker not found"
WORK=$(mktemp -d 2>/dev/null) || WORK="${TMPDIR:-/tmp}/darkith-oneshot.$$"
[ -d "$WORK" ] || die M0 "cannot create a work directory"
trap 'rm -rf "$WORK"' EXIT

# ── 1. extract the payload (ZIP after the marker line) ──────────────────────────
tail -n +"$LINE" "$SELF" > "$WORK/payload.zip"
python3 - "$WORK/payload.zip" "$EXPECT_SHA256" <<'PY' || die M1 "payload extract/verify failed"
import hashlib, io, sys, zipfile
path, want = sys.argv[1], sys.argv[2]
data = open(path, "rb").read()
got = hashlib.sha256(data).hexdigest()
if want and want != got:
    print("payload sha256 mismatch: want %s got %s" % (want[:16], got[:16]))
    sys.exit(1)
zipfile.ZipFile(io.BytesIO(data)).extractall(path + ".d")
PY
SRC="$WORK/payload.zip.d/darkith-forge"
[ -d "$SRC" ] || die M1 "payload has no $PREFIX root"

# ── 2. provision the raw chain (idempotent; skips anything already present) ─────
if [ -x "$SRC/tools/fetch_toolchain.sh" ]; then
  say "toolchain: provisioning (cached under .tools/)"
  ( cd "$SRC" && bash tools/fetch_toolchain.sh ) || die M2 "toolchain provisioning failed"
  export JAVA_HOME="${JAVA_HOME:-$SRC/.tools/jdk}"
  [ -x "$SRC/.tools/kotlinc/bin/kotlinc" ] && export KOTLINC="$SRC/.tools/kotlinc/bin/kotlinc"
  for j in "$SRC"/.tools/android*.jar "$SRC"/.tools/android.jar; do [ -r "$j" ] && export ANDROID_JAR="$j"; done
  export PATH="$JAVA_HOME/bin:$SRC/.tools:$PATH"
fi

# ── 3. stage the child-forge engine inputs (android.jar + signing pair) ─────────
if [ -x "$SRC/tools/stage_engine_inputs.sh" ]; then
  ( cd "$SRC" && bash tools/stage_engine_inputs.sh ) || say "engine staging: skipped"
fi

# ── 4. build with the raw 7-step chain ──────────────────────────────────────────
say "build: running the 7-step raw chain"
( cd "$SRC" && bash build.sh . Darkith com.darkith.transliaison ) || die M3 "build failed"
APK="$SRC/app-signed.apk"
[ -f "$APK" ] || die M3 "no APK produced at $APK"
say "build: $(wc -c <"$APK") B -> $APK"

# The work dir is removed on exit, so publish the APK to the caller's CWD first.
OUT_APK="$PWD/darkith-forge-signed.apk"
cp "$APK" "$OUT_APK" 2>/dev/null && APK="$OUT_APK" && say "apk: $APK"

# ── 5. install (skip for --build/--verify) ──────────────────────────────────────
if [ "$MODE" = "install" ]; then
  if command -v termux-open >/dev/null 2>&1; then
    termux-open --content-type application/vnd.android.package-archive "$APK" \
      || die M4 "termux-open failed"
    say "install: handed to the package installer"
  elif command -v pm >/dev/null 2>&1; then
    pm install -r "$APK" || die M4 "pm install failed"
    say "install: installed via pm"
  else
    say "install: no termux-open/pm — APK left at $APK"
    say "         open it in the forge app's terminal, or: termux-open $APK"
  fi
else
  say "mode=$MODE: APK left at $APK"
fi

say "done. The forge terminal inside the app can now build on-device."
exit 0
"""


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def included(rel: pathlib.Path) -> bool:
    parts = set(rel.parts)
    if parts & EXCLUDE_DIR_PARTS:
        return False
    if rel.suffix in EXCLUDE_SUFFIX:
        return False
    if rel.name.endswith(".so") and "jniLibs" not in rel.parts:
        return False
    return True


def collect() -> list[tuple[str, bytes]]:
    members: list[tuple[str, bytes]] = []
    for d in INCLUDE_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT)
            if not included(rel):
                continue
            members.append((rel.as_posix(), p.read_bytes()))
    for f in INCLUDE_FILES + WEBAPPS:
        p = ROOT / f
        if p.is_file():
            members.append((f, p.read_bytes()))
    return members


def build_payload(members: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, data in members:
            zi = zipfile.ZipInfo(PREFIX + rel, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o100644 << 16
            z.writestr(zi, data)
    return buf.getvalue()


def write(members: list[tuple[str, bytes]]) -> dict:
    payload = build_payload(members)
    digest = sha256(payload)
    head = HEADER.replace("__EXPECT_SHA256__", digest).encode()
    ONESHOT.parent.mkdir(parents=True, exist_ok=True)
    ONESHOT.write_bytes(head + MARKER + payload)
    ONESHOT.chmod(ONESHOT.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return {"bytes": ONESHOT.stat().st_size, "payload": len(payload), "sha256": digest}


def check() -> int:
    if not ONESHOT.exists():
        print("one-shot: MISSING", file=sys.stderr)
        return 1
    data = ONESHOT.read_bytes()
    i = data.find(MARKER)
    if i < 0:
        print("one-shot: no payload marker", file=sys.stderr)
        return 1
    payload = data[i + len(MARKER):]
    want = sha256(build_payload(collect()))
    got = sha256(payload)
    ok = want == got
    print(f"  {'OK  ' if ok else 'STALE'} one-shot payload  {got[:16]}  (tree {want[:16]})")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        return check()
    members = collect()
    info = write(members)
    print(f"one-shot {info['bytes']:,} B  payload {info['payload']:,} B  members {len(members)}")
    print(f"  sha256 {info['sha256'][:16]}  -> {ONESHOT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
