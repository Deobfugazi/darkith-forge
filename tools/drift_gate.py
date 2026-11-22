#!/usr/bin/env python3
"""drift_gate.py — uncommitted drift is a defect CLASS, never a warning (NEVER #22).

WHY THIS EXISTS
    D-1 in tools/ci.sh printed `working tree clean: WARN` for uncommitted edits, and the
    autophagy registry had no class for general uncommitted work (tree_invariant covers
    only the derived-artifact subclass). A WARN holds exit 0: every consumer of the exit
    code reads it as a pass, the detail scrolls away, and half a repair sat invisible
    until an off-schedule run shipped it. Three identical red runs on 2026-11-22 had one
    root cause: edits sitting uncommitted between stages of the same corrective loop.
    Operator directive: drift is a permanent failure mode, and the fix is a CLASS fix —
    a detector, a deterministic repair, a prevention gate in CI, and a test that proves
    all three (MUST #41). Converges with tree_invariant (NEVER #22, the derived-artifact
    subclass); the general class was still ungated and unfixable.

Exit contract (a gate must be exact about what it refuses to judge):
    0   newborn tree — nothing uncommitted
    1   DEFECTIVE    — uncommitted drift present; --check names every path
    2   internal fault — never used for a verdict about the tree
    3   SKIP         — git itself cannot run here: a named skip, never a pass
"""
import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def git(args, root=ROOT):
    return subprocess.run(["git"] + args, cwd=str(root), capture_output=True, text=True)


def find_drift(root=ROOT):
    """Return (state, paths); state is 'clean', 'drift', or 'skip'."""
    st = git(["status", "--porcelain"], root=root)
    if st.returncode != 0:
        return 'skip', [st.stderr.strip() or 'git unavailable']
    paths = sorted(l for l in st.stdout.splitlines() if l.strip())
    return ("drift" if paths else "clean"), paths


def repair(root=ROOT):
    """One deterministic sweep: stage, commit, push. Never force, never rewrite."""
    st = git(["status", "--porcelain"], root=root)
    if st.returncode != 0:
        return 'skip', [st.stderr.strip() or 'git unavailable']
    if not st.stdout.strip():
        return "clean", []
    git(["add", "-A"], root=root)
    c = git(["-c", "user.name=openhands",
             "-c", "user.email=openhands@all-hands.dev",
             "commit", "-q", "-m",
             "autophagy: eliminate uncommitted drift (NEVER #22)\n\n"
             "Co-authored-by: openhands <openhands@all-hands.dev>"], root=root)
    if c.returncode != 0:
        return 'drift', [c.stderr.strip() or 'commit refused']
    push = git(["push", "origin", "HEAD"], root=root)
    if push.returncode != 0:
        return 'drift', [push.stderr.strip() or 'push refused (never force-pushed)']
    state, paths = find_drift(root=root)
    if state != "clean":
        return "drift", paths or ["repair did not converge"]
    return "clean", []


def check():
    state, paths = find_drift()
    if state == "skip":
        print("drift gate: SKIP (no git repository — nothing was judged)")
        return 3
    if state == "drift":
        print("drift gate: FAIL (uncommitted drift is a defect class — NEVER #22)")
        for p in paths:
            print(f"    {p}")
        print("    repair: python3 tools/drift_gate.py --fix")
        return 1
    print("drift gate: PASS (newborn tree, nothing uncommitted)")
    return 0


def selftest():
    """Prove the detector fires on a dirty tree, stays silent on a clean one, and that
    the repair converges — against REAL git repositories, never mocks (MUST #20)."""
    import tempfile
    FAILS = []

    def check(name, ok, detail=""):
        print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            FAILS.append(name)

    def fresh_repo():
        d = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=d, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-q", "--allow-empty", "-m", "seed"], cwd=d, check=True)
        return pathlib.Path(d)

    print("== a clean, committed tree is newborn ==")
    clean = fresh_repo()
    state, _ = find_drift(clean)
    check("detector is silent on a clean tree", state == "clean", state)

    print("== uncommitted drift must fire, with every path named ==")
    dirty = fresh_repo()
    (dirty / "HISTORY.md").write_text("half a repair\n")
    state, paths = find_drift(dirty)
    check("detector fires on a dirty tree", state == "drift", state)
    check("the drifted path is named", any("HISTORY.md" in p for p in paths), str(paths))

    print("== the repair converges, and it is a real commit on disk (SPI-2) ==")
    r_state, r_paths = repair(dirty)
    check("repair reports convergence", r_state == "clean", str(r_paths))
    check("detector agrees the tree is newborn", find_drift(dirty)[0] == "clean")
    log = git(["log", "--format=%s"], root=dirty)
    check("the repair is a committed fact", "eliminate uncommitted drift" in log.stdout)

    print("== no git repo is a named SKIP, never a pass ==")
    with tempfile.TemporaryDirectory() as bare:
        state, _ = find_drift(bare)
        check("no git repo is a skip", state == "skip", state)

    print()
    if FAILS:
        print(f"DRIFT GATE SELFTEST: FAIL ({len(FAILS)}): {FAILS}")
        return 1
    print("DRIFT GATE SELFTEST: PASS")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--fix" in sys.argv:
        state, paths = repair()
        if state == "skip":
            print("drift repair: SKIP (no git repository)")
            sys.exit(3)
        if state == "clean":
            print("drift repair: converged to newborn")
            sys.exit(0)
        print("drift repair: DID NOT CONVERGE")
        for p in paths:
            print(f"    {p}")
        sys.exit(1)
    sys.exit(check())
