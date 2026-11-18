#!/usr/bin/env python3
"""syntax_gate.py — fail if any Kotlin tree has an unclosed or orphan block comment.

W-023 says a scanner is not a parser and grep cannot read structure. The ONE
canonical lexer lives in `tools/kt_comment_scan.py` (SPI-27: import it, never
fork it). This gate is the CI entrypoint: it scans the given tree roots with that
lexer and fails on either defect class:

  UNCLOSED     a '/*' that never reaches a matching '*/' (nesting honored)
  ORPHAN_CLOSE a '*/' with no opening '/*' — the fingerprint a blind `sed` leaves
               when it strips an opening '/*'

It is not kotlinc, so it cannot prove a file compiles — but it is exact about the
one defect that silently swallows the rest of a file.

Exit 0 if every file is clean; exit 1 otherwise, printing the file and line.

Usage:
  python3 tools/syntax_gate.py <tree-root> [more roots...]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kt_comment_scan import scan  # noqa: E402  (the canonical lexer)


def main(argv: list[str]) -> int:
    roots = [pathlib.Path(a) for a in argv[1:]]
    if not roots:
        print("usage: syntax_gate.py <tree-root> [more roots...]", file=sys.stderr)
        return 2
    failures = []
    total = 0
    for root in roots:
        for p in sorted(root.rglob("*.kt")):
            total += 1
            text = p.read_text(encoding="utf-8", errors="replace")
            for kind, ln, col in scan(text):
                if kind == "UNCLOSED":
                    failures.append((p, f"unclosed /* opened at line {ln}"))
                elif kind == "ORPHAN_CLOSE":
                    failures.append((p, f"orphan */ with no opening /* at line {ln}"))
    if failures:
        print(f"syntax_gate: FAIL — {len(failures)} defect(s) in {total} scanned .kt file(s):")
        for p, why in failures:
            print(f"  {p}: {why}")
        return 1
    print(f"syntax_gate: PASS — {total} .kt file(s), every block comment closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
