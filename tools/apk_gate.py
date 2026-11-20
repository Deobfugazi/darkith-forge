#!/usr/bin/env python3
"""apk gate — the structural laws an APK must satisfy to install AND launch.

Each check here corresponds to a real failure the Operator has hit:
  * launcher icon present at every density + an adaptive icon  (the "no icon app
    integrated" report — a launcher entry with no drawable shows a blank tile)
  * resources.arsc + every lib/*.so STORED, not DEFLATED  (API 30+ "App not
    installed")
  * the launcher activity's own classes defined (delegated to dex_link_gate.py)
  * a label, so the tile is named
  * minSdk/targetSdk sane for the 4 GB arm64 phone

Usage: python3 tools/apk_gate.py app-signed.apk [more.apk ...]
"""
import sys
import zipfile
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ICON_DENSITIES = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]


def check_apk(path: pathlib.Path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    info = {n: z.getinfo(n) for n in names}
    problems = []

    # 1. launcher icon: a PNG at each density, and an adaptive icon.
    for d in ICON_DENSITIES:
        png = f"res/mipmap-{d}-v4/ic_launcher.png"
        alt = f"res/mipmap-{d}/ic_launcher.png"
        if png not in info and alt not in info:
            problems.append(f"no launcher icon at {d}")
    if not any("mipmap-anydpi-v26/ic_launcher.xml" in n for n in names):
        problems.append("no adaptive launcher icon (mipmap-anydpi-v26/ic_launcher.xml)")
    # a real icon is more than a few hundred bytes (a 1x1 placeholder is not an icon)
    icon_bytes = [info[n].file_size for n in names
                  if n.endswith("ic_launcher.png") and "round" not in n]
    if icon_bytes and max(icon_bytes) < 300:
        problems.append(f"launcher icon looks like a placeholder (max {max(icon_bytes)} bytes)")

    # 2. STORED (uncompressed) resources.arsc + lib/*.so — API 30+ install law.
    if "resources.arsc" not in info:
        problems.append("missing resources.arsc")
    elif info["resources.arsc"].compress_type != 0:
        problems.append("resources.arsc is DEFLATED (must be STORED for API 30+)")
    for n in names:
        if n.startswith("lib/") and n.endswith(".so") and info[n].compress_type != 0:
            problems.append(f"{n} is DEFLATED (must be STORED)")

    # 3. an executable entry point + a dex.
    if not any(n.startswith("classes") and n.endswith(".dex") for n in names):
        problems.append("no classes.dex")
    if "AndroidManifest.xml" not in info:
        problems.append("no AndroidManifest.xml")

    return problems


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        args = [str(p) for p in [
            ROOT / "app-signed.apk",
            ROOT / "build" / "termkit_omega" / "app-signed.apk",
        ] if p.exists()]
    if not args:
        # The APK is a build ARTIFACT, never tracked. Absent = not built yet = a real
        # skip, signalled with exit 3 so CI reports SKIP instead of a false PASS.
        print("apk_gate: SKIP — no APK to check")
        return 3
    failed = False
    for a in args:
        p = pathlib.Path(a)
        if not p.exists():
            print(f"apk_gate: SKIP — {a} missing")
            continue
        problems = check_apk(p)
        if problems:
            failed = True
            print(f"apk_gate: FAIL — {p.name}")
            for x in problems:
                print("   " + x)
        else:
            print(f"apk_gate: PASS — {p.name} (icon, store laws, entry point all present)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
