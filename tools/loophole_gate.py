#!/usr/bin/env python3
"""loophole_gate.py — fail if a gate can be satisfied without doing the work.

A loophole is a rule that reads as enforced but can be passed without enforcing anything.
The two measured classes in this repo (SPI-31, SPI-32):

  SKIP-AS-PASS   a gate prints SKIP and returns 0. CI's run() then prints PASS, so a check
                 that verified nothing is indistinguishable from one that verified the tree.
  VACUOUS-PASS   a gate iterates a set, finds it empty, and returns 0. "No inputs" is the
                 loudest result there is and it was being reported as the quietest.

Both are detected by reading the gate sources, because the defect is in the source, not in a
run. A gate that skips legitimately must signal exit 3.

Exit: 0 = no loopholes; 1 = at least one gate can pass without verifying.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

# `print("... SKIP ...")` and, within the next few statements, a bare `return 0`.
# SKIP must be a status token, not part of a hyphenated word: "skip-as-pass" in a PASS
# message is prose about this gate, not a gate skipping, and matching it made the scanner
# report itself.
SKIP_PRINT = re.compile(r'print\(\s*f?"[^"]*\bSKIP\b(?![-\w])', re.I)
RETURN_0 = re.compile(r"^\s*return\s+0\s*$", re.M)
RETURN_3 = re.compile(r"^\s*return\s+3\s*$", re.M)

# The empty-set idiom: `if not <name>:` where <name> is a collected list of inputs.
EMPTY_SET = re.compile(r"^\s*if\s+not\s+(?:targets|files|items|found|hits|rows|roots|docs|corpus)\s*:",
                       re.M)


def scan(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    out: list[str] = []
    lines = text.splitlines()

    for i, line in enumerate(lines):
        if not SKIP_PRINT.search(line):
            continue
        # Look ahead 4 statements for the exit code this skip takes.
        window = "\n".join(lines[i:i + 5])
        if RETURN_3.search(window):
            continue
        if RETURN_0.search(window):
            out.append(f"{path.name}:{i + 1} prints SKIP then returns 0 — "
                       f"CI reports PASS (SPI-31: a skip is never a pass; use exit 3)")

    for m in EMPTY_SET.finditer(text):
        n = text[:m.start()].count("\n") + 1
        window = "\n".join(lines[n - 1:n + 6])
        if RETURN_0.search(window) and not RETURN_3.search(window):
            out.append(f"{path.name}:{n} passes over an empty input set with return 0 "
                       f"(SPI-32: no gate may pass over zero inputs; use exit 3)")
    return out


def main(argv: list[str]) -> int:
    root = pathlib.Path(argv[1]) if len(argv) > 1 else ROOT
    gates = sorted(p for p in (root / "tools").glob("*_gate.py"))
    if not gates:
        print("loophole_gate: SKIP — no gates to inspect")
        return 3

    findings: list[str] = []
    for g in gates:
        findings += scan(g)

    if findings:
        print(f"loophole_gate: FAIL — {len(findings)} loophole(s) in {len(gates)} gate(s):")
        for f in findings:
            print("  " + f)
        return 1

    print(f"loophole_gate: PASS — {len(gates)} gate(s) inspected, no skip-as-pass, "
          f"no vacuous pass")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
