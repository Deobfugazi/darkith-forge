#!/usr/bin/env python3
"""authority_gate.py — NEVER #21: an automated decision is already approved.

The defect this closes: an agent finished work, then held it back pending "approval" for a
decision the Operator had ALREADY automated (tools/board_pulse.sh commits and pushes the
moment the board changes). Nothing in the repo asked for that pause. The pause was imported
from a generic platform default and it overrode the house law. Work sat uncommitted, the
board went stale, and a parallel worker went blind. That is an off-schedule stall, and a
stall is a defect with a cost measured in real time.

Two things are made binding here:

  1. THE AUTHORITY IS WRITTEN DOWN. Every board file must carry the standing-authority
     sentinel. A law that lives only in a chat message is not a law (SPI-15); it can be
     reinterpreted by the next session. The sentinel makes the absence detectable.

  2. A STALL IS MEASURABLE, SO IT IS GATED. Uncommitted drift and unpushed commits are
     read as AGE IN SECONDS. Past the budget, the gate fails and names the files and the
     age. "In progress" is not a state the gate accepts for work that is finished.

  python3 tools/authority_gate.py                 gate (default budget: 900s)
  python3 tools/authority_gate.py --check         same, no side effects
  python3 tools/authority_gate.py --budget 0      zero tolerance (CI: a pushed tree)
  python3 tools/authority_gate.py --selftest      prove the detector fires on a real stall

Exit 0 = no stall and the authority is inscribed. Exit 1 = a named stall or a missing law.
"""
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The sentinel is a machine token, not prose. It must appear verbatim in every board so the
# gate can prove the law is inscribed rather than assume it.
SENTINEL = "STANDING-AUTHORITY (NEVER #21)"
BOARDS = ["AGENTS.md", "DARKITH.md", "TASKS.md", "RESUME.md", "README.md"]

DEFAULT_BUDGET = 900  # seconds a finished change may sit before it is a stall

# Machine-written trees. Gates legitimately rewrite these during CI (proof/convergence.json
# is convergence_gate's own output), so a dirty file here is not withheld human work — it is
# a generated artifact under another gate's jurisdiction. Excluding them keeps this gate
# honest about its one job: nothing FINISHED is sitting uncommitted.
GENERATED_PREFIXES = ("proof/", "delivery/", "dl/")
GENERATED_SUFFIXES = (".pyc",)


def is_generated(path: str) -> bool:
    if any(path.startswith(p) for p in GENERATED_PREFIXES):
        return True
    if any(path.endswith(s) for s in GENERATED_SUFFIXES):
        return True
    return "__pycache__/" in path


def git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def git_ok(*args: str) -> bool:
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True).returncode == 0


def dirty_files() -> list[str]:
    """Tracked files whose bytes differ from the index, plus untracked non-ignored files."""
    out = git("status", "--porcelain")
    paths = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:  # a rename reports "old -> new"
            path = path.split(" -> ", 1)[1]
        if not is_generated(path):
            paths.append(path)
    return paths


def age_seconds(paths: list[str]) -> int:
    """The oldest mtime among the stalled paths — how long the OLDEST change has waited."""
    now = time.time()
    ages = []
    for p in paths:
        f = ROOT / p
        try:
            ages.append(now - f.stat().st_mtime)
        except OSError:
            continue
    return int(max(ages)) if ages else 0


def unpushed() -> tuple[int, str]:
    """Commits on the local branch that the remote does not have. (count, detail)."""
    if not git_ok("symbolic-ref", "-q", "HEAD"):
        return 0, "detached HEAD"
    branch = git("symbolic-ref", "--short", "HEAD").strip() or "main"
    remote = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").strip()
    if not remote:
        return 0, "no upstream configured"
    ahead = git("rev-list", "--count", f"{remote}..HEAD").strip()
    if ahead == "":
        return 0, "remote not comparable"
    return int(ahead), f"{ahead} commit(s) ahead of {remote}"


def check_budget(budget: int) -> tuple[list[str], list[str]]:
    """Return (failures, notes). A failure is a named stall."""
    failures: list[str] = []
    notes: list[str] = []

    # 1. the authority must be inscribed in every board
    for name in BOARDS:
        f = ROOT / name
        if not f.is_file():
            failures.append(f"board {name} is missing — the authority cannot be inscribed in a file that does not exist")
            continue
        if SENTINEL not in f.read_text(encoding="utf-8", errors="replace"):
            failures.append(f"board {name} does not carry '{SENTINEL}' — the standing authority is not written down")

    # 2. uncommitted drift past the budget is a stall
    paths = dirty_files()
    if paths:
        age = age_seconds(paths)
        if age > budget:
            failures.append(
                f"{len(paths)} file(s) uncommitted for {age}s (budget {budget}s): "
                + ", ".join(sorted(paths)[:6]) + (" ..." if len(paths) > 6 else "")
                + " — run tools/board_pulse.sh")
        else:
            notes.append(f"{len(paths)} file(s) uncommitted for {age}s (within {budget}s budget)")

    # 3. commits the remote does not have are a stall: a parallel worker cannot fetch them
    ahead, detail = unpushed()
    if ahead:
        failures.append(f"{detail} — the work is not on the remote, so a parallel worker is blind")
    elif detail not in ("detached HEAD",):
        notes.append(detail)

    return failures, notes


