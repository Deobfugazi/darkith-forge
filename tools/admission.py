#!/usr/bin/env python3
"""Admission control: prove a change BEFORE it lands, not after.

The failure this closes is not "a gate was wrong". Eight runs on main went red in one day
because every gate ran on the far side of the push. A gate you can only read after landing
cannot prevent anything; it can only narrate the damage. The pipeline was measuring the
wreck instead of screening the traffic.

Two questions, both answered before the push:

  preflight  Does this change COLLIDE with work that already exists? Law ids, gate labels,
             tool names, derived artifacts gone stale, drift already sitting in the tree.
  rehearse   Would the real `tools/ci.sh` pass on the EXACT bytes about to be pushed?
             Asked in an isolated git worktree, so the answer cannot be contaminated by
             the run that produces it.

Neither command edits a gate, a workflow, or a live ledger. Nothing here grants authority
to mint, spend, deploy, or merge. It only refuses to let a known-red change leave the
machine, which is the one decision that was never being made.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROOF = ROOT / "proof" / "admission"

# Sigma-zero rehearsal treats every failure, skip, and inactive required gate as blocking.


def sh(cmd: list[str], cwd: Path = ROOT, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


def git(*args: str, cwd: Path = ROOT) -> str:
    return sh(["git", *args], cwd=cwd).stdout


# --------------------------------------------------------------------------------------
# preflight: vector collisions
# --------------------------------------------------------------------------------------

DECL = re.compile(r"^\s*[─-]{2,}\s*(NEVER|MUST) #(\d+)\b", re.M)


def law_ids(text: str, kind: str) -> dict[str, int]:
    """Count DECLARATIONS only, not mentions.

    A law's id appears in cross-references all over the board ("NEVER #11 one tree" is cited
    in a dozen prose lines). Counting mentions would report every long-standing law as a
    collision and this gate could never pass -- which is the precise failure it exists to
    prevent. A declaration is the one canonical header line.
    """
    ids: dict[str, int] = {}
    for m in DECL.finditer(text):
        if m.group(1) != kind:
            continue
        ids[m.group(2)] = ids.get(m.group(2), 0) + 1
    return ids


def gate_labels(ci_text: str) -> dict[str, int]:
    """Every `run "label" ...` in ci.sh. A label registered twice means two gates share
    one line in the summary, so one can fail silently behind the other's PASS."""
    labels: dict[str, int] = {}
    for m in re.finditer(r'^\s*run\s+"([^"]+)"', ci_text, re.M):
        labels[m.group(1)] = labels.get(m.group(1), 0) + 1
    return labels


def added_paths(diff_names: str) -> list[str]:
    """Paths ADDED relative to a base, from 'git diff --name-only --diff-filter=A' output."""
    return [l.strip() for l in diff_names.splitlines() if l.strip()]


def cross_branch_collisions() -> list[str]:
    """R3 / SPI-40 P3: preflight must compare against origin/main, not only the local tree.

    The real collision that built this check: two agents created tools/drift_gate.py on
    two branches at once, and each preflight read only its own tree, so neither saw the
    other until CI differed. Two checks, both honest about what they can and cannot see:

      1. TOOL COLLISION — a tools/ file ADDED on this branch (or untracked) that
         origin/main already tracks is a collision: the other agent landed it, and this
         branch must converge on their bytes, not fork the name.
      2. LAW COLLISION — a law id DECLARED on origin/main but absent from the local
         DARKITH.md means a naive merge would silently drop a landed law.
    """
    if git("rev-parse", "--verify", "--quiet", "origin/main").strip() == "":
        return []  # no origin/main visible from here: nothing to compare against, said so

    problems: list[str] = []

    added = set(added_paths(git("diff", "--name-only", "--diff-filter=A", "origin/main...HEAD")))
    added.update(p for p in added_paths(git("ls-files", "--others", "--exclude-standard", "tools")))
    for path in sorted(added):
        if path.startswith("tools/") and path.endswith(".py"):
            if sh(["git", "cat-file", "-e", f"origin/main:{path}"]).returncode == 0:
                problems.append(
                    f"cross-branch tool collision: {path} already exists on origin/main "
                    f"(another agent landed it) — converge on THEIR bytes, do not fork the name")

    origin_law = git("show", "origin/main:DARKITH.md") if sh(
        ["git", "cat-file", "-e", "origin/main:DARKITH.md"]).returncode == 0 else ""
    if origin_law:
        darkith = ROOT / "DARKITH.md"
        if darkith.is_file():
            origin_ids = set(law_ids(origin_law, "NEVER")) | set(law_ids(origin_law, "MUST"))
            local_ids = set(law_ids(darkith.read_text(encoding="utf-8"), "NEVER")) | \
                        set(law_ids(darkith.read_text(encoding="utf-8"), "MUST"))
            for kind_num in sorted(origin_ids - local_ids):
                problems.append(
                    f"cross-branch law collision: {kind_num} is declared on origin/main but "
                    f"nowhere in this tree — merging here would silently drop a landed law")

    return problems


