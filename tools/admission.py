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

# Gates whose verdict is a function of the REMOTE state, not the content of the change.
# board_pulse compares local main to origin/main; the stall clock measures how long a
# finished change has sat unpushed; authority_gate flags the same thing. In a worktree
# those three are guaranteed red because the change has, by definition, not been pushed
# yet. They are not suppressed -- they are reported in their own column, and they resolve
# the instant the push lands. Every other red is a real content failure.
REMOTE_ONLY = ("board pulse", "stall clock", "authority gate")

# Red for a second structural reason: the chain gate hashes the tree against the CURRENT
# cycle's S01 baseline. Any governing-source change is therefore chain-red until a cycle
# seals it, and the prescribed repair is to run the cycle, not to edit anything. This is not
# a loophole: the cycle's own S14 runs the full suite and refuses to seal on failure, so a
# genuinely broken tree still cannot land through this path.
SEAL_ONLY = ("revitalization chain gate",)


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


def workflow_contract_errors(auto_text: str, workflow_texts: list[str],
                               ci_text: str) -> list[str]:
    """Prove the automation cannot admit a main-bound change after a single trial.

    This gate intentionally checks the executable workflow contract, not its prose:
    two fresh isolated rehearsals, exact candidate/base SHA checks, testnet-only repair,
    and no scheduled dependency write directly to main.
    """
    errors: list[str] = []
    required = (
        ("testnet trial 1/2", "trial 1 job missing"),
        ("testnet trial 2/2", "trial 2 job missing"),
        ("  trial_1:\n    name: testnet trial 1/2\n    needs: prepare_testnet", "trial 1 does not depend on preflight"),
        ("  trial_2:\n    name: testnet trial 2/2\n    needs: [prepare_testnet, trial_1]", "trial 2 does not depend on trial 1 and preflight"),
        ("needs: [prepare_testnet, trial_1, trial_2]", "main admission does not depend on both trials"),
        ("TESTED_SHA", "candidate SHA is not revalidated before merge"),
        ("TESTED_BASE", "main base SHA is not revalidated before merge"),
        ("branch=\"testnet/darkbot-", "scheduled dependency proposal is not isolated on testnet"),
        ("gh workflow run auto-merge.yml", "dependency proposal does not dispatch the admission workflow"),
    )
    for token, message in required:
        if token not in auto_text:
            errors.append(message)

    if auto_text.count("python3 tools/admission.py rehearse") < 2:
        errors.append("fewer than two full isolated admission rehearsals are configured")
    if "python3 tools/absolution_phase.py" not in auto_text or "python3 tools/admission.py" not in auto_text:
        errors.append("testnet preflight repair/admission preflight is missing")
    if "gh pr merge" not in auto_text or "merge_testnet:" not in auto_text:
        errors.append("automatic promotion is not gated through the testnet merge job")
    if re.search(r"git\s+push\s+(?:origin\s+)?(?:main|master)(?:\s|$)", auto_text):
        errors.append("automation contains a direct push to main/master")

    trial2 = auto_text.split("  trial_2:", 1)[1].split("\n  tests:", 1)[0] if "  trial_2:" in auto_text else ""
    if "needs.trial_1.result == 'success'" not in trial2:
        errors.append("trial 2 can run without trial 1 passing")
    merge = auto_text.split("  merge_testnet:", 1)[1].split("\n  merge_dependency:", 1)[0] if "  merge_testnet:" in auto_text else ""
    if ("needs.trial_1.result == 'success'" not in merge
            or "needs.trial_2.result == 'success'" not in merge):
        errors.append("main merge does not require both trial verdicts")

    if "python3 tools/absolution_phase.py --check" not in ci_text:
        errors.append("CI does not enforce read-only absolution before hashing")
    if re.search(r"run\s+[\"'][^\"\n]*absolution phase[^\"\n]*[\"']\s+python3 tools/absolution_phase.py\s*(?:\n|$)", ci_text):
        errors.append("CI invokes the repair phase instead of checking the carried candidate")

    for workflow in workflow_texts:
        for line in workflow.splitlines():
            if re.search(r"\buses\s*:", line):
                if not re.search(r"\buses\s*:\s*[^@\s]+@[0-9a-f]{40}(?:\s|$)", line.strip()):
                    errors.append("workflow action is not pinned to an immutable 40-character SHA")
                    break
    return errors


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

    workflow_dir = ROOT / ".github" / "workflows"
    auto_path = workflow_dir / "auto-merge.yml"
    ci_path = ROOT / "tools" / "ci.sh"
    if auto_path.is_file() and ci_path.is_file():
        workflow_texts = [p.read_text(encoding="utf-8") for p in sorted(workflow_dir.glob("*.yml"))]
        problems.extend(workflow_contract_errors(
            auto_path.read_text(encoding="utf-8"), workflow_texts,
            ci_path.read_text(encoding="utf-8")))

    return problems


