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
    Class_("closed briefing re-opened",
           "python3 tools/closed_briefings.py --check",
           "python3 tools/closed_briefings.py --check",
           "ci: closed briefings stay closed",
           "a closed briefing back on the board is a fresh agent re-litigating a question the "
           "bytes already answered, and it costs a delivery cycle every time"),
    Class_("standing authority inscribed",
           "python3 tools/authority_gate.py --sentinel-only",
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

    Class_("board law citations are real",
           "python3 tools/board_law_gate.py",
           "python3 tools/board_law_gate.py",
           "ci: board law citations",
           "a board that cites a law which does not exist teaches the next agent to obey "
           "an invention and to doubt a real law; the gate is the only thing that can "
           "tell the two apart"),

    Class_("phantom gate command",
           "python3 tools/revitalization.py --check-gate-commands",
           "python3 tools/revitalization.py --check-gate-commands",
           "ci: revitalization selftest",
           "a gate whose recovered command is a line-continuation backslash fails without "
           "running, manufacturing a defect with no root cause that no repair can close"),

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

    # Found 2026-11-20: commit 67ea976 dropped 340 lines from TASKS.md, including the title
    # and the whole STANDING-AUTHORITY section. Every gate stayed green because the generator
    # that replaced the file was the thing being trusted.
    Class_("board header intact",
           "python3 tools/board_header_gate.py --check",
           "python3 tools/board_header_gate.py --fix",
           "ci: board header intact",
           "a generator that deletes governance prose is a silent loss no diff reviewer sees"),

    # Found 2026-11-22: a cycle closed 16/16, sealed its receipts, wrote its verdict into
    # TASKS.md — and stopped. Three gates went red on that one fact (board_pulse,
    # convergence_gate, authority_gate) and not one of them was allowed to repair it. The
    # repairer existed all along: board_pulse.sh with no arguments commits and pushes.
    # Nothing called it. That is FM-03 exactly ("a correct table with no caller"), so this
    # class is the caller, and it is placed LAST so it lands whatever the classes above it
    # left dirty in a single pass.
    Class_("uncommitted derived drift",
           "python3 tools/tree_invariant.py --check",
           "python3 tools/tree_invariant.py --repair",
           "ci: tree invariant (NEVER #22)",
           "a derived artifact that is verified on disk and never committed is drift every "
           "gate can see and none may fix; CI checks out a HEAD that never held it"),

    # Found 2026-11-22 (converged): the derived-artifact subclass above was gated, but the
    # GENERAL class — any uncommitted edit in the working tree — was still only a WARN in
    # ci.sh D-1, so half a repair sat invisible until an off-schedule run shipped it.
    # Detector + deterministic repair + prevention gate + test: MUST #41.
    Class_("uncommitted general drift",
           "python3 tools/drift_gate.py --check",
           "python3 tools/drift_gate.py --fix",
           "ci: drift gate (NEVER #22)",
           "uncommitted or unpushed edits are invisible to the other tab and ship half a "
           "repair; the detector fails the tree and the repair commits and pushes it"),

]


def probe(c):
    """Return clean, dirty, or skipped; exit 3 is an explicit no-verdict, not a defect."""
    returncode = sh(c.detect).returncode
    if returncode == 3:
        return "skipped"
    return "clean" if returncode == 0 else "dirty"


def dirty(c):
    return probe(c) == "dirty"


def heal(c, dry):
    if dry:
        return "would repair"
    sh(c.repair)
    state = probe(c)
    if state == "clean":
        return "repaired"
    if state == "skipped":
        return "skipped"
    return "REPAIR DID NOT CONVERGE"


def probe_code(returncode):
    if returncode == 3:
        return "skipped"
    return "clean" if returncode == 0 else "dirty"


def verdict(rows, passes, residue):
    skipped = [c for c, state in rows if state == "skipped"]
    print()
    print("=" * 78)
    if residue:
        headline = "DEFECTIVE — residue remains"
    elif skipped:
        headline = f"INCOMPLETE — {len(skipped)} class(es) could not be examined"
    else:
        headline = "CLEAN — newborn tree"
    print(f"  AUTOPHAGY: {headline}")
    print("=" * 78)
    for c, state in rows:
        mark = "  ok  " if state in ("clean", "repaired", "would repair") else (" SKIP " if state == "skipped" else " FAIL ")
        print(f"{mark} {c.name:<34} {state:<24} prevented by {c.prevent}")
    print("-" * 78)
    print(f"  passes: {passes}   classes: {len(CLASSES)}   "
          f"residue: {len(residue)}   skipped: {len(skipped)}")
    if residue:
        print("  remaining:")
        for c, why in residue:
            print(f"    - {c.name}: {why}")
    print("=" * 78)
    if residue:
        return 1
    return 3 if skipped else 0


def selftest():
    checks = [
        ("exit 0 is clean", probe_code(0) == "clean"),
        ("exit 1 is dirty", probe_code(1) == "dirty"),
        ("exit 3 is skipped, not dirty", probe_code(3) == "skipped"),
        ("every repair has a prevention gate", all(c.prevent for c in CLASSES)),
        ("registry names are unique", len({c.name for c in CLASSES}) == len(CLASSES)),
    ]
    for name, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    good = all(ok for _, ok in checks)
    print(f"autophagy selftest: {'PASS' if good else 'FAIL'} ({sum(ok for _,ok in checks)}/{len(checks)})")
    return 0 if good else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    dry = "--check" in sys.argv
    do_commit = "--commit" in sys.argv

    rows, passes, residue = [], 0, []
    for passes in range(1, MAX_PASSES + 1):
        statuses = {c: probe(c) for c in CLASSES}
        work = [c for c in CLASSES if statuses[c] == "dirty"]
        if not work:
            rows = [(c, statuses[c]) for c in CLASSES]
            break
        for c in work:
            state = heal(c, dry)
            statuses[c] = state
            print(f"  [{passes}] {c.name}: {state}")
        if dry:
            rows = [(c, "would repair" if statuses[c] == "dirty" else statuses[c])
                    for c in CLASSES]
            residue = [(c, "dirty — not repaired (--check)") for c in work]
            break
    else:
        statuses = {c: probe(c) for c in CLASSES}
        residue = [(c, "still dirty after MAX_PASSES") for c in CLASSES
                   if statuses[c] == "dirty"]
        rows = [(c, "still dirty" if statuses[c] == "dirty" else statuses[c])
                for c in CLASSES]

    if not dry:
        # Recompute from disk: later repairs can dirty an earlier class or heal another one.
        statuses = {c: probe(c) for c in CLASSES}
        residue = [(c, "still dirty after repair") for c in CLASSES
                   if statuses[c] == "dirty"]
        rows = [(c, "still dirty" if statuses[c] == "dirty" else statuses[c])
                for c in CLASSES]

    if do_commit and not dry:
        st = sh("git status --porcelain")
        if st.stdout.strip():
            sh("git add -A")
            sh('git -c user.name=openhands -c user.email=openhands@all-hands.dev '
               'commit -q -m "autophagy: return the tree to newborn\n\n'
               'Co-authored-by: openhands <openhands@all-hands.dev>"')
            sh("git push -q origin main")
            print("  committed and pushed the healed tree")

    return verdict(rows or [(c, probe(c)) for c in CLASSES], passes, residue)


if __name__ == "__main__":
    sys.exit(main())
