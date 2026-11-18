#!/usr/bin/env python3
"""absolution_admission.py — the gated ABSOLUTION ADMISSION TEST for a noveltreatise.

A noveltreatise is admitted into the carried corpus (`docs/nt/`) only when it is
truthful down to the verifiable bit. Nothing here is asserted; every claim is either
re-walked by an evidence command or marked as a boundary. The gate is fail-closed.

Claim kinds (the SAVF ledger vocabulary, re-used, not re-implemented):

  W  witness       re-runs `evidence.cmd`; passes iff exit 0 and `evidence.expect`
                   appears in the output. A witness MUST carry an external referent.
  R  derived       holds iff every `derived_from` parent is declared or verified.
  A  analysis      the author's synthesis; the uncertainty must be stated (INFERRED).
  C  contradiction a claim that conflicts with reality; it MUST have exactly one
                   reconciliation in the reconciliation ledger, and that
                   reconciliation's evidence command MUST re-run green.

The gate FAILS (exit 1) unless ALL hold:

  1. the treatise is CARRIED at docs/nt/NT-<roman>.txt (not merely cited at the root);
  2. the claims ledger passes `savf ledger --run` with 0 problem(s), and NO witness
     was silently downgraded to a bare declaration;
  3. every contradiction has exactly one resolution and no resolution is orphaned;
  4. every resolution's evidence command re-runs green (exit 0 + its marker);
  5. the treatise's own corpus count is TRUE: a claim about the "N preceding/prior
     noveltreatises" must equal the number actually carried, and a claim about "the
     N noveltreatises" (the whole set, this one included) must equal carried + 1.
     This is the defect class that let a treatise say "twelve preceding" when only
     eleven existed.
  6. no unresolved mechanism is smuggled as RESOLVED: a `[MECHANISM NOT DERIVED`
     boundary must be named in a part flagged EXPOSABLE, never hidden.

Usage:
  python3 tools/absolution_admission.py
  python3 tools/absolution_admission.py --roman XII \
      --claims proof/nt_xii_claims.json --recon proof/nt_xii_reconciliation.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shlex
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "docs" / "nt"

WORD = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}

# "the twelve preceding noveltreatises", "the eleven prior noveltreatises"
PRECEDING = re.compile(r"the (\w+) (?:preceding|prior) noveltreatises", re.I)
# "the twelve noveltreatises" (the whole set, this treatise included)
TOTAL = re.compile(r"the (\w+) noveltreatises\b", re.I)
# a named, honest boundary (Prime Directive: not a stub, a declared absence)
UNRESOLVED = re.compile(r"\[MECHANISM NOT DERIVED")
# the Prime Directive's canonical template, not a live unresolved mechanism
UNRESOLVED_TEMPLATE = "I do not have the implementation for X. My uncertain idea is Y."


def fail(msg: str) -> "NoReturn":  # noqa: F821
    print(f"absolution_admission: FAIL — {msg}")
    sys.exit(1)


def carried_treatises() -> set[str]:
    """The roman numerals of the noveltreatises actually carried in docs/nt/."""
    romans: set[str] = set()
    if not CORPUS.is_dir():
        return romans
    for f in CORPUS.glob("NT-*.txt"):
        m = re.match(r"NT-([IVX]+)\.txt$", f.name)
        if m:
            romans.add(m.group(1))
    # NT-I-IV-protocol.md carries treatises I through IV in one file.
    if (CORPUS / "NT-I-IV-protocol.md").is_file():
        romans |= {"I", "II", "III", "IV"}
    return romans


def run_evidence(ev: dict, timeout: int = 120) -> tuple[bool, str]:
    """Re-run a recorded evidence command. True iff exit 0 and `expect` in output."""
    if not isinstance(ev, dict) or not ev.get("cmd"):
        return False, "no evidence command"
    parts = shlex.split(ev["cmd"])
    if parts and parts[0] in ("python", "python3"):
        parts[0] = sys.executable
    try:
        p = subprocess.run(parts, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"could not run: {e}"
    out = p.stdout + p.stderr
    ok = p.returncode == 0 and str(ev.get("expect", "")) in out
    last = out.strip().splitlines()[-1] if out.strip() else "(no output)"
    return ok, last


def check_count(text: str, n_carried: int) -> list[str]:
    """Every corpus-count claim must be true against the carried corpus.

    'the N preceding/prior noveltreatises' counts the treatises BEFORE this one:
    carried minus this one. 'the N noveltreatises' counts the whole set, this one
    included: carried. The defect class this catches: a treatise that says
    'twelve preceding' when only eleven precede it.
    """
    bad = []
    n_preceding = n_carried - 1  # carried, minus the treatise being admitted
    for m in PRECEDING.finditer(text):
        w = m.group(1).lower()
        if w in WORD and WORD[w] != n_preceding:
            bad.append(f"says 'the {w} preceding/prior noveltreatises' but {n_preceding} precede it")
    for m in TOTAL.finditer(text):
        w = m.group(1).lower()
        if w in WORD and WORD[w] != n_carried:
            bad.append(f"says 'the {w} noveltreatises' but {n_carried} are carried (the set)")
    return bad


def check_boundaries(text: str) -> list[str]:
    """A named unresolved mechanism must sit under an EXPOSABLE flag, not a RESOLVED one.

    The Prime Directive's canonical template (the rule definition) is not a live
    unresolved mechanism and is skipped; any OTHER declaration must be flagged.
    """
    bad = []
    for m in UNRESOLVED.finditer(text):
        tail = text[m.start():m.start() + 200]
        if UNRESOLVED_TEMPLATE in tail:
            continue  # the rule's own template, not a live boundary
        # the flag for the part is the nearest preceding "PART ... | <FLAGS>" heading
        head = text[:m.start()]
        last = head.rfind("PART ")
        flags = text[last:head.find("\n", last)] if last != -1 else ""
        if "EXPOSABLE" not in flags:
            bad.append(f"unresolved mechanism at offset {m.start()} is not flagged EXPOSABLE")
    return bad


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roman", default="XII", help="the roman numeral of the treatise to admit")
    ap.add_argument("--claims", default="proof/nt_xii_claims.json")
    ap.add_argument("--recon", default="proof/nt_xii_reconciliation.json")
    a = ap.parse_args(argv)

    # 1. the treatise must be CARRIED in the corpus, not merely present at the root.
    carried_path = CORPUS / f"NT-{a.roman}.txt"
    if not carried_path.is_file():
        fail(f"the treatise is not carried at docs/nt/NT-{a.roman}.txt "
             f"(a treatise that is cited but not carried is a note, not a law)")
    text = carried_path.read_text(encoding="utf-8")

    # 2. the claims ledger must pass SAVF with 0 problems, and no witness downgraded.
    claims_path = ROOT / a.claims
    if not claims_path.is_file():
        fail(f"claims ledger missing: {a.claims}")
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT))
    import savf  # noqa: E402  (the one ledger implementation; re-used, not copied)

    rows, bad = savf.ledger(claims, run=True)
    downgraded = [r["id"] for r in rows
                  if r["kind"] == "W" and r.get("effective") != "W"]
    if bad:
        fails = [r for r in rows if r["status"] in ("invalid", "failed", "unsupported")]
        for r in fails[:20]:
            print(f"  [{r['status']}] {r['id']}: {r['note']}")
        fail(f"{bad} ledger problem(s) (a witness failed, or a derivation is unsupported)")
    if downgraded:
        fail("witness(es) silently downgraded to a bare declaration (no external referent): "
             + ", ".join(downgraded))

    # 3. every contradiction resolved exactly once; no orphans.
    contradictions = {c["id"] for c in claims if c.get("kind") == "C"}
    recon_path = ROOT / a.recon
    if contradictions and not recon_path.is_file():
        fail(f"{len(contradictions)} contradiction(s) but no reconciliation ledger ({a.recon})")
    recon = json.loads(recon_path.read_text(encoding="utf-8")) if recon_path.is_file() else []
    ids = [r.get("id") for r in recon]
    if len(ids) != len(set(ids)):
        fail("the reconciliation ledger names the same contradiction twice")
    resolved = set(ids)
    unresolved = contradictions - resolved
    orphan = resolved - contradictions
    if unresolved:
        fail("unresolved contradiction(s): " + ", ".join(sorted(unresolved)))
    if orphan:
        fail("orphaned resolution(s) (no matching contradiction): " + ", ".join(sorted(orphan)))

    # 4. every resolution re-runs green.
    print(f"absolution_admission: {len(claims)} claims, {len(contradictions)} contradiction(s), "
          f"{len(recon)} resolution(s)")
    bad_r = 0
    for r in sorted(recon, key=lambda x: x.get("id", "")):
        ok, note = run_evidence(r.get("evidence") or {})
        print(f"  [{'PASS' if ok else 'FAIL'}] {r.get('id',''):28s} "
              f"{r.get('resolved_as',''):10s} {note}")
        bad_r += not ok
    if bad_r:
        fail(f"{bad_r} resolution(s) did not re-run green")

    # 5. the treatise's own corpus count must be true.
    n_carried = len(carried_treatises())
    count_bad = check_count(text, n_carried)
    if count_bad:
        for b in count_bad:
            print(f"  [FAIL] corpus count: {b}")
        fail(f"{len(count_bad)} corpus-count contradiction(s) (the treatise is not truthful "
             f"about how many treatises it stands on)")

    # 6. no unresolved mechanism smuggled as RESOLVED.
    bnd_bad = check_boundaries(text)
    if bnd_bad:
        for b in bnd_bad:
            print(f"  [FAIL] boundary: {b}")
        fail(f"{len(bnd_bad)} unresolved mechanism(s) not flagged EXPOSABLE")

    print(f"absolution_admission: PASS — NT-{a.roman} admitted. "
          f"{len(claims)} claims witnessed/derived, {len(recon)} contradiction(s) resolved, "
          f"corpus count true ({n_carried} carried; {n_carried - 1} precede this one), "
          f"no smuggled mechanism.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
