#!/usr/bin/env python3
"""stall_gate.py — enforces NEVER #17 (NO STALLED DEFICIENCY) and MUST #19 (DARKITH.md §23/§30).

The law: NEVER leave a named deficiency open across two or more deliveries. Every open entry
is either CLOSED (implemented, compiled, verified in the artifact) or DESCoped (formally, with
the reason written down). Silence is not a third option.

A ledger entry that is neither closed nor descoped, delivery after delivery, is a STALL — and
a stall is worse than a lie, because it looks like diligence (W-046).

Mechanics:
  - DEFICITS.json is the machine-readable ledger; each entry carries `named_in` (the
    versionCode of the delivery that first named it) and a status of closed|descoped|open.
  - The current delivery is the manifest's versionCode.
  - A `closed` entry must carry `evidence`; a `descoped` entry must carry `reason`.
  - An `open` entry is a stall the moment `current - named_in >= 2` (named two or more
    deliveries ago and still not resolved). An entry with no `named_in` is an unversioned
    stall and fails outright.

Fails if the ledger is absent, malformed, carries a closed/descoped entry with no
evidence/reason, or leaves any entry open across two or more deliveries.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "DEFICITS.json"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"
VALID = {"closed", "descoped", "open"}


def current_versioncode() -> int | None:
    if not MANIFEST.is_file():
        return None
    m = re.search(r'android:versionCode="(\d+)"', MANIFEST.read_text(encoding="utf-8"))
    return int(m.group(1)) if m else None


def main() -> int:
    if not LEDGER.is_file():
        print("stall_gate: FAIL — no DEFICITS.json (NEVER #17 has no ledger to enforce)")
        return 1
    try:
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"stall_gate: FAIL — DEFICITS.json is not valid JSON: {e}")
        return 1

    cur = current_versioncode()
    entries = data.get("deficits")
    if not isinstance(entries, list) or not entries:
        print("stall_gate: FAIL — DEFICITS.json carries no deficits")
        return 1

    fails, stalls = [], []
    for e in entries:
        did = e.get("id", "?")
        st = e.get("status")
        if st not in VALID:
            fails.append(f"{did}: status '{st}' is not one of {sorted(VALID)}")
            continue
        if st == "closed" and not e.get("evidence"):
            fails.append(f"{did}: closed with no evidence (MUST #20: prove it in the artifact)")
        if st == "descoped" and not e.get("reason"):
            fails.append(f"{did}: descoped with no reason written down")
        named = e.get("named_in")
        if st == "open":
            if not isinstance(named, int):
                fails.append(f"{did}: open with no `named_in` version (unversioned stall)")
            elif cur is not None and cur - named >= 2:
                stalls.append(f"{did}: open since versionCode {named}, now {cur} "
                              f"({cur - named} deliveries) — a stall, not diligence")

    if fails or stalls:
        print(f"stall_gate: FAIL — {len(fails) + len(stalls)} problem(s):")
        for f in fails + stalls:
            print("  " + f)
        return 1

    closed = sum(1 for e in entries if e["status"] == "closed")
    desc = sum(1 for e in entries if e["status"] == "descoped")
    op = sum(1 for e in entries if e["status"] == "open")
    print(f"stall_gate: PASS — {len(entries)} deficit(s): {closed} closed, {desc} descoped, "
          f"{op} open (none stalled); delivery versionCode={cur}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
