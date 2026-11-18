#!/usr/bin/env python3
"""forge_child_gate.py — C2: a forged child APK must be a working, self-forging app.

The forge (`HomekeeperBridge.forgeNative` -> `ChimeraBuilder.forgeChimera`) stamps every
child from `assets/engine/AndroidManifest.tpl.xml` and `assets/engine/template.dex`. Two
things make a child *work* rather than merely build:

  F-01 extractNativeLibs=true in the template. The forge execs the handcoded native tools
       (libaapt2.so, libzipalign.so) from nativeLibraryDir. Without extractNativeLibs=true
       Android leaves nativeLibraryDir empty, so a forged app cannot build a child of its
       own, and install_gate I-07 is OPEN ("App not installed" class). The host manifest sets
       it for exactly this reason (delivery gate L-17); the child template must match.

  F-02 both builders ship the native tools STORED under lib/<abi>/. A child that does not
       carry libaapt2.so / libzipalign.so is a dead end: it installs but can never forge.

  F-03 the template names the launcher activity, so a forged child has an icon to tap.

A tree that fails F-01/F-02 compiles clean and passes every source law, yet ships children
that cannot forge — a silent C2 regression. This gate names it.

Usage: python3 tools/forge_child_gate.py
Exit:  0 = all forge-child laws hold.  non-zero = at least one is open.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL = ROOT / "app/src/main/assets/engine/AndroidManifest.tpl.xml"
CHIMERA = ROOT / "app/src/main/java/com/darkith/transliaison/ChimeraBuilder.kt"
BUILDENGINE = ROOT / "app/src/main/java/com/darkith/transliaison/BuildEngine.kt"

# A builder "ships the native tools" if it enumerates nativeLibraryDir's *.so and writes them
# under lib/<abi>/ (ChimeraBuilder writes the zip entry directly; BuildEngine via its extras list).
SHIP_MARKERS = (
    re.compile(r'lib/\$\{abi\.name\}'),
    re.compile(r'"lib/\$\{abi\.name\}/\$\{so\.name\}"'),
    re.compile(r'libaapt2\.so'),
)

OPEN = 0


def rec(law: str, ok: bool, detail: str) -> None:
    global OPEN
    if not ok:
        OPEN += 1
    print(f"  {'CLOSED' if ok else 'OPEN  '} {law:28} {detail}")


def ships_native(path: pathlib.Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return any(m.search(text) for m in SHIP_MARKERS)


def main() -> int:
    print("== FORGE CHILD GATE — a forged child must be a working, self-forging app ==")
    if not TPL.is_file():
        print(f"forge_child_gate: FAIL - missing {TPL.relative_to(ROOT)}", file=sys.stderr)
        return 1
    tpl = TPL.read_text(encoding="utf-8")

    rec("F-01-extract-native-libs", 'android:extractNativeLibs="true"' in tpl,
        "child template sets extractNativeLibs=true" if 'android:extractNativeLibs="true"' in tpl
        else "missing -> nativeLibraryDir stays empty; child cannot exec the forge tools")

    rec("F-02-chimera-ships-natives", ships_native(CHIMERA),
        "ChimeraBuilder ships lib/<abi>/*.so" if ships_native(CHIMERA)
        else "ChimeraBuilder does not ship lib/<abi>/*.so -> forged child cannot forge")

    rec("F-03-buildengine-ships-natives", ships_native(BUILDENGINE),
        "BuildEngine ships lib/<abi>/*.so" if ships_native(BUILDENGINE)
        else "BuildEngine does not ship lib/<abi>/*.so -> forged child cannot forge")

    launcher = ('android.intent.action.MAIN' in tpl and 'android.intent.category.LAUNCHER' in tpl
                and 'com.darkith.transliaison.HomekeeperActivity' in tpl)
    rec("F-04-launcher-activity", launcher,
        "template declares a MAIN/LAUNCHER activity" if launcher
        else "template has no MAIN/LAUNCHER HomekeeperActivity -> child has no icon to tap")

    if OPEN:
        print(f"forge_child_gate: FAIL - {OPEN} forge-child law(s) OPEN")
        return 1
    print("forge_child_gate: PASS - forged children install and can forge their own")
    return 0


if __name__ == "__main__":
    sys.exit(main())
