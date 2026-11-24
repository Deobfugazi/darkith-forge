#!/usr/bin/env python3
"""citation_gate.py — NEVER #27 / MUST #46. Citations are checked ONLY where attributed.

The gate exists to catch a claim the document ATTRIBUTES to a source that the source does not
contain ("NT VI names Condition C" when NT VI has Conditions 1-3).

It must never be turned on the author's own coinage. A phrase the Operator introduces is not a
citation; it is his name for his own concept, and the gate protects it from deletion.

Table: docs/CITATION-TABLE.json
  { "citations": [ {"claim": "...", "source": "...", "must_contain": ["..."]} ],
    "protected_coinages": [ {"phrase": "...", "source": "...", "note": "..."} ] }

Exit 0 = every attributed row found AND every protected coinage still present.
Exit 1 = an invented attribution, or a protected coinage was deleted.
Exit 3 = table absent (a skip is never a pass).
"""
from __future__ import annotations

import json
import sys
import pathlib

TABLE = pathlib.Path("docs/CITATION-TABLE.json")

# The corpus and the Operator's research documents sit beside the repo, not inside it.
# Resolve each source against every root and record which one answered, so a missing file
# is reported as missing rather than silently passing.
CORPUS_ROOTS = [pathlib.Path("."), pathlib.Path(".."), pathlib.Path("../..")]


def resolve(src: str) -> pathlib.Path | None:
    for root in CORPUS_ROOTS:
        cand = root / src
        if cand.is_file():
            return cand
    return None


def check(rows: list[dict], read) -> list[str]:
    problems = []
    for r in rows:
        src = r.get("source")
        try:
            text = read(src)
        except Exception:
            problems.append(f"SOURCE_ABSENT {r.get('claim')} -> {src}")
            continue
        for needle in r.get("must_contain", []):
            if needle not in text:
                problems.append(f"INVENTED {r.get('claim')} -> {needle!r} absent from {src}")
    return problems


def check_coinages(coinages: list[dict], read) -> list[str]:
    """A protected coinage must still exist in the Operator's source. Absence = deletion."""
    problems = []
    for c in coinages:
        phrase, src = c.get("phrase", ""), c.get("source")
        try:
            text = read(src)
        except Exception:
            problems.append(f"COINAGE_SOURCE_ABSENT {phrase!r} -> {src}")
            continue
        if phrase not in text:
            problems.append(f"COINAGE_DELETED {phrase!r} is absent from {src} — the author's "
                            f"wording was removed")
    return problems


def run() -> int:
    if not TABLE.exists():
        print("CITATION_GATE: SKIP table_absent (a skip is never a pass, SPI-31)")
        return 3
    doc = json.loads(TABLE.read_text())
    rows = doc.get("citations", [])
    coinages = doc.get("protected_coinages", [])
    def read(p: str) -> str:
        f = resolve(p)
        if f is None:
            raise FileNotFoundError(p)
        return f.read_text()
    problems = check(rows, read) + check_coinages(coinages, read)

    present = sum(1 for c in coinages
                  if resolve(c["source"]) and c.get("phrase", "") in read(c["source"]))
    print("=" * 78)
    print("CITATION GATE — attributed claims grepped; author's coinages protected")
    print("=" * 78)
    print(f"attributed rows    : {len(rows)}")
    print(f"needles            : {sum(len(r.get('must_contain', [])) for r in rows)}")
    print(f"protected coinages : {len(coinages)}")
    print(f"coinages present   : {present}")
    for p in problems:
        print(f"  [DEFECT] {p}")
    ok = not problems
    print("\n" + "=" * 78)
    print(f"VERDICT: {'CITATIONS_REAL_AND_AUTHOR_INTACT' if ok else 'DEFECT'}")
    print("=" * 78)
    return 0 if ok else 1


def selftest() -> int:
    corpus = {"docs/nt/NT-VI.txt": "Condition 1 — Disjointness\nCondition 2 — Continuity\n"
                                  "Condition 3 — Synchrony\n"}
    operator = {"real upliftment.txt": "Condition C without D. A promise with no server of record.\n"}
    read_c = lambda p: corpus[p]
    read_o = lambda p: operator[p]
    results = []

    attributed_bad = [{"claim": "NT VI names a fourth condition", "source": "docs/nt/NT-VI.txt",
                       "must_contain": ["Condition 4"]}]
    results.append(("fires on invented attribution",
                    len(check(attributed_bad, read_c)) == 1, ""))

    attributed_ok = [{"claim": "NT VI names three conditions", "source": "docs/nt/NT-VI.txt",
                      "must_contain": ["Condition 1", "Condition 2", "Condition 3"]}]
    results.append(("silent on real attribution", check(attributed_ok, read_c) == [], ""))

    # THE POINT OF THE REWRITE: the author's coinage must be SILENT, not flagged.
    coinage_present = [{"phrase": "Condition C without D", "source": "real upliftment.txt"}]
    results.append(("silent on author's coinage (the old bug)",
                    check_coinages(coinage_present, read_o) == [], ""))

    coinage_deleted = [{"phrase": "Condition C without D", "source": "real upliftment.txt"}]
    operator_missing = {"real upliftment.txt": "Condition 1 without Condition 3.\n"}
    read_missing = lambda p: operator_missing[p]
    results.append(("fires when author's wording was deleted",
                    len(check_coinages(coinage_deleted, read_missing)) == 1,
                    f"{check_coinages(coinage_deleted, read_missing)}"))

    print("=" * 78)
    print("CITATION GATE — SELFTEST")
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
