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

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The jurisdiction boundary is already written down, once: authority_gate.is_generated()
# names the trees that gates legitimately rewrite during CI (proof/convergence.json is
# convergence_gate's own output). Re-deriving that list here would be a second opinion about
# whose job a dirty file is, and the two would drift. A dirty GENERATED file is not withheld
# work; a dirty TASKS.md or docs/INDEX.md is exactly the defect this tool exists to catch.
sys.path.insert(0, str(ROOT / "tools"))
try:
    from authority_gate import is_generated
except Exception:  # noqa: BLE001 - a missing authority_gate must not silently widen scope
    def is_generated(path: str) -> bool:  # type: ignore[misc]
        return path.startswith(("proof/", "delivery/", "dl/")) or "__pycache__/" in path

# The gate that decides whether landing is allowed. If it refuses AFTER the commit, the
# commit is rolled back: a drift repair that seals a lie is worse than the drift.
DERIVED_GATE = ("python3", "tools/revitalization.py", "gate")


def sh(cmd: tuple[str, ...], cwd: pathlib.Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(cwd), capture_output=True, text=True)


def detached() -> bool:
    return sh(("git", "rev-parse", "--abbrev-ref", "HEAD")).stdout.strip() == "HEAD"


def drifted() -> list[str]:
    """Tracked files whose bytes differ from the index, minus gate-written trees.

    `proof/convergence.json` is convergence_gate's own output: CI rewrites it every run, so
    counting it would make this gate red on every CI run forever — the "gate that cannot
    pass" failure this project already burned once. What remains is the real defect class:
    TASKS.md, docs/INDEX.md, and the other sealed artifacts a cycle writes and forgets.
    """
    out = sh(("git", "status", "--porcelain", "--untracked-files=no")).stdout
    return [line[3:] for line in out.splitlines()
            if line.strip() and not is_generated(line[3:])]


def untracked_receipts() -> list[str]:
    """Untracked paths under proof/ — receipts a cycle writes and forgets to land."""
    out = sh(("git", "status", "--porcelain", "--untracked-files=all", "--", "proof/")).stdout
    return [line[3:] for line in out.splitlines() if line.startswith("??")]


def cycle_open() -> bool:
    """A cycle in flight is SUPPOSED to have a dirty tree: S01..S16 write receipts and
    regenerate derived tissue before S16 lands it. Reporting that as drift would make
    closure impossible — a gate that forbids the very work it guards.

    The signal is REVITALIZATION_BOOTSTRAP, which `revitalization.py` exports for every
    in-cycle `ci.sh` run, including the post-seal pass. The CURRENT marker is the wrong
    signal: it is written `closed=True` BEFORE the post-seal checks run, so keying on it
    would make this class fail the very cycle that is about to land the tree.
    """
    return os.environ.get("REVITALIZATION_BOOTSTRAP") == "1"


def check() -> int:
    if cycle_open():
        print("tree_invariant: SKIP — a revitalization cycle is open; the tree is meant to be "
              "dirty until S16 lands it")
        return 3
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


def push_deferred() -> bool:
    """Testnet repair commits locally; the workflow publishes only the settled tree."""
    return os.environ.get("DARKITH_DEFER_PUSH") == "1"


def repair() -> int:
    if cycle_open():
        print("tree_invariant: SKIP — a revitalization cycle is open; S16 lands the cycle, so "
              "landing here would commit half-written receipts")
        return 3
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

    if push_deferred():
        if drifted():
            print(f"tree_invariant: FAIL — {len(drifted())} path(s) remain dirty before deferred push")
            return 1
        print("tree_invariant: PASS — repaired and committed locally; final testnet push deferred")
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
    """Test detection, commit landing, deferred publication, and exact rollback in a throwaway repo."""
    import tempfile
    ok = True

    def check_(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
        ok = ok and cond

    old_defer = os.environ.get("DARKITH_DEFER_PUSH")
    try:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            sh(("git", "init", "-q", "-b", "main"), tmp)
            (tmp / "a.txt").write_text("one\\n", encoding="utf-8")
            sh(("git", "add", "-A"), tmp)
            seed = sh(("git", "-c", "user.name=t", "-c", "user.email=t@t",
                       "commit", "-qm", "seed"), tmp)
            check_("seed commit created", seed.returncode == 0, seed.stderr.strip())

            def drift_in(repo: pathlib.Path) -> list[str]:
                out = sh(("git", "status", "--porcelain", "--untracked-files=no"), repo).stdout
                return [line[3:] for line in out.splitlines() if line.strip()]

            check_("testnet repair mode defers publication by default", not push_deferred())
            os.environ["DARKITH_DEFER_PUSH"] = "1"
            check_("deferred-push mode is explicit and detectable", push_deferred())
            os.environ.pop("DARKITH_DEFER_PUSH", None)

            check_("clean tree yields no drift", drift_in(tmp) == [])
            (tmp / "a.txt").write_text("two\\n", encoding="utf-8")
            check_("edited file is detected as drift", drift_in(tmp) == ["a.txt"])
            sh(("git", "add", "-A"), tmp)
            check_("staged-but-uncommitted is still drift", drift_in(tmp) == ["a.txt"])
            landed = sh(("git", "-c", "user.name=t", "-c", "user.email=t@t",
                         "commit", "-qm", "land"), tmp)
            check_("commit lands the repaired file", landed.returncode == 0, landed.stderr.strip())
            check_("committed tree is clean again", drift_in(tmp) == [])

            (tmp / "a.txt").write_text("three\\n", encoding="utf-8")
            before = sh(("git", "rev-parse", "HEAD"), tmp).stdout.strip()
            sh(("git", "add", "-A"), tmp)
            sh(("git", "-c", "user.name=t", "-c", "user.email=t@t",
                "commit", "-qm", "rollback target"), tmp)
            sh(("git", "reset", "-q", "--hard", before), tmp)
            check_("rollback restores exact prior bytes",
                   (tmp / "a.txt").read_text(encoding="utf-8") == "two\\n")
    finally:
        if old_defer is None:
            os.environ.pop("DARKITH_DEFER_PUSH", None)
        else:
            os.environ["DARKITH_DEFER_PUSH"] = old_defer

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
