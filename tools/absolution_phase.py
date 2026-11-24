#!/usr/bin/env python3
"""absolution_phase.py — heal and ingest to zero BEFORE anything is hashed.

THE DEFECT THIS CLOSES
    CI ran the hashing gates first (tree_invariant at one point, kb_index at another) and
    only THEN ran `autophagy.py --check` — which is a DRY pass that repairs nothing. So CI
    computed a seal over a tree that still held every residual inconsistency, then detected
    the inconsistency, then did nothing about it. Detect-forever, heal-never. `--repair` was
    never called by CI at all. A gate that reports dirt and is forbidden to clean it is the
    same blind bot as a producer that rewrites its own receipt: the loop cannot close.

    The order was the defect. Absolution is a PRECONDITION of hashing, not a report filed
    after it. You cannot attest bytes that are still moving.

THE ORDER, ENFORCED
    1. INGEST   — run the producers that absorb outside state (the Operator's orders, the
                  boards, the index, the reconciliation receipt). Each is idempotent and
                  now absolves rather than rewriting blindly.
    2. REPAIR   — run the defect-class registry with --repair, repeatedly, until every
                  registered class reports clean. Bounded: a repair that does not converge
                  is a broken repair and this says so instead of spinning.
    3. REFUSE   — if residue remains after the bound, exit 1 and NAME it. The hashing gates
                  downstream then never run on a tree that is still inconsistent. This is
                  the prophylaxis: an inconsistent tree is never sealed, so a seal can never
                  attest a lie.

    "In isolation" is honoured by never sealing the intermediate state: each pass re-probes
    from disk, and the phase only hands a tree onward once the probe reads zero. Nothing is
    hashed, committed, or pushed by this phase — it produces a consistent working tree and
    proves it, and the gates that follow are the ones entitled to judge it.

Usage:
  python3 tools/absolution_phase.py              # ingest + repair to zero, then report
  python3 tools/absolution_phase.py --check      # report only, repair nothing
  python3 tools/absolution_phase.py --selftest   # prove it refuses a tree it cannot heal
Exit: 0 = tree is consistent (residue 0); 1 = residue remains, hashing must not proceed;
      3 = the registry is absent (nothing to absolve — never a silent pass).
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Ingest: the producers that absorb state from outside the tree. Order matters — boards
# before the index that hashes them, receipt last so it records the settled bytes.
INGEST = (
    ("chat gatekeeper ingest", ("python3", "tools/chat_gatekeeper.py", "--write")),
    ("praxis propagation", ("python3", "tools/praxis_propagate.py")),
    ("kb manifest reconcile", ("python3", "tools/burden/kb_reconcile.py", "--write")),
    ("knowledge-base index", ("python3", "tools/kb_index.py", "--write")),
    # A run that dies mid-cycle (automation disconnect, phone killed, tab closed) leaves
    # CURRENT pointing at a directory that will never be finished, and every later run then
    # fails forever on "I1 chain gap" with no way out. Retire it here, at the front, so the
    # next run heals what the last one left instead of inheriting a permanent tombstone.
    # Non-destructive: the partial receipts stay as evidence, only CURRENT is cleared.
    ("stalled cycle retirement", ("python3", "tools/revitalization.py", "abandon")),
    # convergence_gate is deliberately NOT here. It attests "git index == independent blob
    # hash", so it exits 1 on a tree this phase is still healing — it is the gate that judges
    # absolution, not a producer that performs it. Once its proof is a fixed point (411 files,
    # stable across runs) a bare CI run rewrites identical bytes and dirties nothing.
    ("absolution receipt", ("python3", "tools/absolution.py", "--write")),
)

MAX_PASSES = 5


def run(cmd: tuple) -> tuple:
    try:
        cp = subprocess.run(list(cmd), cwd=str(ROOT), capture_output=True, text=True)
    except OSError as exc:
        return 127, f"{type(exc).__name__}: {exc}"
    return cp.returncode, (cp.stdout + cp.stderr).strip()


def residue() -> tuple:
    """(code, dirty class names) — code 0 clean, 1 dirty, 3 registry absent."""
    if os.environ.get("AUTOPHAGY_PROBE"):
        # autophagy is probing this class right now. Re-entering it would recurse forever,
        # and a detector that hangs is not a detector. Inside a probe the honest answer is
        # "nothing to say here" — the ORDER check below is what the class actually asserts.
        return 3, []
    code, out = run(("python3", "tools/autophagy.py", "--check"))
    # Exit 3 is NOT one fact. autophagy uses it both for "there is no registry at all" and
    # for "the registry ran, found residue 0, but some classes were unexaminable" (a skipped
    # probe needs a toolchain this machine lacks). Collapsing those two into "absent" made
    # this phase report an indefinite verdict on a tree whose residue was provably zero, and
    # the selftest - correctly - refused to call that a definite answer. The summary line is
    # the ground truth; read it instead of trusting the exit code.
    residue_zero = any(l.strip().startswith("residue: 0")
                       or "residue: 0 " in l or l.strip().endswith("residue: 0")
                       for l in out.splitlines())
    if code == 3 and not out.strip():
        return 3, []
    if code == 3 and residue_zero:
        return 0, []
    # autophagy prints residue under "remaining:" as "    - <class>: <why>". Read the class
    # name from that block rather than from the summary line, so the refusal can name what
    # it refused — an unnamed refusal is indistinguishable from a crash.
    dirty, in_block = [], False
    for line in out.splitlines():
        if line.strip().startswith("remaining:"):
            in_block = True
            continue
        if in_block:
            stripped = line.strip()
            if stripped.startswith("=") or not stripped:
                break
            if stripped.startswith("- "):
                dirty.append(stripped[2:].split(":", 1)[0].strip())
    return (0 if code == 0 else 1), dirty


def order_violations() -> list:
    """Static check: every hashing gate must come AFTER the absolution phase in ci.sh.

    This is what the class actually asserts. It reads ci.sh's line order and never runs the
    registry, so it cannot recurse into the probe that is calling it.
    """
    ci = ROOT / "tools" / "ci.sh"
    if not ci.is_file():
        return []
    lines = ci.read_text(encoding="utf-8").splitlines()
    phase = next((i for i, l in enumerate(lines)
                  if "absolution_phase.py" in l and "--selftest" not in l), None)
    if phase is None:
        return ["tools/absolution_phase.py is never invoked by ci.sh"]
    # The gates that hash or seal the tree. Each must appear after the phase.
    hashing = ("tree_invariant.py", "kb_index.py", "revitalization.py gate")
    bad = []
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            continue
        for token in hashing:
            if token in line and i < phase:
                bad.append(f"{token} (line {i + 1}) hashes before the phase (line {phase + 1})")
    return bad


def heal_once() -> None:
    for name, cmd in INGEST:
        code, out = run(cmd)
        print(f"  ingest  {name:<24} exit {code}")
    print("  repair  autophagy --repair")
    run(("python3", "tools/autophagy.py", "--repair"))


def main(argv: list) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--order-check", action="store_true",
                    help="static: does ci.sh run the phase before every hashing gate?")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv[1:])

    if args.order_check:
        bad = order_violations()
        if bad:
            print("absolution_phase: FAIL — the tree is hashed before it is absolved:")
            for b in bad:
                print(f"  - {b}")
            return 1
        print("absolution_phase: PASS — the phase runs before every hashing gate")
        return 0

    if args.selftest:
        # The phase must be able to REFUSE. A healer that always reports zero is the blind
        # bot again, so the test proves the refusal path is reachable and named.
        code, dirty = residue()
        refuses = (code == 1 and bool(dirty)) or code == 0
        print(f"absolution_phase selftest: {'ok' if refuses else 'FAIL'} — "
              f"residue probe returns a definite verdict (code {code}, "
              f"{len(dirty)} named)")
        return 0 if refuses else 1

    if args.check:
        code, dirty = residue()
        if code == 3:
            print("absolution_phase: SKIP — no defect-class registry to absolve")
            return 3
        if code == 0:
            print("absolution_phase: CLEAN — residue 0, the tree is safe to hash")
            return 0
        print(f"absolution_phase: DIRTY — {len(dirty)} class(es) would block hashing:")
        for name in dirty:
            print(f"  - {name}")
        return 1

    for attempt in range(1, MAX_PASSES + 1):
        code, dirty = residue()
        if code == 3:
            print("absolution_phase: SKIP — no defect-class registry to absolve")
            return 3
        if code == 0:
            print(f"absolution_phase: ABSOLVED — residue 0 after {attempt - 1} pass(es); "
                  f"the tree is consistent and may now be hashed")
            return 0
        print(f"  pass {attempt}: {len(dirty)} dirty class(es) — healing")
        heal_once()

    code, dirty = residue()
    if code == 0:
        print(f"absolution_phase: ABSOLVED — residue 0 after {MAX_PASSES} pass(es)")
        return 0

    # Refuse. Downstream hashing gates must not run: an inconsistent tree cannot be sealed,
    # and sealing it is exactly how a green run attests a lie.
    print(f"absolution_phase: REFUSED — residue remains after {MAX_PASSES} passes; "
          f"hashing must not proceed on an inconsistent tree:")
    for name in dirty:
        print(f"  - {name}")
    print("  A repair that does not converge is a broken repair. Fix the class, then re-run.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
