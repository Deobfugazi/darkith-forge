#!/usr/bin/env python3
"""drift_gate_test.py — the drift gate is judged like any law: by running it (SPI-38).

Drives real temporary git repositories, never mocks: the detector must fire on a dirty
tree, stay silent on a newborn one, and the deterministic repair (NEVER #22 / MUST #41)
must converge and leave a real commit. A porous gate that lets its own phantom through
is worse than no gate, so the breach cases are the point of this file."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import drift_gate as g  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def fresh_repo():
    import tempfile
    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-q", "--allow-empty", "-m", "seed"], cwd=d, check=True)
    return pathlib.Path(d)


def main():
    print("== a newborn tree stays silent ==")
    clean = fresh_repo()
    state, _ = g.find_drift(clean)
    check("clean tree reads newborn", state == "clean", state)

    print("== drift fires and names its paths; a WARN can never come back ==")
    dirty = fresh_repo()
    (dirty / "HISTORY.md").write_text("half a repair\n")
    (dirty / "HISTORY2.md").write_text("another lost edit\n")
    state, paths = g.find_drift(dirty)
    check("dirty tree reads drift", state == "drift", state)
    check("every drifted path is named",
          all(any(n in p for p in paths) for n in ("HISTORY.md", "HISTORY2.md")),
          str(paths))

    print("== the repair converges and is a real commit (SPI-2: read the bytes) ==")
    r_state, r_paths = g.repair(dirty)
    check("repair converges", r_state == "clean", str(r_paths))
    check("detector agrees: newborn", g.find_drift(dirty)[0] == "clean")
    log = g.git(["log", "--format=%s"], root=dirty)
    check("repair left a real commit", "eliminate uncommitted drift" in log.stdout)

    print("== a repair on a clean tree is a no-op, not a stray commit ==")
    before = len(g.git(['rev-list', 'HEAD'], root=dirty).stdout.splitlines())
    g.repair(dirty)
    after = len(g.git(['rev-list', 'HEAD'], root=dirty).stdout.splitlines())
    check("no stray commit", before == after, f"{before} -> {after}")

    print("== no git repo is a named SKIP, never a false pass ==")
    import tempfile
    with tempfile.TemporaryDirectory() as bare:
        state, _ = g.find_drift(bare)
        check("not a repo -> skip", state == "skip", state)

    print()
    if FAILS:
        print(f"DRIFT GATE TEST: FAIL ({len(FAILS)}): {FAILS}")
        return 1
    print("DRIFT GATE TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
