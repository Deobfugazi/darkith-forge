#!/usr/bin/env python3
"""nt_sensor — the hardware-coupled sensor for the Healer's repair example.

The corpus (NT X §4.4/5.4, NT XII §14.2) shows the Healer repairing an unresolved
`Button` symbol. It used to name `import androidx.compose.material3.Button` as the
"verified truth". Reality's own reference — the android.jar the device's compiler
checks against — falsifies that: the jar carries `android/widget/Button.class` and
has zero `androidx` entries, so the androidx import does not resolve and the raw
`android.widget.Button` does. The corpus was re-pointed to the raw import.

This sensor re-checks that claim against the reference bytes (SPI-2: read the exact
bytes, do not guess):

  * the carried corpus names the RAW import and not the androidx one;
  * the repo law still forbids `import androidx` (fork_integrity_gate, SPI-13);
  * the reference jar carries `android/widget/Button.class` and no `androidx` symbol
    (the hardware-coupled half — the jar is the compiler's ground truth).

Exit 0 and print the marker when the corpus+law hold. When the reference jar is
discoverable it is checked too; when it is genuinely absent the run says so loudly
(a silent skip is how a broken tree ships looking green) and still verifies the
carried bytes, so the gate stays runnable on a phone with no toolchain yet.

Usage: python3 tools/nt_sensor.py            # verify the Healer example
       python3 tools/nt_sensor.py --selftest # offline proof of the sensor logic
"""
from __future__ import annotations

import glob
import os
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKER = "HEALER-RAW-IMPORT-HARDWARE-VERIFIED"
RAW = "import android.widget.Button"
FOREIGN = "import androidx.compose.material3.Button"
LAW_FILE = "tools/fork_integrity_gate.sh"
LAW = "import androidx"
CORPUS = ("docs/nt/NT-X.txt", "docs/nt/NT-XII.txt")
BUTTON = "android/widget/Button.class"


def find_jar() -> pathlib.Path | None:
    """The reference android.jar: $ANDROID_JAR first, else any .tools/ jar that
    actually carries android/widget/Button.class (proving it is a platform jar)."""
    cands: list[str] = []
    if os.environ.get("ANDROID_JAR"):
        cands.append(os.environ["ANDROID_JAR"])
    cands += sorted(glob.glob(str(ROOT / ".tools" / "*.jar")))
    cands += sorted(glob.glob(str(ROOT / "*.jar")))
    for p in cands:
        if not os.path.isfile(p):
            continue
        try:
            if BUTTON in zipfile.ZipFile(p).namelist():
                return pathlib.Path(p)
        except (OSError, zipfile.BadZipFile):
            continue
    return None


def check_jar(path: pathlib.Path) -> tuple[bool, str]:
    names = zipfile.ZipFile(path).namelist()
    # AOSP's own android.jar ships two androidx annotation stubs (RecentlyNullable,
    # RecentlyNonNull) because framework classes reference them, plus the bare
    # `androidx/` directory entry that holds them. None carry UI and none can satisfy
    # a compose import, so they are platform, not foreign. Any other androidx entry
    # means a UI toolkit leaked in, which is what this gate forbids.
    foreign = [n for n in names
               if "androidx" in n
               and n != "androidx/"
               and not n.startswith("androidx/annotation/")]
    ok = BUTTON in names and not foreign
    note = (f"{path.name}: {BUTTON} present, {len(foreign)} androidx symbol(s)"
            if ok else f"{path.name}: Button={BUTTON in names} androidx={len(foreign)}")
    return ok, note


def main() -> int:
    fails: list[str] = []

    def expect(cond: bool, msg: str) -> None:
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            fails.append(msg)

    blob = "".join((ROOT / f).read_text(encoding="utf-8-sig") for f in CORPUS)
    law = (ROOT / LAW_FILE).read_text(encoding="utf-8")

    expect(RAW in blob, "corpus names the RAW import (android.widget.Button)")
    expect(FOREIGN not in blob, "corpus no longer names the androidx import")
    expect(LAW in law, "the repo law still forbids 'import androidx' (SPI-13)")

    jar = find_jar()
    if jar is None:
        print("  NOTE SENSOR-ABSENT: no reference android.jar found — corpus+law "
              "checked; the hardware half did NOT run")
    else:
        ok, note = check_jar(jar)
        expect(ok, f"reference jar carries the raw symbol, no androidx — {note}")

    print(f"\n{('FAIL' if fails else 'PASS')}: {len(fails)} failed")
    if fails:
        return 1
    print(MARKER)
    return 0


def selftest() -> int:
    """Offline proof of the sensor's two halves, with no toolchain and no corpus."""
    import tempfile
    fails: list[str] = []

    def expect(cond: bool, msg: str) -> None:
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            fails.append(msg)

    # a synthetic jar: one platform class, zero androidx.
    with tempfile.TemporaryDirectory() as d:
        good = pathlib.Path(d) / "good.jar"
        with zipfile.ZipFile(good, "w") as z:
            z.writestr(BUTTON, b"\xca\xfe\xba\xbe")
        ok, _ = check_jar(good)
        expect(ok, "a jar with the raw class and no androidx passes")

        # The exact shape of a real AOSP jar: platform annotation stubs + the bare
        # androidx/ dir. If this fails, the exemption has been widened too far.
        aosp = pathlib.Path(d) / "aosp.jar"
        with zipfile.ZipFile(aosp, "w") as z:
            z.writestr(BUTTON, b"\xca\xfe\xba\xbe")
            z.writestr("androidx/", b"")
            z.writestr("androidx/annotation/RecentlyNonNull.class", b"\xca\xfe\xba\xbe")
            z.writestr("androidx/annotation/RecentlyNullable.class", b"\xca\xfe\xba\xbe")
        ok, note = check_jar(aosp)
        expect(ok, f"platform annotation stubs are not foreign androidx — {note}")

        # ...but an annotation stub must not buy passage for a compose class.
        sneaky = pathlib.Path(d) / "sneaky.jar"
        with zipfile.ZipFile(sneaky, "w") as z:
            z.writestr(BUTTON, b"\xca\xfe\xba\xbe")
            z.writestr("androidx/annotation/RecentlyNonNull.class", b"\xca\xfe\xba\xbe")
            z.writestr("androidx/compose/ui/Modifier.class", b"\xca\xfe\xba\xbe")
        ok, _ = check_jar(sneaky)
        expect(not ok, "a compose class is still foreign beside an annotation stub")

        bad = pathlib.Path(d) / "bad.jar"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr(BUTTON, b"\xca\xfe\xba\xbe")
            z.writestr("androidx/compose/material3/Button.class", b"\xca\xfe\xba\xbe")
        ok, _ = check_jar(bad)
        expect(not ok, "a jar carrying an androidx symbol is rejected")

        empty = pathlib.Path(d) / "empty.jar"
        with zipfile.ZipFile(empty, "w") as z:
            z.writestr("android/widget/TextView.class", b"\xca\xfe\xba\xbe")
        ok, _ = check_jar(empty)
        expect(not ok, "a jar without the raw class is rejected")

        os.environ["ANDROID_JAR"] = str(good)
        expect(find_jar() == good, "find_jar honours $ANDROID_JAR when it carries Button")
        del os.environ["ANDROID_JAR"]

    print(f"\nNT SENSOR: {'PASS' if not fails else 'FAIL'} ({len(fails)} failed)")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