def preflight() -> list[str]:
    problems: list[str] = []

    darkith = ROOT / "DARKITH.md"
    if darkith.is_file():
        text = darkith.read_text(encoding="utf-8")
        for kind in ("NEVER", "MUST"):
            for num, count in sorted(law_ids(text, kind).items(), key=lambda kv: int(kv[0])):
                if count > 1:
                    problems.append(f"law id collision: {kind} #{num} is declared {count} times")

    ci = ROOT / "tools" / "ci.sh"
    if ci.is_file():
        for label, count in sorted(gate_labels(ci.read_text(encoding="utf-8")).items()):
            if count > 1:
                problems.append(f"gate label collision: '{label}' registered {count} times")

    # Derived artifacts are the most common real cause of red, and they are invisible
    # until CI says so. Ask the generators directly, using the invocation each one
    # actually accepts: kb_index checks when given no arguments, make-oneshot when --check.
    for cmd, name in (
        (["python3", "tools/kb_index.py"], "kb_index"),
        (["python3", "build/make-oneshot.py", "--check"], "one-shot payload"),
    ):
        if (ROOT / cmd[1]).is_file():
            cp = sh(cmd)
            if cp.returncode != 0:
                problems.append(f"{name}: stale derived artifact (regenerate it)")

    drift = [l[3:] for l in git("status", "--porcelain", "--untracked-files=no").splitlines()
             if l.strip()]
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        from authority_gate import is_generated  # noqa: PLC0415
        drift = [p for p in drift if not is_generated(p)]
    except Exception:  # noqa: BLE001
        pass
    if drift:
        problems.append(f"uncommitted drift in {len(drift)} file(s): " + ", ".join(drift[:5]))

    problems.extend(cross_branch_collisions())

    return problems


# --------------------------------------------------------------------------------------
# rehearse: the real suite, on the exact bytes, in isolation
# --------------------------------------------------------------------------------------

