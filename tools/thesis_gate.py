#!/usr/bin/env python3
"""thesis_gate.py — NEVER #31 / MUST #50. No apparatus in place of the thesis.

The machine that proves the claim is not the claim. This gate counts THESIS ADVANCE, not
artifact count: how many of the Operator's stated claims have a delivered document behind
them, and which are still unwritten. A delivery that advances none is apparatus and cannot be
reported as a thesis delivery.

Source of truth: docs/THESIS.md  (the objective, stated plainly)
Claim map:      docs/CLAIM-MAP.json
  { "claims": [ {"id":"T1", "claim":"...", "docs":["docs/X.html"], "status":"advanced"} ] }

Exit 0 = at least one claim advanced and no claim claims a doc that is absent.
Exit 1 = a claim cites an absent document, or zero claims are advanced.
Exit 3 = thesis or map absent.
"""
from __future__ import annotations

import json
import re
import sys
import pathlib

THESIS = pathlib.Path("docs/THESIS.md")
MAP = pathlib.Path("docs/CLAIM-MAP.json")
# The objective is declared in bold, not quoted. The Operator's stated objective is
# recorded as a paraphrase; his frustrated moments are not evidence and are not archived.
DECLARED = re.compile(r"^\*\*The upliftment of friction", re.M)


def load() -> tuple[str, dict]:
    return THESIS.read_text(), json.loads(MAP.read_text())


def evaluate(thesis_text: str, claim_map: dict) -> tuple[list[str], list[dict], bool]:
    problems: list[str] = []
    claims = claim_map.get("claims", [])
    if not DECLARED.search(thesis_text):
        problems.append("THESIS_UNDECLARED — the objective is not declared in docs/THESIS.md")
    for c in claims:
        for d in c.get("docs", []):
            if not pathlib.Path(d).exists():
                problems.append(f"ABSENT_DOC {c['id']} -> {d}")
        if c.get("status") == "advanced" and not c.get("docs"):
            problems.append(f"ADVANCED_WITHOUT_DOC {c['id']}")
    advanced = [c for c in claims if c.get("status") == "advanced"]
    if not advanced:
        problems.append("ZERO_THESIS_ADVANCE — every claim is unwritten; this is apparatus")
    return problems, claims, bool(advanced)


def run() -> int:
    missing = [str(p) for p in (THESIS, MAP) if not p.exists()]
    if missing:
        print(f"THESIS_GATE: SKIP {missing} (a skip is never a pass, SPI-31)")
        return 3
    thesis_text, claim_map = load()
    problems, claims, _ = evaluate(thesis_text, claim_map)
    adv = [c for c in claims if c.get("status") == "advanced"]
    unw = [c for c in claims if c.get("status") != "advanced"]

    print("=" * 78)
    print("THESIS GATE — apparatus is not progress")
    print("=" * 78)
    d = DECLARED.search(thesis_text)
    print(f"objective declared: {'YES' if d else 'ABSENT'}")
    print(f"claims total     : {len(claims)}")
    print(f"claims advanced  : {len(adv)}")
    print(f"claims unwritten : {len(unw)}")
    if unw:
        print("\n-- UNWRITTEN, named (this is the real backlog) " + "-" * 30)
        for c in unw:
            print(f"  [UNWRITTEN] {c['id']}: {c['claim'][:70]}")
    for p in problems:
        print(f"  [DEFECT] {p}")
    ok = not problems
    print("\n" + "=" * 78)
    print(f"VERDICT: {'THESIS_ADVANCED' if ok else 'APPARATUS_ONLY'}")
    print("=" * 78)
    return 0 if ok else 1


def selftest() -> int:
    import tempfile
    good_thesis = "# THESIS\n\n**The upliftment of friction, miscommunication first**\n"
    good_map = {"claims": [{"id": "T1", "claim": "x", "docs": [__file__],
                            "status": "advanced"}]}
    apparatus = {"claims": [{"id": "T1", "claim": "x", "docs": [], "status": "unwritten"}]}
    absent_doc = {"claims": [{"id": "T1", "claim": "x",
                              "docs": ["/nonexistent/x.html"], "status": "advanced"}]}
    results = []
    p, _, _ = evaluate(good_thesis, good_map)
    results.append(("silent on advanced claim", p == [], f"{p}"))
    p, _, _ = evaluate(good_thesis, apparatus)
    results.append(("fires when zero claims advanced",
                    any("ZERO_THESIS_ADVANCE" in x for x in p), f"{p}"))
    p, _, _ = evaluate(good_thesis, absent_doc)
    results.append(("fires on absent document",
                    any("ABSENT_DOC" in x for x in p), f"{p}"))
    p, _, _ = evaluate("# THESIS\n\nno declaration here\n", good_map)
    results.append(("fires on undeclared objective",
                    any("THESIS_UNDECLARED" in x for x in p), f"{p}"))
    print("=" * 78)
    print("THESIS GATE — SELFTEST")
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
