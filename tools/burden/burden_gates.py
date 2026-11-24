#!/usr/bin/env python3
"""burden_gates.py — the two mechanical gates the first rehearsal disclosed as ABSENT.

BURDEN-GATE-1  double-count registry
    Two burden records claiming the same id, or two records covering the same
    (path, sha) baseline, must be refused by CODE. The first rehearsal refused its
    duplicate-id phantom by admission review — a human reading it — and wrote the
    hole down as an open defect. Written down is not closed. This is the closure.

BURDEN-GATE-2  witness strength
    A witness whose output does not depend on the evidence is not evidence. The
    refusal must be mechanical: run the witness twice over DIFFERENT evidence and
    require DIFFERENT output. A witness that prints its own expected token no matter
    what it is given fails here, by measurement, not by review.

Both gates are fail-closed: any doubt is a refusal. `selftest` proves each gate
fires on a phantom AND stays silent on a good record, because a gate that cannot be
shown to fire is indistinguishable from no gate.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


# ----------------------------------------------------------------------------- GATE 1
def gate1_duplicate_registry(records: list[dict]) -> list[str]:
    """Refuse duplicate burden ids and duplicate baselines. Fail-closed."""
    problems: list[str] = []
    seen_ids: dict[str, int] = {}
    seen_baselines: dict[str, int] = {}

    for index, rec in enumerate(records, 1):
        rid = rec.get("id")
        if not rid:
            problems.append(f"GATE1_NO_ID: record {index} has no id")
            continue
        if rid in seen_ids:
            problems.append(
                f"GATE1_DUPLICATE_ID: {rid!r} claimed by records "
                f"{seen_ids[rid]} and {index} — double count refused")
        else:
            seen_ids[rid] = index

        baseline = rec.get("baseline_key") or _baseline_key(rec)
        if baseline:
            if baseline in seen_baselines:
                problems.append(
                    f"GATE1_DUPLICATE_BASELINE: {baseline!r} claimed by records "
                    f"{seen_baselines[baseline]} and {index} — same absence counted twice")
            else:
                seen_baselines[baseline] = index
    return problems


def _baseline_key(rec: dict) -> str:
    path = rec.get("path")
    sha = rec.get("base_sha")
    if not path or not sha:
        return ""
    return hashlib.sha256(f"{path}@{sha}".encode()).hexdigest()[:16]


# ----------------------------------------------------------------------------- GATE 2
def gate2_witness_strength(witness: pathlib.Path, good_tree: pathlib.Path,
                           broken_tree: pathlib.Path, timeout: int = 120) -> list[str]:
    """Refuse a witness whose output is the same on good and broken evidence.

    A real witness must be SENSITIVE: good tree -> pass token, broken tree -> not
    that token. If both runs agree, the witness is constant-output and carries no
    evidence, however convincing its text looks.
    """
    problems: list[str] = []
    good = _run(witness, good_tree, timeout)
    broken = _run(witness, broken_tree, timeout)

    if good is None or broken is None:
        return ["GATE2_UNRUNNABLE: witness did not complete on both trees"]

    good_out, good_rc = good
    broken_out, broken_rc = broken

    if good_out == broken_out and good_rc == broken_rc:
        problems.append(
            "GATE2_CONSTANT_OUTPUT: witness produced identical output and exit code on "
            f"intact and tampered evidence (rc={good_rc}) — it is not reading its input")
    if good_rc != 0:
        problems.append(
            f"GATE2_GOOD_TREE_FAILS: witness exited {good_rc} on INTACT evidence; "
            "a witness that fails on good bytes proves nothing")
    if broken_rc == 0:
        problems.append(
            "GATE2_BROKEN_TREE_PASSES: witness exited 0 on TAMPERED evidence; "
            "it cannot distinguish intact from broken")
    return problems


def _run(witness: pathlib.Path, tree: pathlib.Path, timeout: int):
    try:
        cp = subprocess.run([sys.executable, str(witness)], cwd=str(tree),
                            capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return (cp.stdout.strip() + cp.stderr.strip(), cp.returncode)


# ----------------------------------------------------------------------------- selftest
def selftest() -> int:
    failures = []

    def check(name, got, want_fire):
        fired = bool(got)
        ok = fired == want_fire
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        if not ok:
            failures.append(name)
        return ok

    print("BURDEN-GATE-1 (duplicate registry)")
    good = [{"id": "A", "path": "p", "base_sha": "s1"}]
    check("silent on one good record", gate1_duplicate_registry(good), False)
    check("silent on two distinct records",
          gate1_duplicate_registry([{"id": "A", "path": "p", "base_sha": "s1"},
                                    {"id": "B", "path": "q", "base_sha": "s2"}]), False)
    check("FIRES on duplicate id",
          gate1_duplicate_registry([{"id": "A", "path": "p", "base_sha": "s1"},
                                    {"id": "A", "path": "q", "base_sha": "s2"}]), True)
    check("FIRES on duplicate baseline under different ids",
          gate1_duplicate_registry([{"id": "A", "path": "p", "base_sha": "s1"},
                                    {"id": "B", "path": "p", "base_sha": "s1"}]), True)
    check("FIRES on record with no id",
          gate1_duplicate_registry([{"path": "p", "base_sha": "s1"}]), True)

    print("BURDEN-GATE-2 (witness strength)")
    tmp = pathlib.Path("/tmp/burden_gate2_selftest")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    good_tree = tmp / "good"
    broken_tree = tmp / "broken"
    for t in (good_tree, broken_tree):
        (t / "evidence").mkdir(parents=True)
    (good_tree / "evidence" / "data.txt").write_text("INTACT")
    (broken_tree / "evidence" / "data.txt").write_text("TAMPERED")

    real = tmp / "real_witness.py"
    real.write_text(
        "import hashlib,pathlib,sys\n"
        "p=pathlib.Path('evidence/data.txt')\n"
        "if not p.is_file(): print('MISSING'); sys.exit(1)\n"
        "h=hashlib.sha256(p.read_bytes()).hexdigest()\n"
        "print('OK' if h==hashlib.sha256(b'INTACT').hexdigest() else 'TAMPER')\n"
        "sys.exit(0 if h==hashlib.sha256(b'INTACT').hexdigest() else 1)\n")
    check("silent on a REAL witness", gate2_witness_strength(real, good_tree, broken_tree), False)

    const = tmp / "const_witness.py"
    const.write_text("print('EXPECT:ALL_GOOD')\n")
    check("FIRES on constant-output witness",
          gate2_witness_strength(const, good_tree, broken_tree), True)

    always_pass = tmp / "always_pass.py"
    always_pass.write_text("print('OK')\n")
    check("FIRES on witness that passes tampered evidence",
          gate2_witness_strength(always_pass, good_tree, broken_tree), True)

    always_fail = tmp / "always_fail.py"
    always_fail.write_text("import sys\nprint('BAD')\nsys.exit(1)\n")
    check("FIRES on witness that fails good evidence",
          gate2_witness_strength(always_fail, good_tree, broken_tree), True)

    shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nBURDEN GATES SELFTEST: {'PASS' if not failures else 'FAIL'} "
          f"({len(failures)} failed)")
    return 0 if not failures else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
    raise SystemExit(2)
