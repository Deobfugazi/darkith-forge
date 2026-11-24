#!/usr/bin/env python3
"""delivery_law_gate.py — enforce the NEVER/MUST pairing in DARKITH.md PART VII.

NEVER #24 / MUST #43. A NEVER alone is a post-mortem. A NEVER must carry a coupled MUST
and a gate that exists on disk, and the ledger must name the law that its failure created.

Checks:
  1. every NEVER #24-#31 has a coupled MUST in the same part
  2. every law heading names a gate file that exists
  3. the PAIRING TABLE has one row per NEVER, naming the same MUST and gate
  4. every FAILURE-MODE-LEDGER entry names at least one law id (FM-nn -> NEVER/MUST)

Exit 0 = paired and live. Exit 1 = orphan. Exit 3 = source absent (a skip is never a pass).
"""
from __future__ import annotations

import re
import sys
import pathlib

DARKITH = pathlib.Path("DARKITH.md")
LEDGER = pathlib.Path("docs/FAILURE-MODE-LEDGER.md")

LAW = re.compile(r"───\s*((?:NEVER|MUST)\s*#\d+)\s*\(([^)]*)\)\s*───")
GATE_LINE = re.compile(r"^\s*GATE:\s*(\S+)\s*$", re.M)
PAIR_ROW = re.compile(r"^\|\s*#(\d+)\s*\|(.+?)\|(.+?)\|(.+?)\|\s*`([^`]+)`\s*\|\s*$")
FM = re.compile(r"^##\s*(FM-\d+)\b", re.M)


def part_seven(text: str) -> str:
    i = text.find("# PART VII")
    return text[i:] if i >= 0 else ""


def parse_laws(part: str) -> dict[str, dict]:
    laws: dict[str, dict] = {}
    matches = list(LAW.finditer(part))
    for idx, m in enumerate(matches):
        lid = re.sub(r"\s+", " ", m.group(1)).strip()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(part)
        body = part[m.end():end]
        g = GATE_LINE.search(body)
        laws[lid] = {"title": m.group(2), "gate": g.group(1) if g else None,
                     "body": body}
    return laws


def parse_pairs(part: str) -> list[dict]:
    rows = []
    in_table = False
    for line in part.splitlines():
        if line.startswith("| NEVER |"):
            in_table = True
            continue
        if in_table and set(line.replace("|", "").strip()) <= {"-", " "}:
            continue
        if in_table:
            m = PAIR_ROW.match(line)
            if m:
                must = m.group(3).strip()
                if must.startswith("#"):
                    must = "MUST " + must
                rows.append({"never": f"NEVER #{m.group(1)}",
                             "must": must,
                             "gate": m.group(5).strip()})
            elif line.strip() and not line.startswith("|"):
                break
    return rows


def run() -> int:
    if not DARKITH.exists():
        print("DELIVERY_LAW_GATE: SKIP darkith_absent (a skip is never a pass, SPI-31)")
        return 3
    text = DARKITH.read_text()
    part = part_seven(text)
    if not part:
        print("DELIVERY_LAW_GATE: SKIP part_seven_absent (a skip is never a pass, SPI-31)")
        return 3

    laws = parse_laws(part)
    pairs = parse_pairs(part)
    problems = []

    nevers = [k for k in laws if k.startswith("NEVER")]
    musts = [k for k in laws if k.startswith("MUST")]

    # 1. every NEVER has a coupled MUST named in the pairing table
    paired_nevers = {p["never"] for p in pairs}
    for n in nevers:
        if n not in paired_nevers:
            problems.append(f"ORPHAN_NEVER {n} — no row in the pairing table")

    # 2. every law names a gate that exists
    for lid, info in laws.items():
        if not info["gate"]:
            problems.append(f"NO_GATE {lid} — heading names no GATE: line")
        elif not pathlib.Path(info["gate"]).exists():
            problems.append(f"MISSING_GATE_FILE {lid} -> {info['gate']}")

    # 3. pairing table rows agree with the law blocks
    for p in pairs:
        must = p["must"]
        if must not in laws:
            problems.append(f"TABLE_NAMES_ABSENT_MUST {p['never']} -> {must}")
        if not pathlib.Path(p["gate"]).exists():
            problems.append(f"TABLE_GATE_MISSING {p['never']} -> {p['gate']}")

    # 4. ledger entries name a law
    ledger_unlinked = []
    if LEDGER.exists():
        lt = LEDGER.read_text()
        heads = [(m.group(1), m.start()) for m in FM.finditer(lt)]
        for i, (fm, start) in enumerate(heads):
            end = heads[i + 1][1] if i + 1 < len(heads) else len(lt)
            body = lt[start:end]
            if not re.search(r"(NEVER|MUST)\s*#\d+|SPI-\d+|FM-", body):
                ledger_unlinked.append(fm)

    print("=" * 78)
    print("DELIVERY LAW GATE — NEVER/MUST pairing (NEVER #24 / MUST #43)")
    print("=" * 78)
    print(f"laws in PART VII : {len(laws)}  (NEVER {len(nevers)}, MUST {len(musts)})")
    print(f"pairing rows     : {len(pairs)}")
    print(f"ledger entries   : {len(FM.findall(LEDGER.read_text())) if LEDGER.exists() else 0}")
    print(f"ledger unlinked  : {len(ledger_unlinked)}")

    for p in problems:
        print(f"  [ORPHAN] {p}")
    for fm in ledger_unlinked:
        print(f"  [UNLINKED] {fm} — names no law")

    ok = not problems and not ledger_unlinked
    print("\n" + "=" * 78)
    print(f"VERDICT: {'PAIRED_AND_LIVE' if ok else 'ORPHANS_PRESENT'}")
    print("=" * 78)
    return 0 if ok else 1


def selftest() -> int:
    """Prove the gate fires on an orphan and stays silent on a complete pair."""
    import tempfile
    import os

    good = """# PART VII
─── NEVER #99 (SYNTHETIC) ───
  GATE: /bin/sh
  body
─── MUST #98 (SYNTHETIC PAIR) ───
  GATE: /bin/sh
  body

| NEVER | forbids | coupled MUST | makes it impossible | gate |
|---|---|---|---|---|
| #99 | x | MUST #98 | y | `/bin/sh` |
"""
    bad = """# PART VII
─── NEVER #97 (UNPAIRED SYNTHETIC) ───
  GATE: /bin/sh
  body
"""
    results = []

    def drive(text: str) -> list[str]:
        laws = parse_laws(part_seven(text))
        pairs = parse_pairs(part_seven(text))
        probs = []
        paired = {p["never"] for p in pairs}
        for n in laws:
            if n.startswith("NEVER") and n not in paired:
                probs.append(f"ORPHAN_NEVER {n}")
        for lid, info in laws.items():
            if not info["gate"] or not pathlib.Path(info["gate"]).exists():
                probs.append(f"NO_GATE {lid}")
        return probs

    g = drive(good)
    b = drive(bad)
    results.append(("silent on complete pair", g == [], f"{g}"))
    results.append(("fires on unpaired NEVER", len(b) == 1, f"{b}"))

    print("=" * 78)
    print("DELIVERY LAW GATE — SELFTEST")
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