def classify(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    failures = [line for line in lines if re.match(r"^--- .*: FAIL", line)]
    skips = [line for line in lines if re.match(r"^--- .*: SKIP", line)]
    inactive = [line for line in lines if re.match(r"^INACTIVE:", line)]
    return failures, skips, inactive


def rehearse(keep: bool = False) -> int:
    PROOF.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    log_path = PROOF / f"{stamp}.log"

    tmp = Path(tempfile.mkdtemp(prefix="admission-"))
    tree = tmp / "tree"
    try:
        add = sh(["git", "worktree", "add", "--detach", str(tree), "HEAD"])
        if add.returncode != 0:
            print(f"admission: cannot create worktree: {add.stderr.strip()}")
            return 2

        # Replay the uncommitted change into the worktree so the suite sees the bytes that
        # are about to be pushed, not the bytes that are already committed.
        diff = sh(["git", "diff", "HEAD", "--binary"]).stdout
        if diff.strip():
            applied = subprocess.run(["git", "apply", "--whitespace=nowarn", "-"],
                                     cwd=str(tree), input=diff, text=True,
                                     capture_output=True)
            if applied.returncode != 0:
                print(f"admission: cannot replay change: {applied.stderr.strip()}")
                return 2
        for line in git("ls-files", "--others", "--exclude-standard").splitlines():
            src = ROOT / line
            if src.is_file():
                dst = tree / line
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        # A fresh worktree has no gitignored toolchain (.tools/), so the §19 compile proof
        # would report L-07 OPEN and manufacture a red that does not exist on the real
        # branch. Share the toolchain rather than copy it: it is large and read-only here.
        tools_dir = ROOT / ".tools"
        if tools_dir.is_dir() and not (tree / ".tools").exists():
            (tree / ".tools").symlink_to(tools_dir, target_is_directory=True)

        print(f"admission: rehearsing tools/ci.sh on {len(diff.splitlines())} diff line(s) "
              f"+ uncommitted files, in {tree}")
        env = os.environ.copy()
        env.pop("REVITALIZATION_BOOTSTRAP", None)  # a rehearsal is not a cycle
        env["SIGMA_ZERO"] = "1"
        env["CI_LOG"] = str(log_path)
        cp = subprocess.run(["bash", "tools/ci.sh"], cwd=str(tree), env=env,
                            capture_output=True, text=True, timeout=1800)
        output = cp.stdout + cp.stderr
        log_path.write_text(output, encoding="utf-8")

        failures, skips, inactive = classify(output.splitlines())
        verdict = "PASS" if cp.returncode == 0 and not failures and not skips and not inactive else "BLOCKED"
        print(f"admission: verdict={verdict} "
              f"(failures={len(failures)}, skips={len(skips)}, inactive={len(inactive)}, "
              f"ci_exit={cp.returncode})")
        for line in failures:
            print(f"  BLOCKING  {line}")
        for line in skips:
            print(f"  BLOCKING  {line} — SKIP is not sigma-zero")
        for line in inactive:
            print(f"  BLOCKING  {line} — INACTIVE acceptance condition is unresolved")
        print(f"admission: full log -> {log_path.relative_to(ROOT)}")
        return 0 if verdict == "PASS" else 1
    finally:
        sh(["git", "worktree", "remove", "--force", str(tree)])
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------------------
# the hook: refuse to push a known-red change
# --------------------------------------------------------------------------------------

HOOK = """#!/bin/sh
# Installed by tools/admission.py --install-hook. Refuses to push a change that the real
# suite already rejects. Bypass once with ADMISSION_BYPASS=1 when you have a reason.
[ "$ADMISSION_BYPASS" = "1" ] && exit 0
python3 tools/admission.py rehearse || {
  echo "admission: push refused -- the suite is red on these exact bytes." >&2
  echo "admission: fix it, or re-run with ADMISSION_BYPASS=1 to override." >&2
  exit 1
}
"""


def install_hook() -> int:
    hooks = Path(git("rev-parse", "--git-dir").strip()) / "hooks"
    hooks = (ROOT / hooks) if not hooks.is_absolute() else hooks
    hooks.mkdir(parents=True, exist_ok=True)
    path = hooks / "pre-push"
    path.write_text(HOOK, encoding="utf-8")
    path.chmod(0o755)
    print(f"admission: pre-push hook installed at {path}")
    return 0


# --------------------------------------------------------------------------------------

def selftest() -> int:
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        ok = ok and cond

    decl = "─── NEVER #22 (A) ───\nbody\n─── NEVER #22 (B) ───\nbody\n─── NEVER #23 (C) ───\n"
    check(law_ids(decl, "NEVER")["22"] == 2, "duplicate DECLARATION is counted")
    check(law_ids(decl, "NEVER")["23"] == 1, "unique declaration counted once")
    # The regression that mattered: prose mentions are not declarations. A board citing
    # "NEVER #11" a dozen times is normal, and must never read as a collision.
    check(law_ids("NEVER #11 in prose\nNEVER #11 again in prose\n", "NEVER") == {},
          "prose mentions are not counted as declarations")
    check(law_ids("─── MUST #42 (X) ───\n", "MUST") == {"42": 1}, "MUST declaration counted")
    labels = gate_labels('  run "chain gate" python3 x\n  run "chain gate" python3 y\n'
                         '  run "other" python3 z\n')
    check(labels == {"chain gate": 2, "other": 1}, "duplicate gate label is counted")
    failures, skips, inactive = classify([
        "--- drift gate (NEVER #22): FAIL (exit 1)",
        "--- board pulse: SKIP (exit 3)",
        "INACTIVE: required evidence deferred",
    ])
    check(failures == ["--- drift gate (NEVER #22): FAIL (exit 1)"],
          "every failure remains blocking")
    check(skips == ["--- board pulse: SKIP (exit 3)"],
          "SKIP is classified as blocking")
    check(inactive == ["INACTIVE: required evidence deferred"],
          "INACTIVE evidence is classified as blocking")

    # R3 / SPI-40 P3: cross-branch collision detection.
    check(added_paths("tools/drift_gate.py\ntools/ci.sh\n\n") ==
          ["tools/drift_gate.py", "tools/ci.sh"], "added paths parsed line by line")
    check(added_paths("") == [], "empty diff adds nothing")
    check(law_ids("─── NEVER #22 (T) ───\n", "NEVER") == {"22": 1},
          "origin-side extraction reads the canonical header")

    print(f"admission selftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    if "--install-hook" in argv:
        return install_hook()
    if "rehearse" in argv:
        return rehearse()
    problems = preflight()
    if problems:
        print(f"admission preflight: BLOCKED ({len(problems)} collision(s))")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("admission preflight: PASS -- no law, gate, artifact or drift collision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