# --------------------------------------------------------------------------------------
# rehearse: the real suite, on the exact bytes, in isolation
# --------------------------------------------------------------------------------------

def classify(fail_lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    content, remote, seal = [], [], []
    for line in fail_lines:
        low = line.lower()
        if any(tok in low for tok in SEAL_ONLY):
            seal.append(line)
        elif any(tok in low for tok in REMOTE_ONLY):
            remote.append(line)
        else:
            content.append(line)
    return content, remote, seal


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
        env["CI_LOG"] = str(log_path)
        cp = subprocess.run(["bash", "tools/ci.sh"], cwd=str(tree), env=env,
                            capture_output=True, text=True, timeout=1800)
        output = cp.stdout + cp.stderr
        log_path.write_text(output, encoding="utf-8")

        fails = [l for l in output.splitlines() if re.match(r"^--- .*: FAIL", l)]
        content, remote, seal = classify(fails)

        verdict = "PASS" if not content and not seal else "BLOCKED"
        print(f"admission: verdict={verdict} "
              f"(content reds={len(content)}, seal-pending reds={len(seal)}, "
              f"remote-state reds={len(remote)})")
        for line in content:
            print(f"  BLOCKING  {line}")
        for line in seal:
            print(f"  needs-seal  {line}")
        for line in remote:
            print(f"  resolves-on-push  {line}")
        if seal:
            print("admission: a governing-source change is unsealed -- run "
                  "`python3 tools/revitalization.py run`; its S14 re-runs this suite "
                  "and refuses to seal on a real failure.")
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

    workflow_path = ROOT / ".github" / "workflows" / "auto-merge.yml"
    workflow_text = workflow_path.read_text(encoding="utf-8") if workflow_path.is_file() else ""
    workflow_texts = [p.read_text(encoding="utf-8") for p in
                       sorted((ROOT / ".github" / "workflows").glob("*.yml"))]
    ci_path = ROOT / "tools" / "ci.sh"
    ci_text = ci_path.read_text(encoding="utf-8") if ci_path.is_file() else ""
    errors = workflow_contract_errors(workflow_text, workflow_texts, ci_text)
    check(not errors, "automation requires two isolated trials and immutable action pins",
          "; ".join(errors))
    broken = workflow_text.replace("testnet trial 2/2", "trial omitted") if workflow_text else ""
    check(bool(workflow_contract_errors(broken, workflow_texts, ci_text)),
          "workflow contract detects a missing second trial")
    labels = gate_labels('  run "chain gate" python3 x\n  run "chain gate" python3 y\n'
                         '  run "other" python3 z\n')
    check(labels == {"chain gate": 2, "other": 1}, "duplicate gate label is counted")
    content, remote, seal = classify([
        "--- drift gate (NEVER #22): FAIL (exit 1)",
        "--- board pulse (real-time push): FAIL (exit 1)",
        "--- revitalization chain gate: FAIL (exit 1)",
    ])
    check(content == ["--- drift gate (NEVER #22): FAIL (exit 1)"],
          "content red stays blocking")
    check(remote == ["--- board pulse (real-time push): FAIL (exit 1)"],
          "remote-state red is separated, not hidden")
    check(seal == ["--- revitalization chain gate: FAIL (exit 1)"],
          "seal-pending red is named, neither blocking nor hidden")
    check(classify(["--- authority gate (NEVER #21): FAIL (exit 1)"])[1] != [],
          "authority gate classified as remote-state")

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
