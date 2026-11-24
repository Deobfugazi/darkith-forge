#!/usr/bin/env python3
"""etymon_trace.py — NEVER #27 clause 4 / MUST #46 clause 3. A word's etymon, sourced.

The Atlas requires every claim to carry `src:` with a URL/DOI/ISBN and a retrieved date, or be
marked OPEN (Rule 8 / Gate 1). This applies that rule to etymology, because a semantic argument
that rests on an etymon is a claim, and an unsourced etymon is exactly the "doubly mean word"
the Operator traced by hand.

Trace table: docs/ETYMON-TRACE.json
  { "traces": [ {"word": "...", "etymon": "...", "literal": "...",
                 "src": {"url": "...", "retrieved": "YYYY-MM-DD"},
                 "attested_in": "docs/.../path" } ] }

Each trace must:
  1. carry a src with url (or doi/isbn) AND retrieved date, or be declared OPEN with a date
  2. state the literal sense, not just the modern one
  3. name where the traced word is used in the delivered argument

Exit 0 = every trace sourced and located. Exit 1 = an unsourced or unlocated trace.
Exit 3 = table absent.
"""
from __future__ import annotations

import json
import re
import sys
import pathlib

TABLE = pathlib.Path("docs/ETYMON-TRACE.json")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate(traces: list[dict]) -> list[str]:
    problems = []
    for t in traces:
        w = t.get("word", "?")
        src = t.get("src", {})
        if src.get("open"):
            if not ISO.match(src.get("date", "")):
                problems.append(f"OPEN_WITHOUT_DATE {w}")
        else:
            if not (src.get("url") or src.get("doi") or src.get("isbn")):
                problems.append(f"NO_SOURCE {w} — needs url/doi/isbn or OPEN")
            if not ISO.match(src.get("retrieved", "")):
                problems.append(f"NO_RETRIEVED_DATE {w}")
        if not t.get("literal"):
            problems.append(f"NO_LITERAL_SENSE {w} — the modern gloss alone is the drift")
        if not t.get("attested_in"):
            problems.append(f"NOT_LOCATED {w} — name where the argument uses it")
        elif not pathlib.Path(t["attested_in"]).exists():
            problems.append(f"LOCATION_ABSENT {w} -> {t['attested_in']}")
    return problems


def run() -> int:
    if not TABLE.exists():
        print("ETYMON_TRACE: SKIP table_absent (a skip is never a pass, SPI-31)")
        return 3
    traces = json.loads(TABLE.read_text()).get("traces", [])
    problems = validate(traces)
    print("=" * 78)
    print("ETYMON TRACE — every traced word sourced, literal, and located")
    print("=" * 78)
    print(f"traces : {len(traces)}")
    for t in traces:
        s = t.get("src", {})
        ref = s.get("url") or s.get("doi") or s.get("isbn") or ("OPEN " + s.get("date", ""))
        print(f"  {t.get('word','?'):<14} {t.get('literal','')[:44]:<46} {ref[:40]}")
    for p in problems:
        print(f"  [DEFECT] {p}")
    ok = not problems
    print("\n" + "=" * 78)
    print(f"VERDICT: {'TRACES_SOURCED' if ok else 'UNSOURCED_TRACE'}")
    print("=" * 78)
    return 0 if ok else 1


def selftest() -> int:
    good = [{"word": "war", "literal": "confusion", "attested_in": __file__,
             "src": {"url": "https://en.wiktionary.org/wiki/war", "retrieved": "2026-11-10"}}]
    no_src = [{"word": "war", "literal": "confusion", "attested_in": __file__, "src": {}}]
    no_date = [{"word": "war", "literal": "confusion", "attested_in": __file__,
                "src": {"url": "https://x", "retrieved": "yesterday"}}]
    no_literal = [{"word": "war", "attested_in": __file__,
                   "src": {"url": "https://x", "retrieved": "2026-11-10"}}]
    results = [
        ("silent on sourced trace", validate(good) == [], ""),
        ("fires on missing source", len(validate(no_src)) >= 1, f"{validate(no_src)}"),
        ("fires on non-ISO date", len(validate(no_date)) == 1, f"{validate(no_date)}"),
        ("fires on modern gloss only", len(validate(no_literal)) == 1, f"{validate(no_literal)}"),
    ]
    print("=" * 78)
    print("ETYMON TRACE — SELFTEST")
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
