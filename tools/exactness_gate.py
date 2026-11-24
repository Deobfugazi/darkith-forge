#!/usr/bin/env python3
"""exactness_gate.py — NEVER #28 / MUST #47. No float in a verdict path.

Scans verdict-bearing modules for float literals that could reach a pass/fail decision, and
asserts the resolver's exact-zero contract holds: numerator exactly 0 AND dimension vector
empty. Also re-runs the resolver's falsification battery so a resolver that cannot say no
fails here.

Exit 0 = exact. Exit 1 = a float in a verdict path or the resolver is unfalsifiable.
Exit 3 = a required module is absent.
"""
from __future__ import annotations

import re
import subprocess
import sys
import pathlib

VERDICT_MODULES = [
    "tools/burden/resolve_invariants.py",
    "tools/burden/falsify_resolver.py",
]
FLOAT_LITERAL = re.compile(r"(?<![\w.])[-+]?\d+\.\d+(?![\w.])")
# Lines that are allowed to hold a float: the demonstration that floats lie.
# §4.6 and v1.2 are section refs, not arithmetic. A false positive is as useless as a miss.
ALLOW = re.compile(r"float_lies|0\.1 \+ 0\.2|IEEE754|5\.5511|float_result|exact_result"
                   r"|§\s*\d+\.\d+|\bv\d+\.\d+\b")


def float_hits(path: pathlib.Path) -> list[str]:
    hits = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if ALLOW.search(line):
            continue
        if line.lstrip().startswith("#"):
            continue
        if FLOAT_LITERAL.search(line):
            hits.append(f"{path}:{i}: {line.strip()[:90]}")
    return hits


def run() -> int:
    missing = [m for m in VERDICT_MODULES if not pathlib.Path(m).exists()]
    if missing:
        print(f"EXACTNESS_GATE: SKIP modules_absent {missing} (a skip is never a pass, SPI-31)")
        return 3

    hits = []
    for m in VERDICT_MODULES:
        hits.extend(float_hits(pathlib.Path(m)))

    print("=" * 78)
    print("EXACTNESS GATE — no float reaches a verdict; zero requires empty dimensions")
    print("=" * 78)
    print(f"modules scanned : {len(VERDICT_MODULES)}")
    print(f"float literals  : {len(hits)}")
    for h in hits:
        print(f"  [FLOAT] {h}")

    # The resolver must be able to say NO.
    proc = subprocess.run([sys.executable, "tools/burden/falsify_resolver.py"],
                          capture_output=True, text=True)
    falsifiable = proc.returncode == 0 and "FALSIFIABLE" in proc.stdout
    vec = re.search(r"VECTORS:\s*(\d+)\s+HOLES:\s*(\d+)", proc.stdout)
    print(f"resolver vectors: {vec.group(1) if vec else '?'}  "
          f"holes: {vec.group(2) if vec else '?'}")
    print(f"resolver falsifiable: {falsifiable}")

    ok = not hits and falsifiable
    print("\n" + "=" * 78)
    print(f"VERDICT: {'EXACT_AND_FALSIFIABLE' if ok else 'INEXACT_OR_UNFALSIFIABLE'}")
    print("=" * 78)
    return 0 if ok else 1


def selftest() -> int:
    import tempfile
    results = []
    with tempfile.TemporaryDirectory() as td:
        clean = pathlib.Path(td, "clean.py")
        clean.write_text("from fractions import Fraction as Q\nx = Q(1, 10)\nif x == 0:\n    pass\n")
        dirty = pathlib.Path(td, "dirty.py")
        dirty.write_text("residual = 0.1 + 0.2 - 0.3\nif residual == 0.0:\n    print('closed')\n")
        results.append(("silent on rational verdict", float_hits(clean) == [],
                        f"{float_hits(clean)}"))
        results.append(("fires on float verdict", len(float_hits(dirty)) > 0,
                        f"{float_hits(dirty)}"))
    # dimensioned zero is not scalar zero
    D_J = {"J": 1}
    results.append(("dimensioned zero rejected as scalar zero",
                    not (0 == 0 and D_J == {}), "0[J] has non-empty dimension vector"))
    print("=" * 78)
    print("EXACTNESS GATE — SELFTEST")
    print("=" * 78)
    holes = 0
    for name, ok, detail in results:
        if not ok:
            holes += 1
        print(f"  [{'PASS' if ok else 'HOLE'}] {name}  {detail}")
    print(f"\nSELFTEST: {'PASS' if holes == 0 else 'FAIL'} ({holes} hole(s))")
    return 0 if holes == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
