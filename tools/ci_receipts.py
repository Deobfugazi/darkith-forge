#!/usr/bin/env python3
"""ci_receipts.py — bind a CI run to the hash-chained ledger.

WHY
    CI prints PASS to a terminal and the terminal forgets. `nodal/ledger.py` already stores
    append-only, hash-chained, tamper-evident receipts, but nothing bound a CI run to it: the
    proof existed and the run never touched it. This is the join.

WHAT A RECEIPT CONTAINS
    One receipt per gate, in one lane per run. Each receipt carries the gate's NAME and the
    sha256 of the gate's source, so a receipt attests "this exact program, at these bytes,
    reported this verdict" — not "something called the gate passed once".

WHY IT CANNOT BE GAMED WITHOUT RE-RUNNING
    `input_hash` is the digest of the gate source concatenated with the digest of the tree
    under test. Changing the gate, or changing the tree, changes the hash, and the receipt no
    longer describes the code in front of you. Rewriting a receipt after the fact breaks the
    chain: `Ledger.verify_chain` rebuilds each receipt from its stored fields and compares the
    id, and the witness pointer is computed by the storage layer from its own head, so a
    forger must recompute every descendant in the lane and still cannot forge ancestry.

    This does not make the run honest — nothing can. It makes the run AUDITABLE: the receipt
    is evidence that a named program over named bytes returned a named verdict, and a claim
    without that evidence is a note (SPI-15).

USAGE
    python3 tools/ci_receipts.py --emit   # parse a CI log on stdin, append receipts
    python3 tools/ci_receipts.py --verify # verify every lane's chain
    python3 tools/ci_receipts.py --summary

Exit: 0 ok; 1 verification failed or an unparseable log; 3 nothing to do.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LEDGER_PATH = ROOT / "proof" / "ci_receipts.db"
LANE = "ci"

# `--- name: PASS` / `--- name: FAIL (exit 2)` / `--- name: SKIP (exit 3)`
_RESULT = re.compile(r"^---\s+(?P<name>.+?):\s+(?P<verdict>PASS|FAIL|SKIP)\b(?:.*?exit\s+(?P<rc>\d+))?")


def gate_source_hash(name: str) -> str:
    """Digest of the gate program itself, if it can be identified from the result line.

    The result line carries a human label, not a path, so this searches for a tool whose
    basename or stem appears in the label. When nothing matches, the label alone is hashed —
    still deterministic, still bound, just coarser. Returning a constant here would make every
    receipt for that label identical, which would defeat the point.
    """
    h = hashlib.sha256()
    hit = None
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    for cand in sorted((ROOT / "tools").rglob("*")):
        if not cand.is_file() or cand.suffix not in (".py", ".sh", ".js", ".mjs"):
            continue
        stem = re.sub(r"[^a-z0-9]+", "_", cand.stem.lower()).strip("_")
        if stem and stem in slug:
            hit = cand
            break
    if hit is not None:
        h.update(hit.read_bytes())
        h.update(b"\0")
        h.update(str(hit.relative_to(ROOT)).encode())
    h.update(name.encode())
    return h.hexdigest()


def tree_hash() -> str:
    """Digest over the tracked source tree, so a receipt describes the code it judged."""
    h = hashlib.sha256()
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in (".git", "__pycache__", "node_modules", ".agent_tmp") for part in rel.parts):
            continue
        if p.suffix in (".db", ".pyc", ".apk"):
            continue
        h.update(str(rel).encode())
        h.update(b"\0")
        try:
            h.update(hashlib.sha256(p.read_bytes()).digest())
        except OSError:
            h.update(b"<unreadable>")
    return h.hexdigest()


def parse_log(text: str) -> list[tuple[str, str, int]]:
    out: list[tuple[str, str, int]] = []
    for line in text.splitlines():
        m = _RESULT.match(line.strip())
        if m:
            rc = int(m.group("rc")) if m.group("rc") else {"PASS": 0, "FAIL": 1, "SKIP": 3}[m.group("verdict")]
            out.append((m.group("name").strip(), m.group("verdict"), rc))
    return out


def emit(text: str) -> int:
    from nodal import GENESIS_WITNESS, Ledger, Receipt, Verdict  # noqa: F401

    results = parse_log(text)
    if not results:
        print("ci_receipts: SKIP — no gate results found on stdin")
        return 3

    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(str(LEDGER_PATH))
    th = tree_hash()
    epoch = int(os.environ.get("DARKITH_EPOCH", "0"))
    seq0 = ledger.count()
    accepted = rejected = 0
    now = time.time_ns()

    for i, (name, verdict, rc) in enumerate(results):
        v = {"PASS": Verdict.ALLOW, "FAIL": Verdict.DENY, "SKIP": Verdict.OBSERVE}[verdict]
        draft = Receipt(
            engine_id="ci_receipts",
            boundary="ci.sh",
            epoch=epoch,
            seq=seq0 + i,
            lane=LANE,
            input_hash=hashlib.sha256((gate_source_hash(name) + th).encode()).hexdigest(),
            verdict=v,
            clause=f"{name} -> {verdict} (exit {rc})",
            policy_version="v1",
            t_wall_ns=now,
        )
        r = ledger.append(draft)
        if r.accepted:
            accepted += 1
        else:
            rejected += 1
            print(f"ci_receipts: rejected {name}: {r.reason}")
    print(f"ci_receipts: {accepted} receipt(s) appended, {rejected} rejected; "
          f"lane {LANE!r} now {len(ledger.lane_receipts(LANE))} long; tree {th[:16]}")
    return 0 if rejected == 0 else 1


def verify() -> int:
    from nodal import Ledger

    if not LEDGER_PATH.is_file():
        print("ci_receipts: SKIP — no ledger yet (run --emit)")
        return 3
    ledger = Ledger(str(LEDGER_PATH))
    problems = ledger.verify_all()
    lanes = ledger.lanes()
    if problems:
        print(f"ci_receipts: FAIL — {len(problems)} chain problem(s) across {len(lanes)} lane(s)")
        for p in problems[:10]:
            print("  " + str(p))
        return 1
    print(f"ci_receipts: PASS — {len(lanes)} lane(s), {ledger.count()} receipt(s), "
          f"every chain recomputes to its stored id")
    return 0


def summary() -> int:
    if not LEDGER_PATH.is_file():
        print("ci_receipts: SKIP — no ledger yet")
        return 3
    con = sqlite3.connect(str(LEDGER_PATH))
    rows = con.execute(
        "SELECT clause, receipt_id, witness FROM receipts ORDER BY seq DESC LIMIT 8"
    ).fetchall()
    total = con.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
    print(f"ci_receipts: {total} receipt(s); most recent:")
    for clause, rid, wit in rows:
        print(f"  {rid[:12]}  witness {wit[:12]}  {clause}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="read a CI log on stdin")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if a.verify:
        return verify()
    if a.summary:
        return summary()
    if a.emit:
        return emit(sys.stdin.read())
    ap.print_help()
    return 2


def selftest() -> int:
    """Both trials: an honest log is accepted, a forged ledger is caught."""
    import tempfile

    fails: list[str] = []

    def ok(cond, msg):
        if not cond:
            fails.append(msg)

    log = "=== a ===\n--- alpha gate: PASS\n=== b ===\n--- beta gate: FAIL (exit 1)\n--- gamma: SKIP (exit 3)\n"
    parsed = parse_log(log)
    ok(len(parsed) == 3, f"parsed {len(parsed)} of 3 results")
    ok(parsed[0][1] == "PASS" and parsed[1][1] == "FAIL" and parsed[2][1] == "SKIP", "verdict parse")
    ok(parsed[2][2] == 3, "skip exit code")
    ok(parse_log("no results here\n") == [], "noise parsed as results")

    from nodal import GENESIS_WITNESS, Ledger, Receipt, Verdict

    with tempfile.TemporaryDirectory() as td:
        led = Ledger(str(Path(td) / "t.db"))
        for i, v in enumerate((Verdict.ALLOW, Verdict.DENY, Verdict.OBSERVE)):
            r = led.append(Receipt(engine_id="t", boundary="b", epoch=0, seq=i, lane="L",
                                   input_hash="0" * 64, verdict=v, clause=f"c{i}"))
            ok(r.accepted, f"append {i} rejected: {r.reason}")
        ok(led.verify_chain("L") == [], "clean chain reported problems")
        ok(led.lane_receipts("L")[0]["witness"] == GENESIS_WITNESS, "first receipt not genesis-anchored")

        # FORGERY TRIAL: mutate a stored field out of band. The trigger must refuse it.
        try:
            led.conn.execute("UPDATE receipts SET clause='forged' WHERE seq=1")
            led.conn.commit()
            fails.append("out-of-band UPDATE committed — storage is not immutable")
        except sqlite3.Error:
            led.conn.rollback()

        # FORGERY TRIAL: delete a receipt. Truncation must be detectable or refused.
        try:
            led.conn.execute("DELETE FROM receipts WHERE seq=2")
            led.conn.commit()
            fails.append("out-of-band DELETE committed — history is truncatable")
        except sqlite3.Error:
            led.conn.rollback()

        ok(led.verify_chain("L") == [], "chain broken by refused forgery")

    if fails:
        print(f"ci_receipts selftest: FAIL — {len(fails)} problem(s)")
        for f in fails:
            print("  " + f)
        return 1
    print("ci_receipts selftest: PASS — log parsing, genesis anchoring, and both "
          "out-of-band forgery trials (UPDATE and DELETE refused at the storage layer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
