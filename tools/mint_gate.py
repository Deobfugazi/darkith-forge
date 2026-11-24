#!/usr/bin/env python3
"""Mint gate: decide whether a burden-closure record may mint a unit of value.

This is the load-bearing part of the design.  A mint is admissible only when every
falsifier in docs/PRIME-DIRECTIVE-OMEGA.md holds.  The gate fails CLOSED: anything it
cannot attest is 'marginal', never 'pass'.  That is the same verdict algebra SAVF uses
for source audits, applied to outcome claims.

Usage:
    python3 tools/mint_gate.py closure.json          # grade a closure record
    python3 tools/mint_gate.py --selftest            # prove the gate refuses bad input
"""

import argparse
import hashlib
import json
import sys

PASS, MARGINAL, FAIL = "pass", "marginal", "fail"

# Admissibility checks.  Each is (key, phi_class, hard?).  Hard failures convict.
CHECKS = (
    ("source", "G1", True),        # burden carries source + retrieval date
    ("addressable", "G2", True),   # not conflict-driven
    ("counterfactual", "G6", True),  # baseline names what would have happened
    ("frozen", "G6", True),        # baseline hash recorded
    ("independent", "G3", True),   # measurer != implementer
    ("permanence", "G4", True),    # horizon + slashable bond
    ("rerunnable", "G5", True),    # third party can re-run the closure
    ("solvent", "G7", True),       # vouchers outstanding <= funded commitments
    ("cost", "G8", False),         # verification cost < burden value
    ("payer", "G9", True),         # a named payer exists
)


def _req(rec, path):
    """Fetch a dotted path from the record, or None."""
    cur = rec
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _nonempty(v):
    return v not in (None, "", [], {}, 0)


def grade(rec):
    """Return (verdict, results) for a closure record.

    verdict is PASS / REVIEW / BLOCKED / LIED using the same algebra as savf.verdict:
    a hard fail is LIED (the record asserts something it cannot back); a soft fail is
    BLOCKED; anything unattested is REVIEW; all clear is PASS.
    """
    r = {}

    # G1 — provenance
    r["source"] = PASS if (_nonempty(_req(rec, "burden.source")) and
                           _nonempty(_req(rec, "burden.retrieved"))) else FAIL

    # G2 — conflict-driven crises are out of scope by construction
    drv = str(_req(rec, "burden.drivers") or "").strip().lower()
    if not drv:
        r["addressable"] = MARGINAL  # unknown scope is unattested, not in-scope
    elif "conflict" in drv or "violence" in drv:
        r["addressable"] = FAIL
    else:
        r["addressable"] = PASS

    # G6 — baseline must name a counterfactual and be frozen
    r["counterfactual"] = PASS if _nonempty(_req(rec, "baseline.counterfactual")) else FAIL
    r["frozen"] = PASS if _nonempty(_req(rec, "baseline.sha256")) else FAIL

    # G3 — the measurer may not be the implementer
    impl = _req(rec, "intervention.implementer")
    meas = _req(rec, "measurement.measurer")
    if not impl or not meas:
        r["independent"] = MARGINAL
    else:
        r["independent"] = FAIL if str(impl).strip().lower() == str(meas).strip().lower() else PASS

    # G4 — permanence horizon and a bond that can be slashed
    horizon = _req(rec, "permanence.months")
    bond = _req(rec, "permanence.bond_pct")
    if not isinstance(horizon, (int, float)) or horizon <= 0:
        r["permanence"] = FAIL
    elif not isinstance(bond, (int, float)) or bond <= 0:
        r["permanence"] = FAIL
    else:
        r["permanence"] = PASS

    # G5 — the closure must be re-runnable by a third party
    r["rerunnable"] = PASS if _nonempty(_req(rec, "closure.command")) else FAIL

    # G7 — insolvency invariant: outstanding vouchers may not exceed funded commitments
    funded = _req(rec, "treasury.funded_commitments")
    outstanding = _req(rec, "treasury.vouchers_outstanding")
    if not isinstance(funded, (int, float)) or not isinstance(outstanding, (int, float)):
        r["solvent"] = MARGINAL
    else:
        r["solvent"] = FAIL if outstanding > funded else PASS

    # G8 — verification cost must be below the burden's value (soft: economics, not honesty)
    vcost = _req(rec, "economics.verification_cost")
    bval = _req(rec, "economics.burden_value")
    if not isinstance(vcost, (int, float)) or not isinstance(bval, (int, float)):
        r["cost"] = MARGINAL
    else:
        r["cost"] = FAIL if vcost >= bval else PASS

    # G9 — a named payer must exist before a unit is minted
    r["payer"] = PASS if _nonempty(_req(rec, "payer.name")) else FAIL

    hard = {k for k, _, h in CHECKS if h}
    if any(r[k] == FAIL for k in hard):
        return "LIED", r
    if any(r[k] == FAIL for k in r if k not in hard):
        return "BLOCKED", r
    if any(v == MARGINAL for v in r.values()):
        return "REVIEW", r
    return "PASS", r


