#!/usr/bin/env python3
"""Enforce SPI-15 (a law that is not an executable gate is a note) and the PRIME OMEGA
DIRECTIVE (DARKITH.md §30: NEVER #18 / MUST #21 / MUST #22 / SPI-23 / SPI-24).

Why this exists: 24 laws (NEVER #11-#17, MUST #10-#20, SPI-1-#22) were declared but only a
handful were backed by a gate. The prime directive — that every fix is promoted to its
class and made portable — was never declared at all. This gate makes the declaration
binding: every NEVER/MUST/SPI in DARKITH.md must either name an executable gate that
exists on disk, or carry the explicit marker `[NOTE: not yet gated]`.

This is deliberately exact and small: it does not try to prove a law is *enforced*, only
that it is *declared with a gate*. The stronger claim (the gate actually checks the law)
is each gate's own job.

BASELINE FIRST PRINCIPLE — NO HEADING, NO CLOSURE.
This gate once matched only the `─── NEVER #18 (…) ───` heading form, so a law written as
inline prose was not merely ungated, it was INVISIBLE: the scan stepped over it and the gate
still printed PASS. Six laws (NEVER #12/#13, MUST #10-#13) were declared that way and no
gate ever saw them. A gatekeeper that skips headings is not a gatekeeper — it is a filter
that reports success on the input it declined to read. So an unheaded law declaration is now
itself a FAIL, with the line number, because the defect is not "this law has no gate" but
"this law was never enrolled in the ledger at all".

Fails if:
  - DARKITH.md has no §30 PRIME OMEGA DIRECTIVE (the prime directive must exist);
  - a law is declared WITHOUT a heading (invisible to every gate — the baseline violation);
  - a NEVER/MUST/SPI heading names no gate and carries no `[NOTE: not yet gated]` marker;
  - a named gate path does not exist on disk.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "DARKITH.md"

# A law heading, e.g. "─── NEVER #18 (NO LOCAL-ONLY RESOLUTION) ───"
LAW = re.compile(r"───\s*((?:NEVER|MUST|SPI)-?\s*#?\d+)\s*(?:\(([^)]*)\))?\s*───")
# A gate citation inside a law body: tools/foo.py, tools/foo.sh or tools/foo.js
# The trailing lookahead is load-bearing: without it `tools/unit_ledger.json` parses as
# `tools/unit_ledger.js` + a stranded `on`, because `js` is an alternative and the
# character class before it happily eats the dot. A detector that matches a PREFIX of
# the name it is looking for reports a gate that does not exist (SPI-35).
GATE = re.compile(r"tools/[\w.-]+\.(?:py|sh|js)(?![\w.-])")
NOTE = "[NOTE: not yet gated]"

# A law declaration in prose: the id at the start of a line, followed by "(" or ":".
# Deliberately anchored to line start so a passing mention mid-sentence is not a declaration.
# A law declared as prose with no heading. The separator may be SPACE, HYPHEN, or `#`:
# `SPI-1:`, `SPI 1:`, `SPI#1:`, `MUST-12:`. The first version required whitespace, so
# it was blind to the hyphenated spelling the document actually uses — and reported
# "zero unheaded" over eleven ungated laws (SPI-1..SPI-11). A detector that cannot see
# the common form of the thing it detects is the same defect as a gate that cannot fail.
INLINE = re.compile(r"^[ \t]*(?:[-*][ \t]+)?((?:NEVER|MUST|SPI)[ \t]*[-#]?[ \t]*\d+)[ \t]*[(:]")


def law_id(tok: str) -> str:
    """Canonical id: 'NEVER #11', 'never 11', 'SPI-2', 'MUST-12' -> comparable form."""
    m = re.match(r"(NEVER|MUST|SPI)\s*-?\s*#?\s*(\d+)$", tok.upper().strip())
    if not m:
        return tok.upper().strip()
    kind, num = m.group(1), m.group(2)
    return f"SPI-{num}" if kind == "SPI" else f"{kind} #{num}"


def law_blocks(text: str):
    """Yield (law_id, title, body) for each law heading."""
    lines = text.splitlines()
    hits = [(i, m) for i, line in enumerate(lines) for m in [LAW.search(line)] if m]
    for idx, (i, m) in enumerate(hits):
        end = hits[idx + 1][0] if idx + 1 < len(hits) else len(lines)
        yield law_id(m.group(1)), (m.group(2) or "").strip(), "\n".join(lines[i:end])


def unheaded_laws(text: str) -> list[tuple[int, str, str]]:
    """Law declarations with no heading: (line_number, law_id, the line).

    A heading line is excluded by construction — if the line carries a `───` law heading,
    LAW.search() matches it and the id is already enrolled in the ledger.
    """
    headed = set()
    for line in text.splitlines():
        m = LAW.search(line)
        if m:
            headed.add(law_id(m.group(1)))
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if LAW.search(line):
            continue
        m = INLINE.match(line)
        if m and law_id(m.group(1)) not in headed:
            out.append((n, law_id(m.group(1)), line.strip()))
    return out


def main() -> int:
    if not DOC.is_file():
        print("law_gate: FAIL — no DARKITH.md")
        return 1
    text = DOC.read_text(encoding="utf-8")

    if "PRIME OMEGA DIRECTIVE" not in text:
        print("law_gate: FAIL — DARKITH.md declares no §30 PRIME OMEGA DIRECTIVE")
        return 1

    fails, ungated, gated = [], [], 0
    for law_id_s, title, body in law_blocks(text):
        gates = GATE.findall(body)
        if gates:
            gated += 1
            for g in gates:
                if not (ROOT / g).exists():
                    fails.append(f"{law_id_s} names a gate that does not exist: {g}")
        elif NOTE in body:
            fails.append(f"{law_id_s}: carries '{NOTE}' — notes are forbidden; build the gate")
        else:
            fails.append(
                f"{law_id_s} ({title[:44]}) names no gate and carries no '{NOTE}' marker "
                f"(SPI-15: an ungated law is a note)")

    # Baseline first principle: a law with no heading is not in the ledger at all.
    for n, lid, line in unheaded_laws(text):
        fails.append(
            f"{lid} is declared WITHOUT a heading at DARKITH.md:{n} — invisible to every gate "
            f"(NO HEADING, NO CLOSURE). Recast it as '─── {lid} (TITLE) ───' + 'GATE: tools/…'. "
            f"Line: {line[:72]}")

    if fails:
        print(f"law_gate: FAIL — {len(fails)} problem(s):")
        for f in fails:
            print("  " + f)
        return 1

    print(f"law_gate: PASS — prime directive present; all {gated} law(s) name an existing gate "
          f"(zero notes, zero unheaded)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
