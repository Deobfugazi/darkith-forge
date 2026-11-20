#!/usr/bin/env python3
"""dex-link gate — the check that would have caught the launch crash.

The shipped APK's classes.dex REFERENCED kotlin/jvm/internal/Intrinsics and
com/android/apksig/ApkSigner while DEFINING neither. On the phone ART throws
NoClassDefFoundError the moment the launcher activity touches its own Companion,
so the app died before the UI painted — and every "green" test passed, because
none of them looked inside the dex.

This gate parses every classes*.dex in an APK and fails if any referenced type
that must come from the app (anything outside the platform namespaces) is not
defined in the APK. Run it on every built APK, in CI, before publishing.

Usage:
    python3 tools/dex_link_gate.py app-signed.apk [more.apk ...]
With no args it checks the default APKs if they exist.
"""
import struct
import sys
import zipfile
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Types supplied by the platform (ART / android.jar) — never bundled by the app.
PLATFORM_PREFIXES = (
    "Ljava/", "Ljavax/", "Landroid/", "Ldalvik/", "Lorg/json/",
    "Lorg/w3c/", "Lorg/xml/", "Lorg/apache/", "Lorg/ietf/",
)


def read_dex_types(blob: bytes):
    def u4(o):
        return struct.unpack_from("<I", blob, o)[0]

    def uleb(o):
        r = 0; s = 0
        while True:
            b = blob[o]; o += 1; r |= (b & 0x7F) << s
            if not (b & 0x80):
                break
            s += 7
        return r, o

    str_size, str_off = u4(56), u4(60)
    type_size, type_off = u4(64), u4(68)
    cls_size, cls_off = u4(96), u4(100)

    def string_at(i):
        o = u4(str_off + i * 4)
        ln, o = uleb(o)
        end = blob.index(b"\x00", o)
        return blob[o:end].decode("utf-8", "replace")

    strings = [string_at(i) for i in range(str_size)]
    types = [strings[u4(type_off + i * 4)] for i in range(type_size)]
    defined = {types[u4(cls_off + i * 32)] for i in range(cls_size)}
    referenced = {t for t in types if t.startswith("L") and t.endswith(";")}
    return defined, referenced


def check_apk(path: pathlib.Path):
    z = zipfile.ZipFile(path)
    defined, referenced = set(), set()
    dex_names = [n for n in z.namelist() if n.startswith("classes") and n.endswith(".dex")]
    if not dex_names:
        return [f"{path.name}: no classes*.dex"]
    for n in dex_names:
        d, r = read_dex_types(z.read(n))
        defined |= d
        referenced |= r
    missing = sorted(
        t for t in referenced
        if not t.startswith(PLATFORM_PREFIXES) and t not in defined
    )
    return missing


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        args = [str(p) for p in [
            ROOT / "app-signed.apk",
            ROOT / "build" / "termkit_omega" / "app-signed.apk",
        ] if p.exists()]
    if not args:
        # Build artifact, not a tracked input: exit 3 so CI shows SKIP, never PASS.
        print("dex_link_gate: SKIP — no APK to check")
        return 3

    failed = False
    for a in args:
        p = pathlib.Path(a)
        if not p.exists():
            print(f"dex_link_gate: SKIP — {a} missing")
            continue
        missing = check_apk(p)
        if missing:
            failed = True
            print(f"dex_link_gate: FAIL — {p.name} references {len(missing)} class(es) it does not define")
            for t in missing[:40]:
                print("   " + t)
            if len(missing) > 40:
                print(f"   ... and {len(missing) - 40} more")
        else:
            print(f"dex_link_gate: PASS — {p.name} links cleanly (every non-platform reference is defined)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
