#!/usr/bin/env python3
"""Rebuild the source and bundle zips that the delivery hub links.

Two archives drift whenever the app or the webapp changes:

  darkith_source_fixed.zip   the Gradle source tree (app/ + wrapper) the
                             one-shot carries, without the payload wrapper
  darkith-forge-bundle.zip   the curated "one download gets everything" set

`darkith_source_fixed.zip` is regenerated from the one-shot payload, which is
the single source of truth for the native tree. The bundle is then reassembled
from the freshest delivery files, so its copies of the webapp and the APKs are
never a revision behind.

`c7_patched_sources.zip` is deliberately left alone: it is a frozen alternate
patch lineage (it adds GpuScanner.kt/IRBuilder.kt that the payload does not
carry), consumed by `forge_c7_oneshot.sh`, not a mirror of the payload.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DELIVERY = ROOT / "delivery"
ONESHOT = DELIVERY / "darkith-one-shot.sh"
MARKER = b"\n__DARKITH_PAYLOAD_BELOW__\n"

SOURCE_ZIP = DELIVERY / "darkith_source_fixed.zip"
BUNDLE_ZIP = DELIVERY / "darkith-forge-bundle.zip"

# `make-oneshot.py` roots its payload at this prefix (the tree extracts to
# `darkith-forge/` on the phone).  Source-zip members are matched on the path
# relative to that root, so strip it before comparing.
PAYLOAD_PREFIX = "darkith-forge/"

# Source-tree members that belong in darkith_source_fixed.zip, in payload order.
SOURCE_PREFIXES = ("app/",)
SOURCE_TOP = {
    "build.gradle", "settings.gradle", "gradle.properties",
    "gradlew", "gradlew.bat", "build.sh", "termux-import.sh", "zipalign.py",
}

# The bundle's top level, all served straight from delivery/.
BUNDLE_FILES = [
    "README.txt", "TERMUX-SETUP.txt", "termux-import.sh",
    "darkith-forge.html", "darkith-forged-proof.apk",
    "darkith-homekeeper-debug.apk", "build.sh", "zipalign.py",
    "savf.html", "savf.py", "forge_c7_oneshot.sh",
    "PROGRESS-LEDGER.md", "AGENTS.md",
]


def payload() -> zipfile.ZipFile:
    data = ONESHOT.read_bytes()
    i = data.find(MARKER)
    if i < 0:
        raise SystemExit("[FATAL] payload marker not found in the one-shot")
    return zipfile.ZipFile(io.BytesIO(data[i + len(MARKER):]))


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_zip(path: pathlib.Path, members: list[tuple[str, bytes]]) -> None:
    tmp = path.with_suffix(path.suffix + ".new")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in members:
            z.writestr(name, data)
    tmp.replace(path)


def build() -> int:
    pay = payload()

    def rel(n: str) -> str:
        return n[len(PAYLOAD_PREFIX):] if n.startswith(PAYLOAD_PREFIX) else n

    source = [
        (rel(n), pay.read(n))
        for n in pay.namelist()
        if (rel(n).startswith(SOURCE_PREFIXES) or rel(n) in SOURCE_TOP) and not n.endswith("/")
    ]
    write_zip(SOURCE_ZIP, source)
    print(f"  source_fixed.zip {SOURCE_ZIP.stat().st_size:,} B  entries {len(source)}")

    members: list[tuple[str, bytes]] = [
        ("darkith_source_fixed.zip", SOURCE_ZIP.read_bytes()),
        ("c7_patched_sources.zip", (DELIVERY / "c7_patched_sources.zip").read_bytes()),
    ]
    for name in BUNDLE_FILES:
        src = DELIVERY / name
        if not src.exists():
            raise SystemExit(f"[FATAL] bundle member missing from delivery: {name}")
        members.append((name, src.read_bytes()))
    write_zip(BUNDLE_ZIP, members)
    print(f"  bundle.zip {BUNDLE_ZIP.stat().st_size:,} B  entries {len(members)}")

    with zipfile.ZipFile(BUNDLE_ZIP) as z:
        hk = z.read("darkith_source_fixed.zip")
        inner = zipfile.ZipFile(io.BytesIO(hk))
        print(f"  bundle webapp  sha {sha256(z.read('darkith-forge.html'))[:16]}")
        print(f"  source webapp  sha {sha256(inner.read('app/src/main/assets/homekeeper.html'))[:16]}")
    return 0


def check() -> int:
    # delivery/ zips are regenerable output that .gitignore forbids committing, so a
    # clean checkout has none. Absent is a skip, not a failure (same rule as
    # verify.py check_sync): the gate must pass from a clean clone.
    if not (SOURCE_ZIP.exists() and BUNDLE_ZIP.exists()):
        print("  legacy zips: absent (regenerable, not committed) — skip")
        return 0
    cur = (ROOT / "darkith forge.html").read_bytes()
    # `app/src/main/assets/homekeeper.html` is the app UI surface (a synchrony
    # surface loaded by HomekeeperActivity), not the fused webapp; compare the
    # archive's copy against that source of truth.
    cur_asset = (ROOT / "app/src/main/assets/homekeeper.html").read_bytes()
    ok = True
    for label, path, member, want in [
        ("source_fixed", SOURCE_ZIP, "app/src/main/assets/homekeeper.html", cur_asset),
        ("bundle", BUNDLE_ZIP, "darkith-forge.html", cur),
    ]:
        if not path.exists():
            print(f"  MISSING {label}", file=sys.stderr)
            ok = False
            continue
        try:
            data = zipfile.ZipFile(path).read(member)
        except (KeyError, zipfile.BadZipFile) as e:
            print(f"  STALE {label} {member}  (archive lacks it: {e})", file=sys.stderr)
            ok = False
            continue
        same = data == want
        ok &= same
        print(f"  {'OK  ' if same else 'STALE'} {label} {member}  {sha256(data)[:16]}")
    # bundle's nested source zip must also carry the current webapp
    try:
        z = zipfile.ZipFile(BUNDLE_ZIP)
        inner = zipfile.ZipFile(io.BytesIO(z.read("darkith_source_fixed.zip")))
        hk = inner.read("app/src/main/assets/homekeeper.html")
    except (KeyError, zipfile.BadZipFile) as e:
        print(f"  STALE bundle source webapp  (archive lacks it: {e})", file=sys.stderr)
        ok = False
        hk = None
    if hk is not None:
        same = hk == cur_asset
        ok &= same
        print(f"  {'OK  ' if same else 'STALE'} bundle source webapp  {sha256(hk)[:16]}")
    print("LEGACY ZIPS: " + ("in sync" if ok else "STALE -- run without --check"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    return check() if args.check else build()


if __name__ == "__main__":
    sys.exit(main())