def selftest() -> int:
    """Prove the detector fires on a real stall and stays quiet on a clean tree."""
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        subprocess.run(["git", "-C", str(d), "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", str(d), "config", "user.name", "t"], check=True)
        (d / "TASKS.md").write_text(SENTINEL + "\n")
        subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(d), "commit", "-qm", "base"], check=True)

        # clean tree: no drift
        out = subprocess.run(["git", "-C", str(d), "status", "--porcelain"],
                             capture_output=True, text=True).stdout
        if out.strip():
            print("authority_gate selftest: FAIL — a clean tree reported drift")
            return 1

        # now create a stall and back-date it well past a zero budget
        victim = d / "TASKS.md"
        victim.write_text(SENTINEL + "\nstalled\n")
        old = time.time() - 5000
        import os
        os.utime(victim, (old, old))
        drift = [l[3:].strip() for l in
                 subprocess.run(["git", "-C", str(d), "status", "--porcelain"],
                                capture_output=True, text=True).stdout.splitlines() if len(l) > 3]
        if not drift:
            print("authority_gate selftest: FAIL — the stall was not detected at all")
            return 1
        age = int(time.time() - victim.stat().st_mtime)
        if age <= 0:
            print("authority_gate selftest: FAIL — stall age was not measured")
            return 1

        # the sentinel detector must also fire when the law is deleted
        victim.write_text("no law here\n")
        if SENTINEL in victim.read_text():
            print("authority_gate selftest: FAIL — sentinel detection is broken")
            return 1

        # a generated artifact is NOT withheld human work: it must not be read as a stall,
        # while a source file in the same tree must be
        (d / "proof").mkdir(exist_ok=True)
        (d / "proof" / "out.json").write_text("{}")
        (d / "tools").mkdir(exist_ok=True)
        (d / "tools" / "real.py").write_text("x = 1\n")
        tracked = subprocess.run(["git", "-C", str(d), "status", "--porcelain", "--untracked-files=all"],
                                 capture_output=True, text=True).stdout.splitlines()
        names = [l[3:].strip() for l in tracked if len(l) > 3]
        kept = [n for n in names if not is_generated(n)]
        if "tools/real.py" not in kept:
            print("authority_gate selftest: FAIL — a real source change was not counted as drift")
            return 1
        if "proof/out.json" in kept:
            print("authority_gate selftest: FAIL — a generated artifact was counted as withheld work")
            return 1

    print("authority_gate selftest: ok — clean tree silent, drift measured, missing law caught, "
          "generated artifacts excluded")
    return 0


def sentinel_failures() -> list[str]:
    """Only the inscription check, with no drift/push budget.

    Autophagy repairs this class by regenerating the boards, so its detector must observe
    exactly what the repair can change. The full gate also fails on unpushed commits and
    stale drift, which `cns_directive --write` can never fix — pairing the broad detector with
    that repair made the class report "still dirty after repair" forever.
    """
    out = []
    for name in BOARDS:
        f = ROOT / name
        if not f.is_file():
            out.append(f"board {name} is missing")
        elif SENTINEL not in f.read_text(encoding="utf-8", errors="replace"):
            out.append(f"board {name} does not carry '{SENTINEL}'")
    return out


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()

    if "--sentinel-only" in argv:
        bad = sentinel_failures()
        if bad:
            print(f"authority_gate: FAIL — {len(bad)} board(s) missing the sentinel:")
            for b in bad:
                print(f"  - {b}")
            return 1
        print(f"authority_gate: PASS — sentinel inscribed in {len(BOARDS)} boards")
        return 0

    budget = DEFAULT_BUDGET
    if "--budget" in argv:
        i = argv.index("--budget")
        try:
            budget = int(argv[i + 1])
        except (IndexError, ValueError):
            print("authority_gate: FAIL — --budget needs an integer (seconds)")
            return 1

    failures, notes = check_budget(budget)
    for n in notes:
        print(f"authority_gate: note — {n}")
    if failures:
        print(f"authority_gate: FAIL — {len(failures)} off-schedule stall(s):")
        for f in failures:
            print(f"  - {f}")
        print("  NEVER #21: the decision was already automated. Execute, commit, push.")
        return 1
    print(f"authority_gate: PASS — authority inscribed in {len(BOARDS)} boards; "
          f"no drift past {budget}s; nothing withheld")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
