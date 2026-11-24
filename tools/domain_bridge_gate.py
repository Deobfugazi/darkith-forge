#!/usr/bin/env python3
"""domain_bridge_gate.py — NEVER #30 / MUST #49. No cross-domain transplant without a bridge.

Every carrier in a composition must close to the target dimension INDEPENDENTLY. Not the sum.
A composition whose total happens to close while one term does not is a defect, and it is how
a Bill appears to balance while summing joules into dollars.

Reads the carrier table from docs/COMPOSITION.json:
  { "target": {"M":1,"T":-1},
    "carriers": [ {"x":"I","R":{"B":1,"T":-1},"kappa":{"J":1,"B":-1},"rho":{"M":1,"J":-1}},
                  ... ] }

Exit 0 = every carrier closes. Exit 1 = a carrier does not. Exit 3 = file absent.
"""
from __future__ import annotations

import json
import sys
import pathlib

SPEC = pathlib.Path("docs/COMPOSITION.json")


def mul(*ds: dict) -> dict:
    r: dict = {}
    for d in ds:
        for k, v in d.items():
            r[k] = r.get(k, 0) + v
            if r[k] == 0:
                del r[k]
    return r


def evaluate(spec: dict) -> tuple[list[dict], bool]:
    target = spec["target"]
    rows = []
    for c in spec["carriers"]:
        prod = mul(c["R"], c["kappa"], c["rho"])
        rows.append({"x": c["x"], "product": prod, "closes": prod == target})
    return rows, all(r["closes"] for r in rows)


def run() -> int:
    if not SPEC.exists():
        print("DOMAIN_BRIDGE_GATE: SKIP spec_absent (a skip is never a pass, SPI-31)")
        return 3
    spec = json.loads(SPEC.read_text())
    rows, ok = evaluate(spec)
    print("=" * 78)
    print("DOMAIN BRIDGE GATE — every carrier closes to the target independently")
    print("=" * 78)
    print(f"target : {spec['target']}")
    for r in rows:
        print(f"  x={r['x']:3s}  product={r['product']}  "
              f"{'CLOSED' if r['closes'] else 'BROKEN'}")
    print(f"\ncarriers closed: {sum(1 for r in rows if r['closes'])}/{len(rows)}")
    print("\n" + "=" * 78)
    print(f"VERDICT: {'ALL_CARRIERS_CLOSED' if ok else 'CARRIER_BROKEN'}")
    print("=" * 78)
    return 0 if ok else 1


def selftest() -> int:
    target = {"M": 1, "T": -1}
    single_bridge = {"target": target, "carriers": [
        {"x": "I", "R": {"B": 1, "T": -1}, "kappa": {"J": 1, "B": -1}, "rho": {"M": 1, "J": -1}},
        {"x": "E", "R": {"J": 1, "T": -1}, "kappa": {"J": 1, "B": -1}, "rho": {"M": 1, "J": -1}},
        {"x": "$", "R": {"M": 1, "T": -1}, "kappa": {"J": 1, "B": -1}, "rho": {"M": 1, "J": -1}},
    ]}
    per_carrier = {"target": target, "carriers": [
        {"x": "I", "R": {"B": 1, "T": -1}, "kappa": {"J": 1, "B": -1}, "rho": {"M": 1, "J": -1}},
        {"x": "E", "R": {"J": 1, "T": -1}, "kappa": {}, "rho": {"M": 1, "J": -1}},
        {"x": "$", "R": {"M": 1, "T": -1}, "kappa": {}, "rho": {}},
    ]}
    rows_s, ok_s = evaluate(single_bridge)
    rows_p, ok_p = evaluate(per_carrier)
    results = [
        ("fires on single-bridge composition",
         not ok_s and sum(1 for r in rows_s if not r["closes"]) == 2,
         f"broken={[r['x'] for r in rows_s if not r['closes']]}"),
        ("silent on per-carrier composition", ok_p, f"closed={[r['x'] for r in rows_p if r['closes']]}"),
    ]
    print("=" * 78)
    print("DOMAIN BRIDGE GATE — SELFTEST")
    print("=" * 78)
    holes = 0
    for name, ok, detail in results:
        if not ok:
            holes += 1
        print(f"  [{'PASS' if ok else 'HOLE'}] {name}  {detail}")
    print(f"\nSELFTEST: {'PASS' if holes == 0 else 'FAIL'} ({holes} hole(s))")
    return 0 if holes == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
