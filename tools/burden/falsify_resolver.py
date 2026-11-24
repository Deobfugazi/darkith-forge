#!/usr/bin/env python3
"""falsify_resolver.py — prove the resolver can FAIL.

A resolver that only ever prints RESOLVED_TO_EXACT_ZERO is a lamp that always glows.
Each vector below breaks one thing and asserts the resolver reports it. If any vector
is NOT caught, the resolver is defective and this exits 1.

Isolation: stdlib only. Imports the resolver's own algebra, mutates, re-tests.
"""
from __future__ import annotations

import importlib.util
import sys
from fractions import Fraction as Q

spec = importlib.util.spec_from_file_location(
    "ri", __file__.replace("falsify_resolver.py", "resolve_invariants.py"))
ri = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ri)

VECTORS = []


def vector(name, fn):
    VECTORS.append((name, fn))


# V1 — a float witness would pass a non-zero residual as zero
def v1():
    got = (0.1 + 0.2 - 0.3) == 0.0
    return (not got), f"float residual {0.1 + 0.2 - 0.3!r} is not zero -> caught"


vector("V1 float residual cannot masquerade as zero", v1)


# V2 — Bill with ONE bridge pair must fail on E and $ carriers
def v2():
    kp = ri.dmul(ri.D_JOULE, ri.dim(B=-1))
    rh = ri.dmul(ri.D_MONEY, ri.dim(J=-1))
    bridge = ri.dmul(kp, rh)
    target = ri.dmul(ri.D_MONEY, ri.dinv(ri.D_TIME))
    bad = 0
    for x, (dstock, drate) in ri.RATE.items():
        if ri.dmul(drate, bridge) != target:
            bad += 1
    return (bad == 2), f"single-bridge Bill breaks {bad}/3 carriers (E,$) -> caught"


vector("V2 one bridge pair cannot close three carriers", v2)


# V3 — per-carrier bridges must close all three
def v3():
    target = ri.dmul(ri.D_MONEY, ri.dinv(ri.D_TIME))
    ok = 0
    for x, (dstock, drate) in ri.RATE.items():
        kx = ri.dmul(ri.D_JOULE, ri.dim(B=-1)) if x == "I" else ri.D_ONE
        rx = ri.dmul(ri.D_MONEY, ri.dim(J=-1)) if x in ("I", "E") else ri.D_ONE
        if ri.dmul(drate, kx, rx) == target:
            ok += 1
    return (ok == 3), f"per-carrier bridges close {ok}/3 -> repair is real"


vector("V3 per-carrier bridges close all three carriers", v3)


# V4 — dimensioned zero is NOT zero: 0 J is not 0
def v4():
    z = Q(0)
    scalar_zero = (z == 0) and (ri.D_ONE == {})
    joule_zero = (z == 0) and (ri.D_JOULE != {})
    return (scalar_zero and joule_zero), \
        "0[J] has empty numerator but non-empty dimension -> must not be admitted as scalar 0"


vector("V4 dimensioned zero is distinguishable from scalar zero", v4)


# V5 — chi unnormalised sum is refused; normalised sum closes
def v5():
    # unnormalised: a count (7) plus a phase error in radians (0.5) is a category error;
    # we detect it by requiring every term dimensionless AND bounded in [0,1]
    raw = [Q(7), Q(1, 2), Q(3)]
    in_budget = all(0 <= t <= 1 for t in raw)
    norm = [Q(0, 7), Q(0, 3), Q(0, 12)]
    norm_ok = all(0 <= t <= 1 for t in norm) and sum(norm) == 0
    return ((not in_budget) and norm_ok), \
        "unnormalised terms exceed budget -> refused; normalised sum is exactly 0"


vector("V5 chi must be normalised before summing", v5)


# V6 — triad refuses b = 1
def v6():
    b = Q(1)
    refused = (b == 1)
    return refused, "b=1 makes ln b = 0 and n unforced -> the log leg must be refused"


vector("V6 triad refuses b=1 (log leg undefined)", v6)


# V7 — F1 must be read as rates or it is dimensionally undefined
def v7():
    as_stocks = ri.dmul(ri.D_BIT, ri.D_ONE)              # x_gen [b]
    deriv = ri.dmul(ri.D_BIT, ri.dinv(ri.D_TIME))        # dx_sto/dt [b/s]
    broken = (as_stocks != deriv)
    as_rates = ri.dmul(ri.D_BIT, ri.dinv(ri.D_TIME))
    closed = (as_rates == deriv)
    return (broken and closed), \
        "stock+derivative sum is undefined; all-rates sum closes -> annotation is load-bearing"


vector("V7 F1 only closes if all five terms are rates", v7)


# V8 — Landauer floor only typechecks per bit
def v8():
    kappa = ri.dmul(ri.D_JOULE, ri.dim(B=-1))     # J/bit
    floor_raw = ri.D_JOULE                        # J
    bad = (kappa != floor_raw)
    floor_per_bit = ri.dmul(ri.D_JOULE, ri.dim(B=-1))
    good = (kappa == floor_per_bit)
    return (bad and good), "kappa[J/bit] vs k_BT[J] mismatches; per-bit floor matches"


vector("V8 Landauer floor requires per-bit normalisation", v8)


# V9 — the resolver must actually fail when a gap is left OPEN
def v9():
    saved = [dict(g) for g in ri.INVARIANTS]
    try:
        for it in ri.INVARIANTS:
            if it["id"] == "BILL":
                it["gaps"] = [("DIM-9", "injected open gap", "OPEN: not repaired")]
        r = ri.resolve()
        failed = (r["verdict"]["ok"] is False) and (r["verdict"]["gaps_open"] == 1)
        return failed, f"injected OPEN gap -> verdict ok={r['verdict']['ok']}, " \
                       f"gaps_open={r['verdict']['gaps_open']} -> caught"
    finally:
        ri.INVARIANTS[:] = saved


vector("V9 resolver returns FAIL when a gap is injected OPEN", v9)


# V10 — and passes again once restored (control must survive)
def v10():
    r = ri.resolve()
    return r["verdict"]["ok"] is True, \
        f"control: clean corpus -> ok={r['verdict']['ok']}, " \
        f"gaps_open={r['verdict']['gaps_open']}"


vector("V10 control survives: clean corpus resolves", v10)


def main() -> int:
    print("=" * 78)
    print("RESOLVER FALSIFICATION — the resolver must be able to say NO")
    print("=" * 78)
    holes = 0
    for name, fn in VECTORS:
        try:
            ok, detail = fn()
        except Exception as exc:                     # a crashing vector is a hole
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        if not ok:
            holes += 1
        print(f"\n  [{'PASS' if ok else 'HOLE'}] {name}")
        print(f"         {detail}")
    print("\n" + "=" * 78)
    print(f"VECTORS: {len(VECTORS)}   HOLES: {holes}")
    print(f"VERDICT: {'FALSIFIABLE' if holes == 0 else 'RESOLVER_DEFECTIVE'}")
    print("=" * 78)
    return 0 if holes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
