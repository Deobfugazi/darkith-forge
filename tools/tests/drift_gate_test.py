#!/usr/bin/env python3
"""drift_gate_test.py — the drift gate is judged like any law: by running it (SPI-38).

Drives real temporary git repositories, never mocks: the detector must fire on a dirty
tree, stay silent on a newborn one, and the deterministic repair (NEVER #22 / MUST #42)
must converge and leave a real commit. A porous gate that lets its own phantom through
is worse than no gate, so the breach cases are the point of this file."""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent  # tools/
sys.path.insert(0, str(ROOT))

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

    print("== the repair converges without a remote and is a real commit (SPI-2) ==")
    r_state, r_paths = g.repair(dirty)
    check("repair converges (no remote)", r_state == "clean", str(r_paths))
    check("detector agrees: newborn", g.find_drift(dirty)[0] == "clean")
    log = g.git(["log", "--format=%s"], root=dirty)
    check("repair left a real commit", "eliminate uncommitted drift" in log.stdout)

    print("== with a real bare remote, default repair stays local; explicit push lands ==")
    import tempfile
    remote_dir = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", "--bare"], cwd=remote_dir, check=True)
    shared = fresh_repo()
    subprocess.run(["git", "remote", "add", "origin", remote_dir], cwd=shared, check=True)
    (shared / "HISTORY.md").write_text("half a repair\n")
    s_state, s_paths = g.repair(shared)
    check("repair converges with a remote", s_state == "clean", str(s_paths))
    refs = g.git(["ls-remote", "origin"], root=shared)
    check("default repair does not push", refs.returncode == 0 and not refs.stdout.strip(), refs.stdout.strip())
    (shared / "HISTORY2.md").write_text("explicit push\n")
    p_state, p_paths = g.repair(shared, push=True)
    check("explicit push repair converges", p_state == "clean", str(p_paths))
    heads = subprocess.run(["git", "rev-list", "--all"], cwd=remote_dir,
                           capture_output=True, text=True).stdout.splitlines()
    local_head = g.git(["rev-parse", "HEAD"], root=shared).stdout.strip()
    remote_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=remote_dir,
                                 capture_output=True, text=True).stdout.strip()
    check("explicit push really landed", remote_head == local_head and bool(remote_head),
          f"remote {remote_head[:8]} vs local {local_head[:8]}, {len(heads)} commit(s)")

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

    print("== gate-written trees are the gate's own output, not drift ==")
    generated = fresh_repo()
    (generated / "proof").mkdir()
    (generated / "proof" / "convergence.json").write_text('{"v":1}\n')
    subprocess.run(["git", "add", "-A"], cwd=generated, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-q", "-m", "seed proof"], cwd=generated, check=True)
    # convergence_gate rewrites this file on every CI run; counting it would make the gate
    # red forever, the "gate that cannot pass" failure this project already burned once.
    (generated / "proof" / "convergence.json").write_text('{"v":2}\n')
    state, paths = g.find_drift(generated)
    check("a rewritten generated file is not drift", state == "clean", f"{state} {paths}")
    (generated / "TASKS.md").write_text("half a repair\n")
    state, paths = g.find_drift(generated)
    check("real drift beside generated output still fires", state == "drift", str(paths))

    print("== a cycle in flight is allowed a dirty tree ==")
    # S01..S16 write receipts and regenerate tissue before S16 lands them; a gate that
    # failed that would forbid the very work it guards and closure could never happen.
    (generated / "TASKS.md").unlink(missing_ok=True)
    (generated / "UNLANDED.md").write_text("a cycle's own receipt\n")
    g.git(["add", "-A"], root=generated)
    g.git(["commit", "-q", "-m", "seed"], root=generated)
    (generated / "UNLANDED.md").write_text("a cycle's own receipt, rewritten\n")
    # The test must CONTROL this signal, never inherit it: CI runs the suite inside a cycle,
    # where the flag is already set, and an inherited flag made the "outside a cycle" case
    # silently skip instead of firing.
    saved = os.environ.pop("REVITALIZATION_BOOTSTRAP", None)
    try:
        check("outside a cycle the same edit is drift", g.check(generated) == 1)
        os.environ["REVITALIZATION_BOOTSTRAP"] = "1"
        rc = g.check(generated)
        check("in flight the gate is a named SKIP, not a pass", rc == 3, f"exit {rc}")
    finally:
        os.environ.pop("REVITALIZATION_BOOTSTRAP", None)
        if saved is not None:
            os.environ["REVITALIZATION_BOOTSTRAP"] = saved
    print("== the CLI path with no argument judges this repo, and does not crash ==")
    # The suite passes an explicit root everywhere, so the default-argument path -- the one
    # ci.sh actually runs -- was never exercised and shipped a cwd="None" traceback.
    saved = os.environ.pop("REVITALIZATION_BOOTSTRAP", None)
    try:
        rc = g.check()
        check("no-argument check returns a verdict", rc in (0, 1, 3), f"exit {rc}")
    finally:
        if saved is not None:
            os.environ["REVITALIZATION_BOOTSTRAP"] = saved
    print()
    if FAILS:
        print(f"DRIFT GATE TEST: FAIL ({len(FAILS)}): {FAILS}")
        return 1
    print("DRIFT GATE TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
