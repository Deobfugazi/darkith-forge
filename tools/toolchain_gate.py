#!/usr/bin/env python3
"""toolchain_gate.py — a compile gate must not report a code defect it could not check.

Why this exists: kotlinc was installed at .tools/kotlinc, so controller_gate found it and
proceeded. It then failed with "harness did not compile, so the law was not run" — the
exact message a real Kotlin syntax error produces. The real cause was that `java` was not
on PATH: kotlinc is a shell wrapper that needs a JVM. Half a toolchain was indistinguishable
from a broken tree, and the report blamed the code.

This gate makes that state loud and separate. A toolchain is either whole (compiler AND its
runtime resolve) or it is absent (both missing -> every compile gate SKIPs honestly). Half a
toolchain is a defect in the environment and is reported as one.

  python3 tools/toolchain_gate.py --check   # exit 1 if a compiler has no runtime
  python3 tools/toolchain_gate.py --fix     # put the bundled JVM on PATH for this process

Exit: 0 = whole or wholly absent; 1 = half a toolchain; 2 = could not fix.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUNDLED_JDK_BIN = ROOT / ".tools" / "jdk-17.0.12+7" / "bin"


def java_available() -> bool:
    if shutil.which("java"):
        return True
    return (BUNDLED_JDK_BIN / "java").is_file()


def kotlinc_available() -> bool:
    if shutil.which("kotlinc"):
        return True
    return (ROOT / ".tools" / "kotlinc" / "bin" / "kotlinc").is_file()


def kotlinc_path() -> str | None:
    return shutil.which("kotlinc") or (
        str(ROOT / ".tools" / "kotlinc" / "bin" / "kotlinc")
        if (ROOT / ".tools" / "kotlinc" / "bin" / "kotlinc").is_file() else None
    )


def kotlinc_runs() -> tuple[bool, str]:
    """Probe the compiler by running it. Existence is not the question; execution is."""
    exe = kotlinc_path()
    if not exe:
        return False, "kotlinc absent"
    try:
        p = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"kotlinc could not be executed: {e}"
    out = (p.stdout or "") + (p.stderr or "")
    if "command not found" in out or "No such file" in out:
        return False, "kotlinc needs a JVM that is not on PATH"
    # kotlinc -version exits non-zero on some builds while still printing its banner.
    if "kotlin" in out.lower():
        return True, out.strip().splitlines()[0] if out.strip() else "kotlinc ok"
    return False, f"kotlinc produced no version banner: {out.strip()[:120]}"


def main(argv: list[str]) -> int:
    mode = "--fix" if "--fix" in argv else "--check"

    if not kotlinc_available():
        # No kotlinc means the compile gates cannot run — that is a SKIP, and a skip is never
        # a pass (SPI-31). Reporting PASS here would assert a toolchain that is not present,
        # which is the single most dangerous false green in a project whose whole build is a
        # kotlinc chain.
        print("toolchain_gate: SKIP — kotlinc is not installed, so no compile gate ran; "
              "the absence of a compiler is not evidence of a compiling tree")
        return 3

    ok, why = kotlinc_runs()
    if ok:
        print(f"toolchain_gate: PASS — kotlinc runs ({why})")
        return 0

    if mode == "--check":
        print(f"toolchain_gate: FAIL — {why}")
        print("  a compile gate will report 'harness did not compile', which reads as a")
        print("  code defect and is not one")
        print("  remedy: python3 tools/toolchain_gate.py --fix, or export a JDK on PATH")
        return 1

    if not (BUNDLED_JDK_BIN / "java").is_file():
        print("toolchain_gate: FAIL — no bundled JVM to point at")
        return 2
    os.environ["PATH"] = str(BUNDLED_JDK_BIN) + os.pathsep + os.environ.get("PATH", "")
    ok2, why2 = kotlinc_runs()
    if ok2:
        print(f"toolchain_gate: FIXED — prepended {BUNDLED_JDK_BIN}; kotlinc runs ({why2})")
        print("  note: this affects this process only; tools/ci.sh exports it for the whole run")
        return 0
    print(f"toolchain_gate: FAIL — still not runnable after fix: {why2}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
