#!/usr/bin/env python3
"""autophagy.py — the tree consumes its own defects and returns to a newborn state.

WHY THIS EXISTS
    Every defect this project has hit was fixed by a human or an agent noticing it, then
    fixing that one instance. The instance was never the problem: the problem was that
    nothing in the tree could SEE the class, and nothing prevented its return. A source
    base that must be watched is not an apparatus; it is a patient.

    So each defect is registered here as a triple:
      detect  — a command that exits non-zero when the defect is present
      repair  — a deterministic generator that removes it (never a judgement call)
      prevent — the CI gate that fails if the class ever comes back

    detect is what makes it visible. repair is what makes it gone. prevent is what makes it
    IMPOSSIBLE rather than merely absent. A registry entry with no prevent is refused at
    load, because "fixed for now" is the exact failure mode this tool exists to end.

THE LOOP
    Pass over every class. Repair what is dirty. Re-run the detector to PROVE the repair
    took. Repeat until a pass finds nothing to do. Bounded: a repair that does not converge
    is a broken repair, and the tool says so instead of spinning.

    A repair is never trusted because it ran. It is trusted because the detector that
    found the defect now reports clean — the same command, run again, against the bytes on
    disk (SPI-2).

    python3 tools/autophagy.py            heal, loop to convergence, print the verdict
    python3 tools/autophagy.py --check    report the defect classes, repair nothing
    python3 tools/autophagy.py --commit   also commit + push what was healed (NEVER #21)
"""
import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAX_PASSES = 5


class Class_:
    """One defect CLASS: how to see it, how to end it, how to keep it from returning."""

    __slots__ = ("name", "detect", "repair", "prevent", "note")

    def __init__(self, name, detect, repair, prevent, note=""):
        if not prevent:
            raise ValueError(f"{name}: a repair with no prevention gate is refused — "
                             f"'fixed for now' is the defect this tool ends")
        self.name, self.detect, self.repair = name, detect, repair
        self.prevent, self.note = prevent, note


def sh(cmd):
    return subprocess.run(cmd, cwd=ROOT, shell=True, capture_output=True, text=True)


CLASSES = [
    # Ordering is a dependency, not a preference: kb_index hashes every tracked file, so it
    # runs last — after praxis and the boards have written. Placing it first guarantees a
    # stale index on every run.
    Class_("order in force on every board",
           "python3 tools/praxis_propagate.py --check",
           "python3 tools/praxis_propagate.py",
           "ci: praxis propagation gate",
           "boards that disagree about the order let two agents work different directives"),

    Class_("chat gate watermark",
           "python3 tools/chat_gatekeeper.py --check",
           "python3 tools/chat_gatekeeper.py --write",
           "ci: chat gate",
           "an un-ingested order is an order nobody is executing"),

    Class_("pulse freshness",
           "python3 tools/synchrony_pulse.py --check",
           "python3 tools/synchrony_pulse.py",
           "ci: synchrony pulse",
           "a frozen clock makes the whole schedule read as a stall"),

    Class_("one-shot payload",
           "python3 build/make-oneshot.py --check",
           "python3 build/make-oneshot.py",
           "ci: one-shot installer",
           "a stale payload ships yesterday's tree under today's name"),

    Class_("portable kit artifact",
           "python3 kit/coordinasync.py selftest",
           "python3 build/make-coordinasync.py",
           "ci: coordinasync portable kit",
           "the kit is generated from tools/; if the sources heal and the bundle does not, "
           "the apparatus the Operator carries is stale in his hand"),

    Class_("unclosed block comment",
           "! python3 tools/kt_comment_scan.py $(git ls-files '*.kt') 2>/dev/null "
           "| grep -q UNCLOSED",
           "python3 tools/fix_unclosed_comments.py $(git ls-files 'app/src/main/java/*.kt' "
           "'omega-app/src/main/java/*.kt')",
           "ci: kotlin comment scan",
           "an unclosed comment makes every later line of the file unparseable"),
    Class_("standing authority inscribed",
           "python3 tools/authority_gate.py --check",
           "python3 tools/cns_directive.py --write",
           "ci: authority gate (NEVER #21)",
           "the sentinel vanished three times through rebases; it is generated now, so it "
           "cannot"),

    Class_("forge artifact in sync",
           "python3 build/build-forge.py --check",
           "python3 build/build-forge.py",
           "ci: repo gate (sync)",
           "a forge html older than its sources ships code the tree no longer contains"),

    Class_("central directive on every board",
           "python3 tools/cns_directive.py --check",
           "python3 tools/cns_directive.py --write",
           "ci: cns directive",
           "a directive on four boards is a directive one agent does not have"),

    Class_("omega deficit indicator",
           "python3 tools/omega_deficit.py",
           "python3 tools/omega_deficit.py --write",
           "ci: omega deficit",
           "a stale E/W_in reports progress that has not happened"),

    Class_("generated docs index",
           "python3 tools/kb_index.py",
           "python3 tools/kb_index.py --write",
           "ci: kb_index",
           "docs/INDEX.md + kb_manifest.json are generated; a stale index is a lie about the tree"),

    # Found 2026-11-20: tree_omega/ sat gitignored in the working directory holding a second
    # app/src. The unit ledger judged a Kotlin file that is not in the repository at all, so
    # the defect was invisible to every reviewer and loud in CI.
    Class_("phantom source tree",
           "python3 tools/phantom_tree_gate.py --check",
           "python3 tools/phantom_tree_gate.py --fix",
           "ci: phantom source tree",
           "a gitignored duplicate tree is judged by gates that scan the working directory"),

    # Found 2026-11-20: kotlinc was present without a JVM, so controller_gate reported
    # "harness did not compile" — a code-defect message for an absent runtime.
    Class_("half a toolchain",
           "python3 tools/toolchain_gate.py --check",
           "python3 tools/toolchain_gate.py --fix",
           "ci: toolchain integrity",
           "a compiler without its runtime makes every compile gate blame the code"),

]


