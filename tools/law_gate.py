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

Fails if:
  - DARKITH.md has no §30 PRIME OMEGA DIRECTIVE (the prime directive must exist);
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
# A gate citation inside a law body: tools/foo.py or tools/foo.sh
GATE = re.compile(r"tools/[\w.-]+\.(?:py|sh)")
NOTE = "[NOTE: not yet gated]"


def law_blocks(text: str):
    """Yield (law_id, title, body) for each law heading."""
    lines = text.splitlines()
    hits = [(i, m) for i, line in enumerate(lines) for m in [LAW.search(line)] if m]
    for idx, (i, m) in enumerate(hits):
        end = hits[idx + 1][0] if idx + 1 < len(hits) else len(lines)
        yield m.group(1), (m.group(2) or "").strip(), "\n".join(lines[i:end])


def main() -> int:
    if not DOC.is_file():
        print("law_gate: FAIL — no DARKITH.md")
        return 1
    text = DOC.read_text(encoding="utf-8")

    if "PRIME OMEGA DIRECTIVE" not in text:
        print("law_gate: FAIL — DARKITH.md declares no §30 PRIME OMEGA DIRECTIVE")
        return 1

    fails, ungated, gated = [], [], 0
    for law_id, title, body in law_blocks(text):
        gates = GATE.findall(body)
        if gates:
            gated += 1
            for g in gates:
                if not (ROOT / g).exists():
                    fails.append(f"{law_id} names a gate that does not exist: {g}")
        elif NOTE in body:
            fails.append(f"{law_id}: carries '{NOTE}' — notes are forbidden; build the gate")
        else:
            fails.append(
                f"{law_id} ({title[:44]}) names no gate and carries no '{NOTE}' marker "
                f"(SPI-15: an ungated law is a note)")

    if fails:
        print(f"law_gate: FAIL — {len(fails)} problem(s):")
        for f in fails:
            print("  " + f)
        return 1

    print(f"law_gate: PASS — prime directive present; all {gated} law(s) name an existing gate "
          f"(zero notes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
