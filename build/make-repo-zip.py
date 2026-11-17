#!/usr/bin/env python3
"""Rebuild `delivery/darkith-forge-repo.zip` from canonical sources.

The repo zip is the GitHub-shaped host: `darkith-forge/{app,webapp,docs,.github}`.
It drifts whenever the webapp or the engine changes, so it is generated here
rather than hand-assembled.

Canonical sources
  app/      the one-shot payload's `app/` tree -- the same Kotlin, the same
            engine assets, plus the release key/cert and the arm64 toolchain
            libs the host needs to forge on-device.
  webapp/   the project's current single-file webapps.
  docs/     the existing repo docs, with the proof APK refreshed.

Everything else in the repo (README, .github, .gitignore, Termux notes) is
carried over untouched, so hand-written repo scaffolding survives a rebuild.
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
REPO_ZIP = DELIVERY / "darkith-forge-repo.zip"
ONESHOT = DELIVERY / "darkith-one-shot.sh"
MARKER = b"\n__DARKITH_PAYLOAD_BELOW__\n"
PREFIX = "darkith-forge/"

# repo path -> project file
WEBAPP = {
    "webapp/darkith-forge.html": ROOT / "darkith forge.html",
    "webapp/savf.html": ROOT / "savf.html",
    "webapp/savf.py": ROOT / "savf.py",
    "webapp/zipalign.py": ROOT / "zipalign.py",
    "webapp/omega.html": ROOT / "omega.html",
    "webapp/omega/exec-protocol.js": ROOT / "build" / "omega" / "exec-protocol.js",
    "webapp/omega/assistant.js": ROOT / "build" / "omega" / "assistant.js",
}
PROOF = "docs/darkith-forged-proof.apk"


def payload_zip() -> zipfile.ZipFile:
    data = ONESHOT.read_bytes()
    i = data.find(MARKER)
    if i < 0:
        raise SystemExit("[FATAL] payload marker not found in the one-shot")
    return zipfile.ZipFile(io.BytesIO(data[i + len(MARKER):]))


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build() -> int:
    if not REPO_ZIP.exists():
        raise SystemExit("[FATAL] no existing repo zip to seed from")
    base = zipfile.ZipFile(REPO_ZIP)
    pay = payload_zip()

    # repo-relative path -> bytes, seeded from the existing zip.
    entries: dict[str, bytes] = {
        n[len(PREFIX):]: base.read(n)
        for n in base.namelist()
        if n.startswith(PREFIX) and not n.endswith("/")
    }

    # 1. app/ is owned by the one-shot payload (current Kotlin, engine assets,
    #    release key/cert, arm64 toolchain libs).
    for n in pay.namelist():
        if n.startswith("app/") and not n.endswith("/"):
            entries[n] = pay.read(n)

    # 2. webapp/ is owned by the project's current single-file apps.
    for rel, src in WEBAPP.items():
        entries[rel] = src.read_bytes()

    # 3. the proof APK tracks delivery.
    proof = DELIVERY / "darkith-forged-proof.apk"
    if proof.exists():
        entries[PROOF] = proof.read_bytes()

    # 4. drop transient build residue that must never ship in a repo.
    drop = [n for n in entries if n.endswith((".bak", ".pyc", ".log", ".orig"))]
    for n in drop:
        del entries[n]

    tmp = REPO_ZIP.with_suffix(".zip.new")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in sorted(entries):
            z.writestr(PREFIX + rel, entries[rel])
    tmp.replace(REPO_ZIP)

    print(f"repo zip {REPO_ZIP.stat().st_size:,} B  entries {len(entries)}")
    print(f"  webapp/darkith-forge.html  sha {sha256(entries['webapp/darkith-forge.html'])[:16]}")
    print(f"  webapp/savf.html           sha {sha256(entries['webapp/savf.html'])[:16]}")
    print(f"  app/.../homekeeper.html    sha {sha256(entries['app/src/main/assets/homekeeper.html'])[:16]}")
    print(f"  jniLibs: {sorted(n.split('/')[-1] for n in entries if '/jniLibs/' in n)}")
    return 0


def check() -> int:
    # delivery/ zips are regenerable output that .gitignore forbids committing, so a
    # clean checkout has none. Absent is a skip, not a failure (same rule as
    # verify.py check_sync): the gate must pass from a clean clone.
    if not REPO_ZIP.exists():
        print("repo zip: absent (regenerable, not committed) — skip")
        return 0
    z = zipfile.ZipFile(REPO_ZIP)
    cur = (ROOT / "darkith forge.html").read_bytes()
    got = z.read(PREFIX + "webapp/darkith-forge.html")
    same = got == cur
    print(f"  {'OK  ' if same else 'STALE'} repo webapp/darkith-forge.html  {sha256(got)[:16]}")
    cur_savf = (ROOT / "savf.html").read_bytes()
    got_savf = z.read(PREFIX + "webapp/savf.html")
    same2 = got_savf == cur_savf
    print(f"  {'OK  ' if same2 else 'STALE'} repo webapp/savf.html  {sha256(got_savf)[:16]}")
    got_hk = z.read(PREFIX + "app/src/main/assets/homekeeper.html")
    same3 = got_hk == cur
    print(f"  {'OK  ' if same3 else 'STALE'} repo app/.../homekeeper.html  {sha256(got_hk)[:16]}")
    cur_omega = (ROOT / "omega.html").read_bytes()
    got_omega = z.read(PREFIX + "webapp/omega.html")
    same4 = got_omega == cur_omega
    print(f"  {'OK  ' if same4 else 'STALE'} repo webapp/omega.html  {sha256(got_omega)[:16]}")
    cur_proto = (ROOT / "build" / "omega" / "exec-protocol.js").read_bytes()
    got_proto = z.read(PREFIX + "webapp/omega/exec-protocol.js")
    same5 = got_proto == cur_proto
    print(f"  {'OK  ' if same5 else 'STALE'} repo webapp/omega/exec-protocol.js  {sha256(got_proto)[:16]}")
    libs = sorted(n.split("/")[-1] for n in z.namelist() if "/jniLibs/" in n)
    libs_ok = libs == ["libaapt2.so", "libzipalign.so"]
    print(f"  {'OK  ' if libs_ok else 'STALE'} repo jniLibs {libs}")
    key_ok = PREFIX + "app/src/main/assets/engine/release_key" in z.namelist()
    print(f"  {'OK  ' if key_ok else 'STALE'} repo carries release_key")
    ok = same and same2 and same3 and same4 and same5 and libs_ok and key_ok
    print("REPO ZIP: " + ("in sync" if ok else "STALE -- run without --check"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    return check() if args.check else build()


if __name__ == "__main__":
    sys.exit(main())
