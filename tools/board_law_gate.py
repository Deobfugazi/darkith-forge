#!/usr/bin/env python3
"""Fail if the board taxonomy cites a law that does not exist.

Why this gate exists: while writing `board_priority.py` I cited "NEVER #10" for a
stale installer payload. There is no NEVER #10. The citation looked authoritative,
which is exactly what makes a fabricated law dangerous — a reader who trusts the
board would treat an invented rule as binding, and a real one as negotiable.

A taxonomy entry is a claim about the law. This gate checks every claim against the
law files, so an invented citation fails CI instead of being published.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAW_FILES = ("DARKITH.md", "AGENTS.md")
TAXONOMY_FILE = ROOT / "tools" / "board_priority.py"

CITATION = re.compile(r"NEVER #(\d+)\s*[—-]\s*([A-Z][A-Z0-9 ,'’/—-]+)")
LAW_DEF = re.compile(r"NEVER #(\d+)\s*\(([^)]+)\)")
LOOSE_DEF = re.compile(r"NEVER #(\d+)\s+([A-Z][A-Za-z ,'’—-]+):")


def law_inventory() -> dict:
    """Map every NEVER number defined in the law to its declared title."""
    found = {}
    for name in LAW_FILES:
        path = ROOT / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, title in LAW_DEF.findall(text):
            found.setdefault(int(number), title.strip())
        for number, title in LOOSE_DEF.findall(text):
            found.setdefault(int(number), title.strip())
    return found


def cited_in_taxonomy() -> list:
    if not TAXONOMY_FILE.is_file():
        return []
    text = TAXONOMY_FILE.read_text(encoding="utf-8", errors="replace")
    return [(int(n), t.strip()) for n, t in CITATION.findall(text)]


def main() -> int:
    law = law_inventory()
    cited = cited_in_taxonomy()
    if not law:
        print("board_law_gate: FAIL — no NEVER definitions found; the law files "
              "moved or the pattern rotted")
        return 1
    if not cited:
        print("board_law_gate: PASS — taxonomy cites no numbered law "
              f"({len(law)} defined)")
        return 0

    fails = []
    for number, title in cited:
        if number not in law:
            fails.append(f"NEVER #{number} ({title}) is cited but never defined "
                         f"in {' / '.join(LAW_FILES)}")
            continue
        declared = law[number].upper()
        # Titles must agree on substance, not punctuation. Compare the leading word
        # of each: "ONE TREE" vs "NO UNPROVEN CURRENCY" are clearly different laws.
        lead = re.sub(r"[^A-Z ]", "", title.upper()).split()
        if lead and lead[0] not in declared and declared.split()[0] not in title.upper():
            fails.append(f"NEVER #{number} is titled {title!r} here but "
                         f"{law[number]!r} in the law")

    if fails:
        print(f"board_law_gate: FAIL — {len(fails)} fabricated or drifted citation(s):")
        for f in fails:
            print("  " + f)
        return 1
    print(f"board_law_gate: PASS — {len(cited)} citation(s) across {len(law)} "
          f"defined law(s), every one real")
    return 0


if __name__ == "__main__":
    sys.exit(main())
