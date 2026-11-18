#!/usr/bin/env python3
"""inject_updater.py — inject the update watcher into the app UI surface.

The fused webapp (`darkith forge.html`) gets the watcher from build-forge.py.
The APK's own UI (`app/src/main/assets/homekeeper.html`) is a separate surface
loaded by HomekeeperActivity, so it needs the same block — injected between
stable markers so re-running is byte-identical (idempotent, like every other
injector here).

The watcher's LOCAL version stamp comes from VERSION.json, so the surface
always carries the repo's true version and can compare it against the live
remote manifest even with the radio off.

Run:  python3 build/inject_updater.py [--check]
      --check  verify the surface is current without writing (the CI gate)
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
UPDATER = ROOT / "build" / "updater.js"
VERSION_JSON = ROOT / "VERSION.json"
SURFACES = [ROOT / "app/src/main/assets/homekeeper.html"]

BEGIN = "<!-- BEGIN GENERATED update-watcher (build/inject_updater.py) — DO NOT EDIT -->"
END = "<!-- END GENERATED update-watcher -->"


def block() -> str:
    man = json.loads(VERSION_JSON.read_text(encoding="utf-8"))
    js = UPDATER.read_text(encoding="utf-8")
    local = {
        "versionCode": man["versionCode"],
        "versionName": man["versionName"],
        "surfaceVersion": man.get("surfaceVersion", ""),
    }
    js = re.sub(r"var LOCAL = \{[^}]*\};",
                "var LOCAL = " + json.dumps(local, separators=(",", ":")) + ";", js, count=1)
    js = js.replace("</script", "<\\/script")
    return f"{BEGIN}\n<script>\n{js}\n</script>\n{END}"


def inject(html: str, payload: str) -> str:
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    if pattern.search(html):
        return pattern.sub(lambda _: payload, html, count=1)
    for anchor in ("</body>", "</html>"):
        i = html.rfind(anchor)
        if i != -1:
            return html[:i] + payload + "\n" + html[i:]
    return html + "\n" + payload + "\n"


def main() -> int:
    check = "--check" in sys.argv[1:]
    if not UPDATER.is_file() or not VERSION_JSON.is_file():
        print("inject_updater: FAIL — build/updater.js or VERSION.json missing")
        return 1
    payload = block()
    stale = []
    for s in SURFACES:
        original = s.read_text(encoding="utf-8")
        updated = inject(original, payload)
        if updated != original:
            stale.append(s.name)
            if not check:
                s.write_text(updated, encoding="utf-8")
    if check:
        if stale:
            print(f"inject_updater: FAIL — {len(stale)} surface(s) not current: {stale}")
            return 1
        print(f"inject_updater: PASS — {len(SURFACES)} surface(s) carry the current watcher")
        return 0
    print(f"inject_updater: {len(stale)} surface(s) updated; {len(SURFACES)} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
