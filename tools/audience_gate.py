#!/usr/bin/env python3
"""audience_gate.py — NEVER #25 / MUST #44. The general register is burden-first and apparatus-free.

Scans the general-register byte range of the delivered document for apparatus vocabulary and
for the position of the first burden. The apparatus belongs in the technical register; this
gate proves it was relocated, not merely promised.

Exit 0 = general register clean and burden-first. Exit 1 = violation. Exit 3 = doc absent.
"""
from __future__ import annotations

import re
import sys
import pathlib

DOC = pathlib.Path("docs/MISCOMMUNICATION-AND-WAR.html")

# Tokens that must never appear in front of a reader who has no interest in the machinery.
BANNED = ["sha256", "hash", "gate", "receipt", "resolver", "invariant", "manifest",
          "falsif", "dimension vector", "root hash", "commit", "SPI-", "NT-",
          "register 2", "register 3", "reconcil"]
# Proper nouns that merely share a stem with apparatus vocabulary.
ALLOW = ["truth-and-reconciliation", "reconciliation process"]

# The general-reader document has no register split; the whole body is the general register.
GENERAL_OPEN = re.compile(r'<h1[^>]*>', re.I)
TECH_OPEN = re.compile(r'<hr\s*/?>\s*<p class="sub"', re.I)
BURDEN = re.compile(r'<h2[^>]*>\s*(?:Start with|The claim)', re.I)


def strip_tags(h: str) -> str:
    return re.sub(r"<[^>]+>", " ", h)


def scan(text: str) -> tuple[list[str], int]:
    a, b = GENERAL_OPEN.search(text), TECH_OPEN.search(text)
    if not a or not b:
        return ["REGISTER_HEADINGS_ABSENT"], -1
    seg = text[a.end():b.start()]
    low = strip_tags(seg).lower()
    for a in ALLOW:
        low = low.replace(a.lower(), "")
    hits = sorted({t for t in BANNED if t.lower() in low})
    m = BURDEN.search(seg)
    return hits, (m.start() if m else -1)


def run() -> int:
    if not DOC.exists():
        print("AUDIENCE_GATE: SKIP doc_absent (a skip is never a pass, SPI-31)")
        return 3
    text = DOC.read_text()
    hits, pos = scan(text)
    print("=" * 78)
    print("AUDIENCE GATE — general register is burden-first and apparatus-free")
    print("=" * 78)
    print(f"document      : {DOC}")
    print(f"banned tokens : {len(hits)}  {hits}")
    print(f"first burden  : {'ABSENT' if pos < 0 else f'at char {pos}'}")
    ok = not hits and pos >= 0
    print("\n" + "=" * 78)
    print(f"VERDICT: {'READER_FIRST' if ok else 'APPARATUS_IN_GENERAL_REGISTER'}")
    print("=" * 78)
    return 0 if ok else 1


def selftest() -> int:
    close = '<hr><p class="sub">footer</p>'
    clean = ('<h1>Why Wars Start</h1><p>Your water bill doubled.</p>'
             '<h2>Start with what you know</h2><p>plain</p>' + close)
    dirty = ('<h1>Why Wars Start</h1><p>The sha256 of the receipt failed.</p>'
             '<h2>Start with what you know</h2><p>plain</p>' + close)
    no_burden = ('<h1>Why Wars Start</h1><p>Framing about the author.</p>' + close)
    results = []
    h, p = scan(clean)
    results.append(("silent on clean burden-first register", h == [] and p >= 0, f"{h} pos={p}"))
    h, p = scan(dirty)
    results.append(("fires on apparatus vocabulary", len(h) > 0, f"{h}"))
    h, p = scan(no_burden)
    results.append(("fires when no burden appears", p < 0, f"pos={p}"))
    print("=" * 78)
    print("AUDIENCE GATE — SELFTEST")
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
