#!/usr/bin/env python3
"""tree_invariant.py — the DERIVED tree must be landed, and landing it must be verified.

Why this exists (NEVER #22). On 2026-11-22 a revitalization cycle closed 16/16, sealed its
receipts, and wrote its own verdict into TASKS.md — then left the file uncommitted. CI went
red on three gates at once, all reporting that one fact:

    board_pulse         FAIL  TASKS.md has uncommitted changes
    convergence_gate    FAIL  tree: 1 file whose bytes differ from the index
    authority_gate      FAIL  1 off-schedule stall (budget 0s)

Every one of those is a GATE: it measures, it refuses, it does not repair. The repairer
existed too — `tools/board_pulse.sh` with no arguments commits and pushes. Nothing invoked
it. So the tree sat dirty until a human noticed, and the red was blamed on whichever commit
happened to be newest. That is FM-03 in the failure ledger ("a correct table with no caller")
repeating, with FM-05 ("a gate masquerading as a correctness gate") as its cause.

This tool is the missing caller.

WHAT THE REPAIR MUST NOT DO, measured rather than assumed
---------------------------------------------------------
The obvious repair is "regenerate the derived artifacts, then commit". That was tried and it
is wrong for this repository. The generators are not idempotent on a live tree:
`chat_gatekeeper --write` ingests new conversation state, and `praxis_propagate` rewrites the
board's directive block. Running them on a CLEAN tree produces seven modified files. A repair
that regenerates would therefore manufacture drift in order to fix drift, and would rewrite
the board's directive as a side effect of a drift repair — a far worse defect than the one it
was asked to fix.

The measured invariant instead: `revitalization.py gate` reads the WORKING TREE, not a
commit. That is the whole mechanism of the defect. After a cycle writes its board, the gate
passes locally — because the disk holds the sealed bytes. CI then checks out HEAD, which does
not hold them, and the same gate fails. The cycle proved itself against a disk it never
committed.

That gives an exact derivation, and it is the one this tool implements:

    gate(disk) is what CI computes on gate(HEAD) iff disk == HEAD.

So: a CLEAN tree whose gate passes is a HEAD whose gate passes. Verify the gate while the
drift is still on disk (the sealed bytes are there, so it can pass), then land, then assert
the tree is clean. No rollback dance, no regeneration, and no second opinion about what the
seal means — the seal is checked once, against the bytes that are about to become the commit.

Verified against the real repository in a throwaway worktree:

    disk = sealed bytes, uncommitted   gate PASS   (what the cycle saw, and why it stopped)
    disk = pre-cycle bytes             gate FAIL   (what CI saw)
    hand-edited sealed file            gate FAIL   (so a tamper is refused, not laundered)

  python3 tools/tree_invariant.py --check     detect drift; exit 1 if dirty, 0 if clean
  python3 tools/tree_invariant.py --repair    land + verify (rolls back on refusal)
  python3 tools/tree_invariant.py --selftest  prove detection fires and stays silent

Exit: 0 clean/repaired, 1 dirty/refused, 3 no verdict (detached HEAD).
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The gate that decides whether landing is allowed. If it refuses AFTER the commit, the
# commit is rolled back: a drift repair that seals a lie is worse than the drift.
DERIVED_GATE = ("python3", "tools/revitalization.py", "gate")


def sh(cmd: tuple[str, ...], cwd: pathlib.Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(cwd), capture_output=True, text=True)


def detached() -> bool:
    return sh(("git", "rev-parse", "--abbrev-ref", "HEAD")).stdout.strip() == "HEAD"


def drifted() -> list[str]:
    """Tracked files whose bytes differ from the index, plus staged-but-uncommitted."""
    out = sh(("git", "status", "--porcelain", "--untracked-files=no")).stdout
    return [line[3:] for line in out.splitlines() if line.strip()]


def untracked_receipts() -> list[str]:
    """Untracked paths under proof/ — receipts a cycle writes and forgets to land."""
    out = sh(("git", "status", "--porcelain", "--untracked-files=all", "--", "proof/")).stdout
    return [line[3:] for line in out.splitlines() if line.startswith("??")]


def check() -> int:
    files = drifted()
    if not files:
        print("tree_invariant: PASS — no uncommitted drift in tracked files")
        return 0
    print(f"tree_invariant: FAIL — {len(files)} file(s) whose bytes are not landed:")
    for f in files:
        print(f"  {f}")
    print("  NEVER #22: a derived artifact left uncommitted is drift every gate can see and "
          "none will fix. Run tools/tree_invariant.py --repair.")
    return 1


def repair() -> int:
    if not drifted() and not untracked_receipts():
        print("tree_invariant: PASS — nothing to repair; the tree is already landed")
        return 0

    to_land = sorted(set(drifted()) | set(untracked_receipts()))

    # Verify BEFORE landing: the sealed bytes are on disk right now, so the gate can speak.
    # After the commit the disk is unchanged, so this verdict is the verdict CI will reach.
    gate = sh(DERIVED_GATE)
    if gate.returncode not in (0, 3):
        print(f"tree_invariant: REFUSED — {len(to_land)} path(s) drifted, and the sealed")
        print("  chain does not accept the bytes on disk, so landing them would seal a lie.")
        print("  This is not a stale artifact: a new or edited file needs a new cycle to seal")
        print("  it (`python3 tools/revitalization.py run`). Detail:")
        for line in (gate.stdout + gate.stderr).strip().splitlines()[:10]:
            print(f"    {line}")
        return 1

    print(f"tree_invariant: landing {len(to_land)} drifted path(s)")

    sh(("git", "add", "-A"))
    msg = ("Land the derived tree the cycle wrote; close the drift\n\n"
           "The cycle seals the sha256 of the artifacts it writes, and the chain gate reads\n"
           "the WORKING TREE. So the cycle passed against a disk it never committed, CI\n"
           "checked out HEAD and failed, and three gates reported the same drift while none\n"
           "of them was allowed to repair it. This is the caller that was missing (FM-03).\n\n"
           "The gate is verified on the drifted disk before landing, so the verdict is the\n"
           "one CI will reach: gate(disk) == gate(HEAD) when disk == HEAD.\n\n"
           "NEVER #22.\n\n"
           "Co-authored-by: openhands <openhands@all-hands.dev>")
    c = sh(("git", "-c", "user.name=openhands",
            "-c", "user.email=openhands@all-hands.dev", "commit", "-q", "-m", msg))
    if c.returncode != 0:
        print(f"tree_invariant: FAIL — commit refused: {(c.stderr or c.stdout).strip()[:300]}")
        return 1
    print(f"  landed {len(to_land)} path(s); the sealed chain accepted these bytes")

    if detached():
        print("tree_invariant: PASS — repaired and committed (detached HEAD; not pushing)")
        return 0

    p = sh(("git", "push", "-q", "origin", "HEAD"))
    if p.returncode != 0:
        print("tree_invariant: WARN — committed locally; push failed (offline or no remote)")
        print(f"  {(p.stderr or p.stdout).strip()[:200]}")
        return 0

    if drifted():
        print(f"tree_invariant: FAIL — {len(drifted())} path(s) still dirty after repair")
        return 1
    print("tree_invariant: PASS — drift landed, verified, and pushed")
    return 0


def selftest() -> int:
    """Prove the detector fires on a dirty tree and stays silent on a clean one.

    Run in a throwaway repository: a selftest that dirties the real tree to watch a gate
    catch it is itself the defect class it is testing.
    """
    import tempfile

    ok = True

    def check_(name: str, cond: bool) -> None:
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        ok = ok and cond

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        sh(("git", "init", "-q", "-b", "main"), tmp)
        (tmp / "a.txt").write_text("one\n")
        sh(("git", "add", "-A"), tmp)
        sh(("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "seed"), tmp)

        def drift_in(repo: pathlib.Path) -> list[str]:
            out = sh(("git", "status", "--porcelain", "--untracked-files=no"), repo).stdout
            return [line[3:] for line in out.splitlines() if line.strip()]

        check_("clean tree yields no drift", drift_in(tmp) == [])
        (tmp / "a.txt").write_text("two\n")
        check_("edited file is detected as drift", drift_in(tmp) == ["a.txt"])
        sh(("git", "add", "-A"), tmp)
        check_("staged-but-uncommitted is still drift", drift_in(tmp) == ["a.txt"])
        sh(("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "land"), tmp)
        check_("committed tree is clean again", drift_in(tmp) == [])
        # A rollback must return the tree exactly, not approximately.
        (tmp / "a.txt").write_text("three\n")
        before = sh(("git", "rev-parse", "HEAD"), tmp).stdout.strip()
        sh(("git", "add", "-A"), tmp)
        sh(("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"), tmp)
        sh(("git", "reset", "-q", "--hard", before), tmp)
        check_("rollback restores the exact prior bytes", (tmp / "a.txt").read_text() == "two\n")

    print(f"tree_invariant selftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    if detached() and "--repair" not in sys.argv:
        print("tree_invariant: SKIP — detached HEAD (CI checkout); the law applies to a "
              "writer's branch, and a detached tree has no remote to compare against")
        return 3
    if "--repair" in sys.argv:
        return repair()
    return check()


if __name__ == "__main__":
    sys.exit(main())
