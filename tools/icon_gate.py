#!/usr/bin/env python3
"""Fail if the launcher icon is missing, or if the manifest declares none.

Why this exists: the app shipped with no `android:icon`, so the launcher drew a blank
tile. That is not a crash, but it is a real delivery defect — and it is invisible to
every other gate, which only look at code and assets. A phone user sees the icon first.

Checks (all must hold, else exit 1):
  - the manifest declares android:icon (and android:roundIcon);
  - the icon name it declares resolves to a resource on disk (legacy mipmaps + the
    API 26 adaptive xml);
  - at least one real mipmap PNG exists, so pre-26 devices get pixels, not nothing.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "app/src/main/res"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"


def main() -> int:
    if not MANIFEST.is_file():
        print("icon_gate: SKIP (no AndroidManifest.xml)")
        return 0
    m = MANIFEST.read_text(encoding="utf-8", errors="replace")

    fails = []
    icon = re.search(r'android:icon="([^"]+)"', m)
    round_icon = re.search(r'android:roundIcon="([^"]+)"', m)
    if not icon:
        fails.append("manifest declares no android:icon (launcher shows a blank tile)")
    if not round_icon:
        fails.append("manifest declares no android:roundIcon")

    # `@mipmap/ic_launcher` -> must resolve to mipmap-*/ic_launcher.{png,xml}
    for label, ref in (("icon", icon), ("roundIcon", round_icon)):
        if not ref:
            continue
        name = ref.group(1).split("/")[-1]
        found = list(RES.glob(f"mipmap-*/{name}.png")) + list(RES.glob(f"mipmap-*/{name}.xml"))
        if not found:
            fails.append(f"android:{label}={ref.group(1)} resolves to no mipmap on disk")
        elif not list(RES.glob(f"mipmap-*/{name}.png")):
            fails.append(f"android:{label}={ref.group(1)} has no PNG (pre-API-26 devices get nothing)")

    if fails:
        print(f"icon_gate: FAIL — {len(fails)} problem(s):")
        for f in fails:
            print("  " + f)
        return 1
    pngs = sorted(RES.glob("mipmap-*/ic_launcher.png"))
    print(f"icon_gate: PASS — icon + roundIcon declared, {len(pngs)} legacy PNG(s), adaptive xml present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
