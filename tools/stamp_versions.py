#!/usr/bin/env python3
"""Stamp the ONE version of record (VERSION.json) into every terminal surface.

Failure mode this kills: the app shipped as 1.2.0-omega but `darkterm.js`/
`darktools.js`/`termkit.bundle.js` each carried their own hardcoded
`var VERSION = "1.0.0" | "2.0.0" | "2.1.0"`, so the terminal the Operator opens
reported a version that has nothing to do with what was installed. The update
watcher compared versionCode, the terminal compared its own string — two truths.

This makes VERSION.json.versionName the single truth. Run before packaging, or
`--check` in CI to fail the moment a surface drifts.
"""
import json
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "VERSION.json"

# Every file that carries a self-reported terminal/engine version.
TARGETS = [
    "app/src/main/assets/vendor/darkterm.js",
    "app/src/main/assets/vendor/darktools.js",
    "app/src/main/assets/darkith_ui.html",
    "app/src/main/assets/savf_core.html",
    "delivery/termkit.bundle.js",
    "darkith forge.html",
    "darkith home forge.html",
    "darkith-inscriber.html",
]

VAR_RE = re.compile(r'(var VERSION = ")([^"]*)(")')


def version_name() -> str:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["versionName"]


def main() -> int:
    check = "--check" in sys.argv[1:]
    want = version_name()
    drift = []
    changed = []
    for rel in TARGETS:
        p = ROOT / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        found = [m.group(2) for m in VAR_RE.finditer(text)]
        if not found:
            continue
        if check:
            bad = [v for v in found if v != want]
            if bad:
                drift.append(f"{rel}: {sorted(set(bad))} != {want}")
            continue
        new = VAR_RE.sub(lambda m: m.group(1) + want + m.group(3), text)
        if new != text:
            p.write_text(new, encoding="utf-8")
            changed.append(f"{rel}: {sorted(set(found))} -> {want}")

    if check:
        if drift:
            print("version_surface_gate: FAIL — surfaces disagree with VERSION.json")
            for d in drift:
                print("   " + d)
            return 1
        print(f"version_surface_gate: PASS — every terminal surface reports {want}")
        return 0

    for c in changed:
        print("  stamped " + c)
    print(f"stamp_versions: {len(changed)} surface(s) stamped to {want}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
