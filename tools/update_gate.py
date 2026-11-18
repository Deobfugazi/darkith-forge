#!/usr/bin/env python3
"""update_gate.py — the version-truth + update-watcher wiring gate.

Asserts, from the repo's own files (no network, no build required):

  * VERSION.json parses and carries an integer versionCode + a versionName;
  * the fused page `darkith forge.html`, WHEN PRESENT, carries the SAME version
    in its embedded `var LOCAL = {...}` stamp — so a shipped page can never
    claim a version the repo does not, and the watcher can never alert on a
    phantom (it would otherwise compare against a stale number);
  * the app surface `app/src/main/assets/homekeeper.html` carries the same
    stamp (it is a tracked file, so this is a hard requirement);
  * the AndroidManifest versionName matches VERSION.json;
  * build/updater.js's default manifest + one-shot URLs match VERSION.json.

Exit 0 PASS, 1 FAIL.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERSION_JSON = ROOT / "VERSION.json"
UPDATER_JS = ROOT / "build" / "updater.js"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"
FORGE_OUT = ROOT / "darkith forge.html"        # generated; may be absent
APP_SURFACE = ROOT / "app/src/main/assets/homekeeper.html"

LOCAL_RE = re.compile(r'var LOCAL = (\{"versionCode".*?\});')


def stamp_of(text: str) -> dict | None:
    m = LOCAL_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def main() -> int:
    problems: list[str] = []

    if not VERSION_JSON.is_file():
        print("update_gate: FAIL — VERSION.json missing")
        return 1
    man = json.loads(VERSION_JSON.read_text(encoding="utf-8"))
    if not isinstance(man.get("versionCode"), int):
        problems.append("VERSION.json versionCode is not an integer")
    if not man.get("versionName"):
        problems.append("VERSION.json versionName is empty")
    want = {
        "versionCode": man.get("versionCode"),
        "versionName": man.get("versionName"),
        "surfaceVersion": man.get("surfaceVersion", ""),
    }

    # the app surface is tracked: its stamp is mandatory and must match.
    surface = APP_SURFACE.read_text(encoding="utf-8")
    got = stamp_of(surface)
    if got is None:
        problems.append(f"{APP_SURFACE.name}: no embedded LOCAL version stamp")
    elif got != want:
        problems.append(f"{APP_SURFACE.name}: stamp {got} != VERSION.json {want}")

    # the fused page is generated: check only when it exists.
    if FORGE_OUT.is_file():
        got2 = stamp_of(FORGE_OUT.read_text(encoding="utf-8"))
        if got2 is None:
            problems.append("darkith forge.html: no embedded LOCAL version stamp")
        elif got2 != want:
            problems.append(f"darkith forge.html: stamp {got2} != VERSION.json {want}")

    # AndroidManifest versionName must agree with the manifest of record.
    if MANIFEST.is_file():
        mvn = re.search(r'android:versionName="([^"]*)"', MANIFEST.read_text(encoding="utf-8"))
        if not mvn:
            problems.append("AndroidManifest.xml: no versionName")
        elif mvn.group(1) != man.get("versionName"):
            problems.append(f"AndroidManifest.xml versionName {mvn.group(1)} != {man.get('versionName')}")

    # updater.js default URLs must point where VERSION.json says.
    js = UPDATER_JS.read_text(encoding="utf-8")
    urls = man.get("manifest_urls") or ([man["manifest_url"]] if man.get("manifest_url") else [])
    for u in urls:
        if u not in js:
            problems.append(f"updater.js does not carry VERSION.json manifest url {u}")
    if man.get("manifest_url") and urls and urls[0] != man.get("manifest_url"):
        problems.append("VERSION.json manifest_url is not the first mirror in manifest_urls")
    if man.get("oneshot_url") and man["oneshot_url"] not in js:
        problems.append("updater.js does not carry VERSION.json oneshot_url")
    apks = man.get("apk_urls") or ([man["apk_url"]] if man.get("apk_url") else [])
    for u in apks:
        if u not in js:
            problems.append(f"updater.js does not carry VERSION.json apk url {u}")
    if man.get("apk_url") and apks and apks[0] != man.get("apk_url"):
        problems.append("VERSION.json apk_url is not the first mirror in apk_urls")

    if problems:
        print("update_gate: FAIL")
        for p in problems:
            print("  - " + p)
        return 1
    print(f"update_gate: PASS — version {man.get('versionName')} (code {man.get('versionCode')}) "
          f"agrees across VERSION.json, manifest, app surface and updater.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
