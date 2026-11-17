#!/usr/bin/env python3
"""s19_compile.py — the reproducible form of §19 MUST-11 ("the compile is the proof").

Runs the project's real raw chain over the authoritative app tree:

    aapt2 compile res -> aapt2 link --java (generates R.java) -> kotlinc

against android.jar plus the build dependency jars (apksig, ...). This is the
same order build.sh uses; no Gradle, no AGP (SPI-1).

Exit 0 only when kotlinc reports zero errors. Every dependency is located via an
environment variable with a sensible default, so the same script runs on the
phone (Termux), on CI, and on a desktop:

    ANDROID_JAR  platform android.jar        (default /tmp/android.jar)
    EXTRA_CP     colon-separated dep jars    (default /tmp/apksig.jar)
    KOTLINC      kotlinc executable          (default: kotlinc on PATH)
    AAPT2        aapt2 executable            (default: aapt2 on PATH)

When the toolchain is absent this exits 2 with a clear "cannot prove" message:
a missing tool is a SKIP, never a green.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
TREE = ROOT / "app/src/main/java/com/darkith/transliaison"
RES = ROOT / "app/src/main/res"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"


def main() -> int:
    android_jar = os.environ.get("ANDROID_JAR", "/tmp/android.jar")
    extra_cp = os.environ.get("EXTRA_CP", "/tmp/apksig.jar")
    kotlinc = os.environ.get("KOTLINC") or shutil.which("kotlinc")
    aapt2 = os.environ.get("AAPT2") or shutil.which("aapt2")

    if not TREE.is_dir():
        print("S19-COMPILE: SKIP — no app source tree")
        return 2
    if not (kotlinc and pathlib.Path(android_jar).exists()):
        print(f"S19-COMPILE: SKIP — need kotlinc + android.jar "
              f"(kotlinc={kotlinc or 'absent'}, android.jar={android_jar})")
        return 2

    kt = sorted(str(p) for p in TREE.rglob("*.kt"))
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        cp = [android_jar] + [j for j in extra_cp.split(os.pathsep) if j]
        rjava = None

        # R.java is a build product: generate it exactly as build.sh does, or the
        # gate cries wolf on "unresolved reference 'R'" (SPI-22).
        if aapt2 and RES.is_dir() and MANIFEST.exists():
            rc = td / "rc"; rc.mkdir()
            gen = td / "gen"; gen.mkdir()
            c = subprocess.run([aapt2, "compile", "--dir", str(RES), "-o", str(rc / "res.zip")],
                               capture_output=True, text=True)
            if c.returncode == 0:
                l = subprocess.run([aapt2, "link", "-o", str(rc / "g.apk"), "-I", android_jar,
                                    "--manifest", str(MANIFEST), str(rc / "res.zip"),
                                    "--java", str(gen), "--min-sdk-version", "24",
                                    "--target-sdk-version", "34", "--auto-add-overlay"],
                                   capture_output=True, text=True)
                if l.returncode == 0:
                    found = list(gen.rglob("R.java"))
                    rjava = str(found[0]) if found else None

        cmd = [kotlinc, "-J-Xmx4g", "-cp", os.pathsep.join(cp),
               "-jvm-target", "1.8", "-nowarn", "-d", str(td / "out")] + kt
        if rjava:
            cmd.append(rjava)
        r = subprocess.run(cmd, capture_output=True, text=True)

    errs = [ln for ln in r.stderr.splitlines() if "error:" in ln]
    if r.returncode == 0 and not errs:
        print(f"S19-COMPILE: PASS — {len(kt)} files, 0 errors"
              f"{' (+R.java)' if rjava else ' (no R.java: aapt2 absent)'}")
        return 0
    print(f"S19-COMPILE: FAIL — {len(errs)} error(s):")
    for ln in errs[:20]:
        print("   " + ln)
    return 1


if __name__ == "__main__":
    sys.exit(main())
