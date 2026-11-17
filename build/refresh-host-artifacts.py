#!/usr/bin/env python3
"""Refresh the host APK and the Termux one-shot with the current webapp.

The host app ships its UI as `assets/homekeeper.html`, a byte-for-byte copy of
the fused webapp. When that webapp is rebuilt the APK and the one-shot payload
must be refreshed too, or they ship a stale UI (exactly the drift this tool
exists to end).

Both artifacts are re-signed with the SAME key that already signs the host APK
(`assets/engine/release_key` / `release_cert`, CN=Darkith Release), so the
refreshed APK installs over an existing one without an uninstall.

  python3 build/refresh-host-artifacts.py           # rewrite both, verify
  python3 build/refresh-host-artifacts.py --check   # verify only, write nothing

Requires: apksigner + zipalign (Android build-tools) and a JDK on PATH, or the
paths in APKSIGNER / ZIPALIGN / JAVA_HOME.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DELIVERY = ROOT / "delivery"
WEBAPP = ROOT / "darkith home forge.html"     # the canonical shell (source of truth)
# The fused `darkith forge.html` is GENERATED from WEBAPP by build/build-forge.py; never
# treat it as source (that inversion is what made the two build scripts disagree).
APK = DELIVERY / "darkith-homekeeper-debug.apk"
ONESHOT = DELIVERY / "darkith-one-shot.sh"

APK_ASSET = "assets/homekeeper.html"
PAYLOAD_ASSET = "app/src/main/assets/homekeeper.html"
APK_KEY = "assets/engine/release_key"
PAYLOAD_KEY = "app/src/main/assets/engine/release_key"
APK_LIB_DIR = "lib/"
PAYLOAD_JNI_DIR = "app/src/main/jniLibs/"
MARKER = b"__DARKITH_PAYLOAD_BELOW__"
# Old signature entries: apksigner writes fresh ones.
SIG_PREFIX = "META-INF/"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: pathlib.Path) -> str:
    return sha256_bytes(p.read_bytes())


def pkcs8(key_der: bytes) -> bytes:
    """Normalise a private key to PKCS#8.

    `assets/engine/release_key` shipped as a bare RSAPrivateKey (PKCS#1), which
    every signer in this project rejects: apksigner says "Not an RSA, EC, or DSA
    private key" and the on-device `ApkSignerRunner` throws from
    `PKCS8EncodedKeySpec`. Converting it here fixes on-device forging and makes
    the shipped asset match the documented format.
    """
    from cryptography.hazmat.primitives import serialization
    k = serialization.load_der_private_key(key_der, password=None)
    return k.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def is_pkcs8(key_der: bytes) -> bool:
    try:
        from cryptography.hazmat.primitives import serialization
        serialization.load_der_private_key(key_der, password=None)
        # PKCS#1 also loads; distinguish by re-encoding round trip.
        return pkcs8(key_der) == key_der
    except Exception:
        return False


def find_tool(name: str, env: str) -> str:
    cand = os.environ.get(env)
    if cand and pathlib.Path(cand).exists():
        return cand
    hit = shutil.which(name)
    if hit:
        return hit
    for base in ("/tmp/bt/android-13", "/opt/android-sdk/build-tools", str(pathlib.Path.home())):
        p = pathlib.Path(base) / name
        if p.exists():
            return str(p)
    raise SystemExit(f"[FATAL] {name} not found (set {env})")


def is_sig_entry(name: str) -> bool:
    base = name[len(SIG_PREFIX):]
    return name.startswith(SIG_PREFIX) and (
        base == "MANIFEST.MF" or base.endswith((".SF", ".RSA", ".DSA", ".EC"))
    )


def replace_in_zip(src: pathlib.Path, dst: pathlib.Path, replacements: dict[str, bytes]) -> None:
    """Copy `src` to `dst`, swapping the payloads in `replacements`.

    Entry order and compression method are preserved; replacements whose names
    are not already present are appended. The old JAR signature trio is dropped
    so apksigner can write a fresh one. The archive is closed before anything
    else touches it, which is what keeps ZIP central directories consistent.
    """
    used = set()
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        for item in zin.infolist():
            if is_sig_entry(item.filename):
                continue
            data = replacements.get(item.filename)
            if data is None:
                data = zin.read(item.filename)
            else:
                used.add(item.filename)
            zout.writestr(item, data)
        for name, data in replacements.items():
            if name not in used:
                zout.writestr(name, data)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def refresh_apk(apksigner: str, zipalign: str, work: pathlib.Path, webapp: bytes) -> dict:
    with zipfile.ZipFile(APK) as z:
        key_fixed = pkcs8(z.read(APK_KEY))

    tmp = work / "base.apk"
    replace_in_zip(APK, tmp, {APK_ASSET: webapp, APK_KEY: key_fixed})

    aligned = work / "aligned.apk"
    r = run([zipalign, "-f", "-p", "4", str(tmp), str(aligned)])
    if r.returncode != 0:
        raise SystemExit(f"[FATAL] zipalign failed:\n{r.stdout}\n{r.stderr}")

    with zipfile.ZipFile(APK) as z:
        cert_der = z.read("assets/engine/release_cert")
        key_der = z.read("assets/engine/release_key")

    signed = work / "signed.apk"
    cert = work / "cert.pem"
    key = work / "key.pk8"
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    cert.write_bytes(x509.load_der_x509_certificate(cert_der).public_bytes(serialization.Encoding.PEM))
    key.write_bytes(pkcs8(key_der))
    r = run([apksigner, "sign", "--key", str(key), "--cert", str(cert),
             "--v1-signing-enabled", "true", "--v2-signing-enabled", "true",
             "--v3-signing-enabled", "true", "--out", str(signed), str(aligned)])
    if r.returncode != 0:
        raise SystemExit(f"[FATAL] apksigner failed:\n{r.stdout}\n{r.stderr}")

    shutil.move(str(signed), str(APK))
    return {"bytes": APK.stat().st_size, "sha256": sha256_file(APK)}


def native_libs_from_apk() -> dict[str, bytes]:
    """The host's arm64 toolchain libs, re-homed into the one-shot's jniLibs.

    ChimeraBuilder and BuildEngine read libaapt2.so / libzipalign.so from the
    app's nativeLibraryDir. A Gradle build only produces those when they are
    present under app/src/main/jniLibs, so the one-shot payload must carry them
    or the host it builds cannot forge.
    """
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(APK) as z:
        for name in z.namelist():
            if name.startswith(APK_LIB_DIR) and name.endswith(".so"):
                rel = name[len(APK_LIB_DIR):]          # arm64-v8a/libaapt2.so
                out[PAYLOAD_JNI_DIR + rel] = z.read(name)
    return out


def refresh_oneshot(work: pathlib.Path, webapp: bytes) -> dict:
    data = ONESHOT.read_bytes()
    i = data.find(b"\n" + MARKER + b"\n")
    if i < 0:
        raise SystemExit("[FATAL] payload marker not found in the one-shot")
    head = data[: i + len(MARKER) + 2]
    old_payload = work / "payload_old.zip"
    old_payload.write_bytes(data[i + len(MARKER) + 2 :])

    new_payload = work / "payload_new.zip"
    with zipfile.ZipFile(old_payload) as z:
        key_fixed = pkcs8(z.read(PAYLOAD_KEY))
    replacements = {PAYLOAD_ASSET: webapp, PAYLOAD_KEY: key_fixed}
    replacements.update(native_libs_from_apk())
    replace_in_zip(old_payload, new_payload, replacements)
    digest = sha256_file(new_payload)

    head = re.sub(
        rb'EXPECT_SHA256="[0-9a-f]{64}"',
        f'EXPECT_SHA256="{digest}"'.encode(),
        head,
        count=1,
    )
    ONESHOT.write_bytes(head + new_payload.read_bytes())
    ONESHOT.chmod(0o755)
    return {"bytes": ONESHOT.stat().st_size, "payload_sha256": digest, "sha256": sha256_file(ONESHOT)}


def payload_of(path: pathlib.Path) -> bytes:
    data = path.read_bytes()
    i = data.find(b"\n" + MARKER + b"\n")
    return data[i + len(MARKER) + 2 :]


def check(webapp_sha: str) -> int:
    ok = True
    with zipfile.ZipFile(APK) as z:
        got = sha256_bytes(z.read(APK_ASSET))
        key_ok = is_pkcs8(z.read(APK_KEY))
    same = got == webapp_sha
    ok &= same
    print(f"  {'OK  ' if same else 'STALE'} apk  assets/homekeeper.html  {got[:16]}")
    ok &= key_ok
    print(f"  {'OK  ' if key_ok else 'STALE'} apk  assets/engine/release_key is PKCS#8")
    pay = payload_of(ONESHOT)
    with zipfile.ZipFile(io.BytesIO(pay)) as z:
        got2 = sha256_bytes(z.read(PAYLOAD_ASSET))
        key_ok2 = is_pkcs8(z.read(PAYLOAD_KEY))
        libs = {n for n in z.namelist() if n.startswith(PAYLOAD_JNI_DIR) and n.endswith(".so")}
    same2 = got2 == webapp_sha
    ok &= same2
    print(f"  {'OK  ' if same2 else 'STALE'} oneshot app/src/main/assets/homekeeper.html  {got2[:16]}")
    ok &= key_ok2
    print(f"  {'OK  ' if key_ok2 else 'STALE'} oneshot engine/release_key is PKCS#8")
    with zipfile.ZipFile(APK) as z:
        want = {PAYLOAD_JNI_DIR + n[len(APK_LIB_DIR):] for n in z.namelist()
                if n.startswith(APK_LIB_DIR) and n.endswith(".so")}
    libs_ok = libs == want and bool(want)
    ok &= libs_ok
    print(f"  {'OK  ' if libs_ok else 'STALE'} oneshot carries native libs {sorted(n.split('/')[-1] for n in libs)}")
    exp = re.search(rb'EXPECT_SHA256="([0-9a-f]{64})"', ONESHOT.read_bytes())
    decl = exp.group(1).decode() if exp else "(none)"
    same3 = decl == sha256_bytes(pay)
    ok &= same3
    print(f"  {'OK  ' if same3 else 'STALE'} oneshot EXPECT_SHA256 matches payload  {decl[:16]}")
    print("  HOST ARTIFACTS:", "in sync" if ok else "STALE — run without --check")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    webapp = WEBAPP.read_bytes()
    webapp_sha = sha256_bytes(webapp)
    print(f"webapp: {WEBAPP.name} {len(webapp):,} B  sha256 {webapp_sha[:16]}")

    if args.check:
        return check(webapp_sha)

    apksigner = find_tool("apksigner", "APKSIGNER")
    zipalign = find_tool("zipalign", "ZIPALIGN")
    print(f"tools: {apksigner} | {zipalign}")

    with tempfile.TemporaryDirectory(prefix="darkith-refresh-") as td:
        work = pathlib.Path(td)
        a = refresh_apk(apksigner, zipalign, work, webapp)
        print(f"  apk     {a['bytes']:>12,} B  sha256 {a['sha256'][:16]}")
        o = refresh_oneshot(work, webapp)
        print(f"  oneshot {o['bytes']:>12,} B  payload {o['payload_sha256'][:16]}")

    r = run([apksigner, "verify", "--verbose", "--print-certs", str(APK)])
    print(r.stdout.strip() or r.stderr.strip())
    rc = check(webapp_sha)
    if r.returncode != 0:
        print("[FATAL] apksigner verify failed")
        return 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
