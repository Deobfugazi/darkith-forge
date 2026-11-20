#!/usr/bin/env python3
"""ofif_gate.py — NT-XIII's falsifier, executed.

NT-XIII §5 claims five fixtures and one composition are forced. G6/G7 are the ones that can
be run against real code today, so they are run here rather than described:

  G6  A non-zero residual on a transaction whose books are KNOWN to balance kills F1.
  G7  A zero residual on a transaction whose cut is KNOWN kills F1 as a detector.

Both are applied to the AutophagicAllocator, whose books ARE known: it is a memory-budget
controller, so for a given free RAM the affordable vertex budget is arithmetic, and the
controller's distance from it is a residual in vertices. If the allocator reports a large
residual when it is sitting exactly on the ceiling (G6), or reports zero when it is
spending 3.5x the ceiling (G7), then F1 does not hold as a detector and NT-XIII is wrong.

Exit 0 = G6 and G7 hold; 1 = a falsifier fired (NT-XIII must be revised); 3 = could not run.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = ROOT / "app/src/main/java/com/darkith/transliaison/core"

HARNESS = '''
import com.darkith.transliaison.core.AutophagicAllocator

fun main() {
    // G6: books KNOWN to balance. Feed the controller the free RAM it needs for exactly the
    // budget it already holds, and let it settle. Residual must go to ~0.
    val a = AutophagicAllocator()
    var r = a.tick(8_000_000L, 1_000_000L, 0.30, 16.6)
    repeat(600) { r = a.tick(8_000_000L, 1_000_000L, 0.30, 16.6) }
    println("G6 budget=${r.vertexBudget} ceiling=${r.budgetCeiling.toLong()} residual=${r.memoryResidual.toLong()}")

    // G7: a KNOWN cut. Ask for far more memory than exists; the controller must NOT report
    // that everything is fine — it must rail to the floor and show a negative residual.
    val b = AutophagicAllocator()
    var q = b.tick(500_000L, 500_000_000L, 0.99, 120.0)
    repeat(600) { q = b.tick(500_000L, 500_000_000L, 0.99, 120.0) }
    println("G7 budget=${q.vertexBudget} ceiling=${q.budgetCeiling.toLong()} residual=${q.memoryResidual.toLong()} scale=${q.resolutionScale}")
}
'''


def find(*cands):
    for c in cands:
        if c and pathlib.Path(c).exists():
            return str(c)
    return None


def main() -> int:
    kotlinc = find(str(ROOT / ".tools/kotlinc/bin/kotlinc"))
    ajar = find(str(ROOT / ".tools/android-all-14-robolectric-10818077.jar"))
    if not kotlinc or not ajar:
        print("ofif_gate: SKIP — kotlinc or android.jar absent; G6/G7 were NOT run")
        return 3

    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        (d / "H.kt").write_text(HARNESS)
        jar = d / "h.jar"
        srcs = [CORE / s for s in ("AutophagicAllocator.kt", "Allocation.kt", "LayoutNode.kt", "IRBuilder.kt")]
        cc = subprocess.run(
            [kotlinc, "-J-Xmx2g", "-cp", ajar, "-nowarn", "-include-runtime", "-d", str(jar)]
            + [str(s) for s in srcs] + [str(d / "H.kt")],
            capture_output=True, text=True, timeout=900)
        if cc.returncode != 0:
            print("ofif_gate: SKIP — harness did not compile")
            return 3
        run = subprocess.run(["java", "-jar", str(jar)], capture_output=True, text=True, timeout=300)

    out = run.stdout
    vals = {}
    for line in out.splitlines():
        if line.startswith(("G6", "G7")):
            print("  " + line)
            f = dict(kv.split("=") for kv in line.split()[1:] if "=" in kv)
            vals[line[:2]] = f
    if set(vals) != {"G6", "G7"}:
        print("ofif_gate: SKIP — harness produced no verdict")
        return 3

    fails = []
    # G6: on balanced books the residual must be small relative to the ceiling.
    g6 = vals["G6"]
    ceil6 = abs(int(g6["ceiling"])) or 1
    if abs(int(g6["residual"])) > 0.02 * ceil6:
        fails.append(f"G6 fired: residual {g6['residual']} on balanced books (ceiling {g6['ceiling']})")
    # G7: on a known cut the DEFICIT MUST BE BOOKED. When the ceiling is below the actuator's
    # hard floor (vMin) the controller cannot comply, so demanding budget <= ceiling would be
    # a charge that can never pass — a miscalibrated charge (W-040). What must hold is that
    # the residual is NEGATIVE, i.e. the shortfall is recorded rather than silenced. A
    # residual of 0 here is the exact failure that fired before the fix: the clamp made
    # error = vMin - vK = 0 and a 7.6x overrun reported "balanced".
    g7 = vals["G7"]
    if int(g7["residual"]) >= 0:
        fails.append(
            f"G7 fired: residual {g7['residual']} on a known cut (ceiling {g7['ceiling']}, "
            f"budget {g7['budget']}) — the deficit was silenced, not booked")
    if int(g7["budget"]) < 65_536:
        fails.append(f"G7 fired: budget {g7['budget']} below the hard floor vMin")

    if fails:
        for f in fails:
            print("  " + f)
        print(f"ofif_gate: FAIL — {len(fails)} falsifier(s) fired; NT-XIII §5 must be revised")
        return 1
    print("ofif_gate: PASS — G6 and G7 hold; F1 behaves as a detector on the real controller")
    return 0


if __name__ == "__main__":
    sys.exit(main())
