#!/usr/bin/env python3
"""nt_gate — run the NT corpus through SAVF and prove every contradiction is resolved.

SPI-15: a law that is not an executable gate is a note. This gate makes the NT
reconciliation executable.

The corpus is a set of claims (proof/nt_claims.json). SAVF (savf.py ledger) grades
each claim: A=analysis, W=witness (re-runs its evidence command), R=derived (holds
iff its parents hold), D=declared, C=contradiction (a claim that conflicts with
reality and is not yet resolved).

This gate FAILS (exit 1) unless:
  1. the corpus files exist under docs/nt/ (the derivation is present, not just cited);
  2. savf.py ledger --run reports 0 problem(s) (no failed witness, no unsupported derivation);
  3. every C (contradiction) claim has exactly one resolution in
     proof/nt_reconciliation.json;
  4. every resolution's evidence command re-runs green (exit 0 and prints its marker);
  5. no resolution is orphaned (a resolution with no matching contradiction).

Nothing is asserted. Every resolution is a re-run evidence command. A contradiction
that is not resolved, or resolved by a command that fails, stops the gate.
"""
import json
import os
import shlex
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAIMS = os.path.join(ROOT, "proof", "nt_claims.json")
RECON = os.path.join(ROOT, "proof", "nt_reconciliation.json")
SAVF = os.path.join(ROOT, "savf.py")
CORPUS_DIR = os.path.join(ROOT, "docs", "nt")


def fail(msg):
    print(f"nt_gate: FAIL — {msg}")
    sys.exit(1)


def run_cmd(cmd, expect, timeout=120):
    """Re-run an evidence command (shell-free, like savf's _cmd). True iff exit 0
    and `expect` appears in stdout+stderr."""
    parts = shlex.split(cmd)
    if parts and parts[0] in ("python", "python3"):
        parts[0] = sys.executable
    try:
        p = subprocess.run(parts, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"could not run: {e}"
    out = p.stdout + p.stderr
    ok = p.returncode == 0 and expect in out
    return ok, out.strip().splitlines()[-1] if out.strip() else "(no output)"


def main():
    # 1. the derivation must be present, not merely cited.
    if not os.path.isdir(CORPUS_DIR):
        fail("docs/nt/ is missing — the NT corpus is cited but not carried (NEVER #16).")
    carried = sorted(f for f in os.listdir(CORPUS_DIR) if not f.startswith("."))
    if not carried:
        fail("docs/nt/ is empty.")

    if not os.path.isfile(CLAIMS):
        fail("proof/nt_claims.json is missing — the corpus has not been run through SAVF.")
    if not os.path.isfile(SAVF):
        fail("savf.py is missing.")

    claims = json.load(open(CLAIMS))
    contradictions = {c["id"] for c in claims if c.get("kind") == "C"}

    # 2. savf must find no failed witness and no unsupported derivation.
    p = subprocess.run([sys.executable, SAVF, "ledger", CLAIMS, "--run"],
                       cwd=ROOT, capture_output=True, text=True, timeout=600)
    tail = (p.stdout + p.stderr).strip().splitlines()
    summary = tail[-1] if tail else ""
    if p.returncode != 0:
        fail(f"savf ledger exited {p.returncode}: {summary}")
    if "0 problem(s)" not in summary:
        fail(f"savf ledger reports problems: {summary}")

    # 3. every contradiction must be resolved; no orphans.
    if not os.path.isfile(RECON):
        fail(f"{len(contradictions)} contradiction(s) but no proof/nt_reconciliation.json.")
    recon = json.load(open(RECON))
    resolved_ids = {r["id"] for r in recon}
    unresolved = contradictions - resolved_ids
    orphan = resolved_ids - contradictions
    if unresolved:
        fail("unresolved contradiction(s): " + ", ".join(sorted(unresolved)))
    if orphan:
        fail("orphaned resolution(s) (no matching contradiction): " + ", ".join(sorted(orphan)))

    # 4. every resolution re-runs green.
    print(f"nt_gate: {len(claims)} claims, {len(contradictions)} contradictions, "
          f"{len(recon)} resolutions")
    print(f"  corpus carried: {len(carried)} files in docs/nt/")
    bad = 0
    for r in sorted(recon, key=lambda x: x["id"]):
        ev = r.get("evidence") or {}
        cmd, expect = ev.get("cmd"), ev.get("expect")
        if not cmd or expect is None:
            print(f"  [FAIL] {r['id']:24s} no evidence command")
            bad += 1
            continue
        ok, note = run_cmd(cmd, expect)
        print(f"  [{'PASS' if ok else 'FAIL'}] {r['id']:24s} "
              f"{r.get('resolved_as', ''):10s} {note}")
        if not ok:
            bad += 1

    if bad:
        fail(f"{bad} resolution(s) did not re-run green.")
    print(f"nt_gate: PASS — every contradiction resolved to absolution; "
          f"savf reports {summary}")


if __name__ == "__main__":
    main()
