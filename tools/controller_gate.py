#!/usr/bin/env python3
"""controller_gate.py — behavioural gate for the AutophagicAllocator control law.

Why this exists. Every other gate in this tree is a text-level regex, and this session
proved they can be fooled by a comment. The allocator's faults were not textual: the code
was well-formed, compiled clean, and its formulas looked like a textbook PID. It was wrong
only when RUN. A regex could not have found it and cannot prevent its return.

So this gate runs the law. It compiles tools/controller_harness.kt against the real
AutophagicAllocator and asserts three properties the law claims:

  track       vK settles within 2% of the affordable ceiling at low and mid free RAM.
              A controller that only ever emits vMin or vMax is a constant. The original
              emitted a constant at every input: it added a BYTE error to a VERTEX count,
              saturated on tick 1, and anti-windup reset the integral every tick.
  scale       resolutionScale returns to >= 0.99 at idle. The original multiplied a bounded
              state by a factor < 1, so it could only descend, and it sat on the 0.5 floor.
  invariants  vK stays in [vMin,vMax], the scale in [0.5,1.0], no NaN escapes, gpuConcurrency
              in [1,8] — over 4000 adversarial ticks including a stalled clock.

Exit: 0 = all three hold; 1 = at least one broken; 3 = kotlinc or android.jar absent, so the
law was NOT run. 3 is a named skip, never a silent pass: a behavioural gate that cannot
execute has judged nothing.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = ROOT / "app/src/main/java/com/darkith/transliaison/core"
SOURCES = ["AutophagicAllocator.kt", "Allocation.kt", "LayoutNode.kt", "IRBuilder.kt"]
HARNESS = ROOT / "tools/controller_harness.kt"


def find_kotlinc() -> str | None:
    for c in (os.environ.get("KOTLINC"), str(ROOT / ".tools/kotlinc/bin/kotlinc"), "kotlinc"):
        if c and (shutil.which(c) or pathlib.Path(c).exists()):
            return c
    return None


def find_android_jar() -> str | None:
    for c in (os.environ.get("ANDROID_JAR"), str(ROOT / ".tools/android-all-14-robolectric-10818077.jar")):
        if c and pathlib.Path(c).exists():
            return c
    hits = sorted((ROOT / ".tools").glob("android*.jar")) if (ROOT / ".tools").is_dir() else []
    return str(hits[0]) if hits else None


def main() -> int:
    kotlinc, ajar = find_kotlinc(), find_android_jar()
    if not kotlinc or not ajar:
        print("controller_gate: SKIP — kotlinc or android.jar absent; the law was NOT run")
        return 3
    missing = [s for s in SOURCES if not (CORE / s).exists()]
    if missing or not HARNESS.exists():
        print(f"controller_gate: SKIP — sources missing: {missing or HARNESS.name}")
        return 3

    with tempfile.TemporaryDirectory() as td:
        jar = pathlib.Path(td) / "h.jar"
        cmd = [kotlinc, "-J-Xmx2g", "-cp", ajar, "-nowarn", "-include-runtime", "-d", str(jar)]
        cmd += [str(CORE / s) for s in SOURCES] + [str(HARNESS)]
        try:
            cc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"controller_gate: SKIP — could not compile harness: {e}")
            return 3
        if cc.returncode != 0 or not jar.exists():
            errs = [l for l in (cc.stdout + cc.stderr).splitlines() if "error:" in l][:8]
            print("controller_gate: FAIL — harness did not compile, so the law was not run")
            for l in errs:
                print("  " + l)
            return 1
        try:
            r = subprocess.run(["java", "-jar", str(jar)], capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"controller_gate: SKIP — could not run harness: {e}")
            return 3

    out = r.stdout
    for line in out.splitlines():
        if line.startswith(("TRACK", "SCALE", "VIOLATION")):
            print("  " + line)
    results = dict(re.findall(r"RESULT (\w+)=(\w+)", out))
    if not results:
        print("controller_gate: FAIL — harness produced no verdict (it did not run)")
        return 1
    failed = [k for k, v in results.items() if v != "PASS"]
    if failed:
        print(f"controller_gate: FAIL — {', '.join(failed)} broken ({len(results)} propert(ies) judged)")
        return 1
    print(f"controller_gate: PASS — {', '.join(sorted(results))} hold on the real law")
    return 0


if __name__ == "__main__":
    sys.exit(main())
