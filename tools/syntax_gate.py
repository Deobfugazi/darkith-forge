#!/usr/bin/env python3
"""syntax_gate.py — fail if a Kotlin tree has an unclosed block comment.

W-023 says a scanner is not a parser and grep cannot read structure. This is a real
scanner: it tracks "..." strings, '...' chars, \"\"\" raw strings, // line comments and
NESTED /* */ block comments. It is not kotlinc, so it cannot prove a file compiles — but
it is exact about the one defect that matters here: a block comment that never closes.

Exit 0 if every file closes all block comments; exit 1 otherwise, printing the file and
the line where the last block comment opened.

Usage:
  python3 tools/syntax_gate.py <tree-root> [more roots...]
"""
from __future__ import annotations

import pathlib
import sys


def scan(text: str):
    """Return the line number where an unclosed block comment opened, or None.

    Returns (unterminated: bool, open_line: int|None).
    """
    depth = 0
    open_line = None
    in_str = in_char = False
    raw = 0
    for lineno, ln in enumerate(text.splitlines(), 1):
        i, n = 0, len(ln)
        while i < n:
            c = ln[i]
            two = ln[i:i + 2]
            three = ln[i:i + 3]
            if raw:
                if three == '"""':
                    raw -= 1
                    i += 3
                    continue
                i += 1
                continue
            if in_str:
                if c == "\\":
                    i += 2
                    continue
                if c == '"':
                    in_str = False
                i += 1
                continue
            if in_char:
                if c == "\\":
                    i += 2
                    continue
                if c == "'":
                    in_char = False
                i += 1
                continue
            if three == '"""':
                raw += 1
                i += 3
                continue
            if depth:
                if two == "/*":
                    depth += 1
                    i += 2
                    continue
                if two == "*/":
                    depth -= 1
                    i += 2
                    continue
                i += 1
                continue
            if two == "/*":
                depth = 1
                open_line = lineno
                i += 2
                continue
            if two == "//":
                break
            if c == '"':
                in_str = True
                i += 1
                continue
            if c == "'":
                in_char = True
                i += 1
                continue
            i += 1
    return depth > 0, open_line


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
            unterm, line = scan(p.read_text(encoding="utf-8", errors="replace"))
            if unterm:
                failures.append((p, line))
    if failures:
        print(f"syntax_gate: FAIL — {len(failures)} file(s) with an unclosed block comment "
              f"(of {total} scanned):")
        for p, line in failures:
            print(f"  {p}: unclosed /* opened at line {line}")
        return 1
    print(f"syntax_gate: PASS — {total} .kt file(s), every block comment closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
