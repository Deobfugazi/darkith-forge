#!/usr/bin/env python3
"""divergence_gate_test.py — the divergence gate judged by running it (SPI-38).

Real bare-origin clone pairs, never mocks: divergence fires with honest ahead/behind
counts, the gate stays silent when synced, ahead-only is not divergence (NEVER #21 owns
dwell), and the repair converges with a pushed park branch and a fast-forwarded main.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent  # tools/
sys.path.insert(0, str(ROOT))

import divergence_gate as g  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def commit(repo, msg):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-q", "--allow-empty", "-m", msg],
                   cwd=str(repo), check=True)


def clone_pair():
    import tempfile
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "origin").mkdir()
    # -b main: a bare repo defaults its HEAD to master, so every clone would start on an
    # unborn branch and "HEAD:main" would be rejected as a non-fast-forward.
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(d / "origin")], check=True)
    w = d / "work"
    subprocess.run(["git", "clone", "-q", str(d / "origin"), str(w)], check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(w), check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(w), check=True)
    (w / "A.md").write_text("a\n")
    subprocess.run(["git", "add", "-A"], cwd=str(w), check=True)
    commit(w, "seed")
    subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=str(w), check=True)
    p = d / "peer"
    subprocess.run(["git", "clone", "-q", str(d / "origin"), str(p)], check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(p), check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(p), check=True)
    return d, w, p


def main():
    print("== in sync stays silent ==")
    _, w, peer = clone_pair()
    check("synced reads clean", g.measure(root=w)[0] == "clean")

    print("== ahead-only is NOT divergence (NEVER #21 owns dwell) ==")
    (w / "B.md").write_text("b\n")
    subprocess.run(["git", "add", "-A"], cwd=str(w), check=True)
    commit(w, "ahead only")
    check("ahead-only reads clean", g.measure(root=w)[0] == "clean")

    print("== ahead AND behind fires with honest counts ==")
    (peer / "C.md").write_text("c\n")
    subprocess.run(["git", "add", "-A"], cwd=str(peer), check=True)
    commit(peer, "from the other tab")
    subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=str(peer), check=True)
    state, ahead, behind, _ = g.measure(root=w)
    check("diverged fires", state == "diverged", state)
    check("ahead=1", ahead == 1, str(ahead))
    check("behind=1", behind == 1, str(behind))

    print("== repair converges: park pushed, main fast-forwarded, no force ==")
    r_state, park = g.repair(root=w)
    check("repair converges", r_state == "clean", str(park))
    check("detector agrees", g.measure(root=w)[0] == "clean")
    remote_main = subprocess.run(["git", "ls-remote", "origin", "refs/heads/main"],
                                 cwd=str(w), capture_output=True, text=True).stdout.split()[0]
    check("origin/main == local HEAD",
          g.git(["rev-parse", "HEAD"], root=w).stdout.strip() == remote_main)
    ls_park = subprocess.run(["git", "ls-remote", "origin", f"refs/heads/{park}"],
                             cwd=str(w), capture_output=True, text=True).stdout
    check("park is a real pushed ref", ls_park.strip() != "", park)

    print("== a second repair is a no-op ==")
    before = g.git(["rev-parse", "HEAD"], root=w).stdout
    g.repair(root=w)
    check("no stray rebase", g.git(["rev-parse", "HEAD"], root=w).stdout == before)

    print()
    if FAILS:
        print(f"DIVERGENCE GATE TEST: FAIL ({len(FAILS)}): {FAILS}")
        return 1
    print("DIVERGENCE GATE TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
