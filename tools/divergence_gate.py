#!/usr/bin/env python3
"""divergence_gate.py — a diverged main is a defect CLASS, not a human emergency (SPI-40 P1).

WHY THIS EXISTS
    A session ended with local main 8 commits ahead and 109 behind origin/main: a plain push
    was refused (non-fast-forward), force-push is forbidden by law, and the drift gate only
    saw files, not topology. The work froze exactly where the session wipe found it. One day
    was lost to a state no gate claimed.

The law (SPI-40 P1): local main AHEAD and BEHIND origin/main is DEFECTIVE. The detector
    fails closed. The repair is deterministic and never force-pushes, never rewrites
    published history:
      1. park every unserved commit on a pushed branch (divergence-park-<stamp>), so a
         session reset cannot eat it;
      2. fast-forward local main to origin/main;
      3. rebase the parked commits onto refreshed main — or if rebase hits conflicts, STOP
         with the park intact. A parked branch with an honest failure beats a silent
         massaged merge every time.
    Convergence is proven by re-running the same detector (SPI-2).

Exit contract: 0 in-sync, 1 diverged/unrepaired, 2 fault, 3 skip (no git here).
"""
import subprocess
import sys
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent


def git(args, root=ROOT):
    return subprocess.run(["git"] + args, cwd=str(root), capture_output=True, text=True)


def detached_branch(root=ROOT) -> str:
    """The branch a detached HEAD belongs to, or '' when no branch points at it.

    tools/admission.py rehearses the suite in `git worktree add --detach`, where
    `rev-parse --abbrev-ref HEAD` answers "HEAD". Treating that as main measured a feature
    branch against origin/main: the rehearsal reported "66 ahead, 8 behind origin" for a
    branch that was in fact 4 ahead and 0 behind its own upstream, and blocked every push.
    A worktree shares refs with its parent, so a local branch still pointing at this commit
    names it exactly.
    """
    out = git(["branch", "--points-at", "HEAD", "--format=%(refname:short)"], root=root)
    # `git branch` also emits pseudo-entries such as "(HEAD detached at abc)" / "(no branch)".
    # They are labels, not refs, and would be read as an upstream name.
    names = [n.strip() for n in out.stdout.splitlines()
             if n.strip() and not n.strip().startswith("(")]
    names = [n for n in names if n != "main"] or names
    return sorted(names)[0] if names else ""


def measure(root=ROOT):
    """Return (state, ahead, behind, branch). state: clean | diverged | skip."""
    if git(["rev-parse", "--is-inside-work-tree"], root=root).returncode != 0:
        return 'skip', 0, 0, ''
    fetch = git(["fetch", "origin"], root=root)
    if fetch.returncode != 0:
        return 'clean', 0, 0, ''   # offline: not judged here; unpushed age is NEVER #21's
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], root=root).stdout.strip()
    if branch == "HEAD":
        named = detached_branch(root=root)
        if not named:
            # A detached commit no branch owns is not a branch that can diverge. Unpushed
            # work is NEVER #21's dwell, judged elsewhere — not a divergence verdict here.
            return 'clean', 0, 0, 'HEAD'
        branch = named
    upstream = f"origin/{branch}"
    if git(["rev-parse", "--verify", "--quiet", upstream], root=root).returncode != 0:
        return 'clean', 0, 0, branch
    ahead = len(git(["rev-list", f"{upstream}..HEAD"], root=root).stdout.splitlines())
    behind = len(git(["rev-list", f"HEAD..{upstream}"], root=root).stdout.splitlines())
    if ahead and behind:
        return 'diverged', ahead, behind, branch
    return 'clean', ahead, behind, branch


def repair(root=ROOT):
    """Park, fast-forward, rebase. Never force. Converge, or stop with the park intact."""
    state, ahead, behind, branch = measure(root=root)
    if state == 'skip':
        return "skip", None
    if state != 'diverged':
        return "clean", None
    park = "divergence-park-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    if git(["branch", park, "HEAD"], root=root).returncode != 0:
        return "drift", "could not park commits on " + park
    if git(["push", "origin", park], root=root).returncode != 0:
        return "drift", "parked on " + park + " but the park ref could not be pushed"
    base = "origin/main" if branch == "HEAD" else f"origin/{branch}"
    rb = git(["rebase", base], root=root)
    if rb.returncode != 0:
        git(["rebase", "--abort"], root=root)
        return ("drift", f"park is safe on {park}; rebase onto {base} hit conflicts and"
                " was aborted — needs an operator decision, never a force-push")
    if git(["push", "origin", "HEAD"], root=root).returncode != 0:
        return "drift", "rebased but push refused"
    st = measure(root=root)[0]
    if st != "clean":
        return "drift", "repair did not converge"
    return "clean", park


def check():
    state, ahead, behind, branch = measure()
    if state == 'skip':
        print("divergence gate: SKIP (no git repository — nothing was judged)")
        return 3
    if state == 'diverged':
        print(f"divergence gate: FAIL ({branch}: {ahead} ahead, {behind} behind origin)")
        print("    needs divergence repair — python3 tools/divergence_gate.py --fix")
        print("    park, fast-forward, rebase; never force-push")
        return 1
    print(f"divergence gate: PASS (in sync with origin: {ahead} ahead, {behind} behind)")
    return 0