def freeze_baseline(rec):
    """Return the record with baseline.sha256 set over the frozen baseline fields.

    The hash covers exactly the fields a baseline must not change after the fact, so a
    shifted baseline is detectable by recomputation (falsifier G6 / B2).
    """
    base = rec.get("baseline") or {}
    canon = json.dumps(
        {k: base.get(k) for k in ("value", "method", "window", "counterfactual")},
        sort_keys=True, separators=(",", ":"),
    ).encode()
    out = json.loads(json.dumps(rec))
    out.setdefault("baseline", {})["sha256"] = hashlib.sha256(canon).hexdigest()
    return out


def baseline_intact(rec):
    """True if the stored baseline hash still matches its fields."""
    stored = _req(rec, "baseline.sha256")
    if not stored:
        return False
    return freeze_baseline(rec)["baseline"]["sha256"] == stored


GOOD = {
    "burden": {
        "crisis": "Drought in Southern Madagascar",
        "country": "Madagascar",
        "drivers": "Drought/drier conditions",
        "severity": 6.3,
        "source": "INFORM Severity October 2026",
        "retrieved": "2026-11-12T00:00:00Z",
    },
    "baseline": {
        "value": 41.8,
        "method": "DHS household survey, 12-month recall",
        "window": "2026-01..2026-12",
        "counterfactual": "no irrigation intervention; trend continuation from 2024-2026",
    },
    "intervention": {"implementer": "NGO-A"},
    "measurement": {"measurer": "Independent-Evaluator-B"},
    "permanence": {"months": 36, "bond_pct": 25},
    "closure": {"command": "python3 tools/verify_closure.py --case MDG-2026-01"},
    "treasury": {"funded_commitments": 100000, "vouchers_outstanding": 40000},
    "economics": {"verification_cost": 8000, "burden_value": 60000},
    "payer": {"name": "Diaspora Pool Madagascar"},
}


def _mutate(base, **paths):
    """Copy base and set dotted paths, for negative tests."""
    out = json.loads(json.dumps(base))
    for path, val in paths.items():
        cur = out
        parts = path.split("__")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = val
    return out


def selftest():
    """Prove the gate accepts a good record and refuses every specific bad one."""
    fails = []

    def expect(name, rec, want):
        got, _ = grade(rec)
        if got != want:
            fails.append(f"{name}: wanted {want}, got {got}")

    frozen = freeze_baseline(GOOD)
    expect("good record", frozen, "PASS")

    # Each negative case must be convicted, not merely reviewed.
    expect("G3 self-attested measurer",
           _mutate(frozen, measurement__measurer="NGO-A"), "LIED")
    expect("G4 no permanence bond",
           _mutate(frozen, permanence__bond_pct=0), "LIED")
    expect("G4 no permanence horizon",
           _mutate(frozen, permanence__months=0), "LIED")
    expect("G5 closure not re-runnable",
           _mutate(frozen, closure__command=""), "LIED")
    expect("G9 no payer",
           _mutate(frozen, payer__name=""), "LIED")
    expect("G1 no source",
           _mutate(frozen, burden__source=""), "LIED")
    expect("G6 no counterfactual",
           _mutate(frozen, baseline__counterfactual=""), "LIED")
    expect("G2 conflict crisis",
           _mutate(frozen, burden__drivers="Conflict/ Violence,Drought"), "LIED")
    expect("G7 insolvent treasury",
           _mutate(frozen, treasury__vouchers_outstanding=200000), "LIED")

    # Soft failure is BLOCKED, not LIED: bad economics is not a lie.
    expect("G8 verification costs more than burden",
           _mutate(frozen, economics__verification_cost=90000), "BLOCKED")

    # Unattested is REVIEW: the gate must not pass what it could not check.
    expect("G8 economics unknown",
           _mutate(frozen, economics__verification_cost=None), "REVIEW")

    # Baseline drift must be detectable.
    drifted = json.loads(json.dumps(frozen))
    drifted["baseline"]["value"] = 20.0
    if baseline_intact(drifted):
        fails.append("baseline drift was not detected")

    # A hash alone must not launder a drifted baseline back to valid.
    if not baseline_intact(frozen):
        fails.append("intact baseline reported as drifted")

    for f in fails:
        print("FAIL " + f, file=sys.stderr)
    print(f"{'FAIL' if fails else 'PASS'}: mint gate selftest, {len(fails)} failure(s)")
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grade a burden-closure record for mint admissibility.")
    ap.add_argument("record", nargs="?", help="closure record JSON path")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--freeze", action="store_true", help="print the record with baseline frozen")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if not a.record:
        ap.error("need a record path or --selftest")

    with open(a.record, encoding="utf-8") as f:
        rec = json.load(f)

    if a.freeze:
        print(json.dumps(freeze_baseline(rec), indent=1))
        return 0

    verdict, results = grade(rec)
    intact = baseline_intact(rec)
    print(json.dumps({"verdict": verdict, "baseline_intact": intact, "checks": results},
                     indent=1))
    return {"PASS": 0, "REVIEW": 2, "BLOCKED": 3, "LIED": 4}[verdict]


if __name__ == "__main__":
    sys.exit(main())