def dirty(c):
    return sh(c.detect).returncode != 0


def heal(c, dry):
    if dry:
        return "would repair"
    sh(c.repair)
    # The repair is not trusted because it ran. It is trusted because the detector that
    # found the defect now reports clean against the bytes on disk.
    return "repaired" if not dirty(c) else "REPAIR DID NOT CONVERGE"


def verdict(rows, passes, residue):
    ok = not residue
    print()
    print("=" * 78)
    print(f"  AUTOPHAGY: {'CLEAN — newborn tree' if ok else 'DEFECTIVE — residue remains'}")
    print("=" * 78)
    for c, state in rows:
        mark = "  ok  " if state in ("clean", "repaired", "would repair") else " FAIL "
        print(f"{mark} {c.name:<34} {state:<24} prevented by {c.prevent}")
    print("-" * 78)
    print(f"  passes: {passes}   classes: {len(CLASSES)}   "
          f"residue: {len(residue)}")
    if residue:
        print("  remaining:")
        for c, why in residue:
            print(f"    - {c.name}: {why}")
    print("=" * 78)
    return 0 if ok else 1


def main():
    dry = "--check" in sys.argv
    do_commit = "--commit" in sys.argv

    rows, passes, residue = [], 0, []
    for passes in range(1, MAX_PASSES + 1):
        work = [c for c in CLASSES if dirty(c)]
        if not work:
            rows = [(c, "clean") for c in CLASSES]
            break
        for c in work:
            state = heal(c, dry)
            rows = [(x, state if x is c else s) for x, s in rows]
            print(f"  [{passes}] {c.name}: {state}")
            if state.startswith("REPAIR DID NOT CONVERGE"):
                residue.append((c, state))
        if dry:
            residue = [(c, "dirty — not repaired (--check)") for c in work]
            break
    else:
        residue = [(c, "still dirty after MAX_PASSES") for c in CLASSES if dirty(c)]

    if not dry:
        # The verdict must describe the tree as it is NOW, not as it was three repairs ago.
        # A class repaired early can be fixed again by a later class's write, and reporting
        # that as residue is a false alarm; the reverse — reporting clean when it is not —
        # is worse, so this is recomputed from disk, never carried forward.
        residue = [(c, "still dirty after repair") for c in CLASSES if dirty(c)]
        if residue:
            rows = [(c, "still dirty" if any(c is r for r, _ in residue) else s)
                    for c, s in (rows or [(x, "clean") for x in CLASSES])]

    if do_commit and not dry:
        st = sh("git status --porcelain")
        if st.stdout.strip():
            sh("git add -A")
            sh('git -c user.name=openhands -c user.email=openhands@all-hands.dev '
               'commit -q -m "autophagy: return the tree to newborn\n\n'
               'Co-authored-by: openhands <openhands@all-hands.dev>"')
            sh("git push -q origin main")
            print("  committed and pushed the healed tree")

    return verdict(rows or [(c, "clean") for c in CLASSES], passes, residue)


if __name__ == "__main__":
    sys.exit(main())