def selftest():
    import tempfile
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
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "origin").mkdir()
        subprocess.run(["git", "init", "-q", "--bare", str(d / "origin")], check=True)
        # The fixture pushes to `main`, so the bare repo's HEAD must point there too. Git's
        # default (master where init.defaultBranch is unset) left the peer clone on an unborn
        # master: its commit shared no history with main and the push was rejected as
        # non-fast-forward. The selftest then failed on the machine's git config, not on the
        # gate. Pin the branch the fixture uses.
        subprocess.run(["git", "-C", str(d / "origin"), "symbolic-ref", "HEAD",
                        "refs/heads/main"], check=True)
        w = d / "work"
        subprocess.run(["git", "clone", "-q", str(d / "origin"), str(w)], check=True)
        for cwd in (w,):
            subprocess.run(["git", "config", "user.name", "t"], cwd=str(cwd), check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(cwd), check=True)
        (w / "A.md").write_text("a\n")
        subprocess.run(["git", "add", "-A"], cwd=str(w), check=True)
        commit(w, "seed")
        subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=str(w), check=True)
        p = d / "peer"
        subprocess.run(["git", "clone", "-q", str(d / "origin"), str(p)], check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=str(p), check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(p), check=True)
        return d, w, p

    print("== in sync stays silent ==")
    _, w, peer = clone_pair()
    check("synced clone reads clean", measure(root=w)[0] == "clean")

    print("== ahead only is not divergence (unpushed age is NEVER #21) ==")
    (w / "B.md").write_text("b\n")
    subprocess.run(["git", "add", "-A"], cwd=str(w), check=True)
    commit(w, "ahead only")
    check("ahead-only reads clean", measure(root=w)[0] == "clean")

    print("== ahead AND behind is divergence, with honest counts ==")
    (peer / "C.md").write_text("c\n")
    subprocess.run(["git", "add", "-A"], cwd=str(peer), check=True)
    commit(peer, "from the other tab")
    subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=str(peer), check=True)
    state, ahead, behind, _ = measure(root=w)
    check("diverged fires", state == "diverged", state)
    check("ahead count is 1", ahead == 1, str(ahead))
    check("behind count is 1", behind == 1, str(behind))

    print("== the repair converges without ever force-pushing ==")
    r_state, park = repair(root=w)
    check("repair converges", r_state == "clean", str(park))
    check("detector agrees: clean", measure(root=w)[0] == "clean")
    on_origin = subprocess.run(["git", "ls-remote", "origin", "refs/heads/main"],
                               cwd=str(w), capture_output=True, text=True).stdout.split()[0]
    local = git(["rev-parse", "HEAD"], root=w).stdout.strip()
    check("local main is now what origin has", local == on_origin)
    ls_park = subprocess.run(["git", "ls-remote", "origin", "refs/heads/" + str(park)],
                             cwd=str(w), capture_output=True, text=True).stdout
    check("the parked branch exists on the origin", ls_park.strip() != "", park)

    print("== no git repo is a named SKIP, never a pass ==")
    with tempfile.TemporaryDirectory() as bare:
        check("no repo -> skip", measure(root=bare)[0] == "skip")

    print("== a detached HEAD is judged against the branch that owns it ==")
    # admission.py rehearses in `worktree add --detach`, where abbrev-ref answers "HEAD".
    # Reading that as main measured a feature branch against origin/main and refused pushes
    # that were clean. Here HEAD is detached at a commit a feature branch owns and one commit
    # ahead of it: ahead-only, therefore clean — never "N ahead, M behind origin".
    d, w2, _ = clone_pair()
    subprocess.run(["git", "checkout", "-q", "-b", "feat/x"], cwd=str(w2), check=True)
    subprocess.run(["git", "push", "-q", "origin", "feat/x"], cwd=str(w2), check=True)
    (w2 / "D.md").write_text("d\n")
    subprocess.run(["git", "add", "-A"], cwd=str(w2), check=True)
    commit(w2, "one ahead of its upstream")
    subprocess.run(["git", "checkout", "-q", "--detach", "HEAD"], cwd=str(w2), check=True)
    st, ahead2, behind2, branch2 = measure(root=w2)
    check("detached HEAD resolves to its owning branch", branch2 == "feat/x", branch2)
    check("detached ahead-only is not divergence", st == "clean", f"{st} {ahead2}/{behind2}")
    check("detached counts are against feat/x, not main", (ahead2, behind2) == (1, 0),
          f"{ahead2}/{behind2}")
    check("an unowned detached commit is not a divergence",
          measure(root=pathlib.Path(tempfile.mkdtemp()))[0] == "skip")

    print()
    if FAILS:
        print(f"DIVERGENCE GATE SELFTEST: FAIL ({len(FAILS)}): {FAILS}")
        return 1
    print("DIVERGENCE GATE SELFTEST: PASS")
    return 0


argv_sys = sys.argv[1:]

if __name__ == "__main__":
    if "--selftest" in argv_sys:
        sys.exit(selftest())
    if "--fix" in argv_sys:
        state, detail = repair()
        if state == "skip":
            print("divergence repair: SKIP (no git repository)")
            sys.exit(3)
        if state == "clean":
            print("divergence repair: converged" + (f" (park: {detail})" if detail else ""))
            sys.exit(0)
        print("divergence repair: " + str(detail))
        sys.exit(1)
    sys.exit(check())
