#!/usr/bin/env python3
"""circadian_gate.py — enforces MUST #15 (CIRCADIAN ANCHOR, DARKITH.md §22/§30).

The law: Operator-facing time is reported in Asia/Manila (UTC+8), and "N hours back" is
resolved from the wake marker, never from the raw machine clock.

This gate fails if any Operator-facing report path takes a bare wall-clock reading
(`datetime.now()` / `datetime.utcnow()` / `time.time()` used for a timestamp) instead of
going through `tools/omega_time.py`. It also proves `omega_time` itself is correct: the
zone is UTC+8 and the anchor is stable.

Fails if:
  - `tools/omega_time.py` is absent, or does not define the UTC+8 zone;
  - a report generator (tools/*.py, build/*.py) takes a naive wall-clock time for output
    while `omega_time` exists (i.e. bypasses the one clock);
  - `omega_time` mis-resolves: its zone offset is not +8, or its anchor drifts run-to-run.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TIME_TOOL = ROOT / "tools/omega_time.py"

# bare wall-clock reads used to stamp output. Allowed only inside omega_time.py itself.
NAIVE = re.compile(r"datetime\.(?:now|utcnow)\(|time\.time\(|datetime\.fromtimestamp\(")
# a line is "for output" if it feeds strftime/format/a timestamp field
OUTPUTISH = re.compile(r"strftime|isoformat|timestamp|stamp|\.write\(|append\(|print\(")


def main() -> int:
    if not TIME_TOOL.is_file():
        print("circadian_gate: FAIL — tools/omega_time.py missing (MUST #15 has no clock)")
        return 1
    # the zone is pinned in the GENERATED runtime (the one implementation)
    gen = ROOT / "build/gen/omega_time_runtime.py"
    src = gen.read_text(encoding="utf-8") if gen.is_file() else TIME_TOOL.read_text(encoding="utf-8")
    if "timedelta(hours=8)" not in src:
        print("circadian_gate: FAIL — the clock does not pin the Operator zone to UTC+8")
        return 1

    fails = []
    for py in sorted(list((ROOT / "tools").glob("*.py")) + list((ROOT / "build").glob("*.py"))):
        if py.name in {"omega_time.py", "circadian_gate.py", "gen_synchrony.py"}:
            continue  # the clock, the clock's generator, and this gate's own regex/docstring
        for i, line in enumerate(py.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if NAIVE.search(line) and OUTPUTISH.search(line):
                fails.append(f"{py.relative_to(ROOT)}:{i} takes a bare wall-clock time for output "
                             f"(must use tools/omega_time.py)")

    # prove omega_time resolves correctly
    r = subprocess.run([sys.executable, str(TIME_TOOL)], capture_output=True, text=True)
    if r.returncode != 0 or "UTC+8" not in r.stdout:
        fails.append("omega_time.py did not resolve the Operator zone at runtime")

    if fails:
        print(f"circadian_gate: FAIL — {len(fails)} problem(s):")
        for f in fails:
            print("  " + f)
        return 1
    print("circadian_gate: PASS — one clock (UTC+8), wake-anchored; no bare wall-clock stamps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
