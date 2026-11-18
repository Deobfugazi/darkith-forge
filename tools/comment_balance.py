#!/usr/bin/env python3
"""comment_balance.py — character-level Kotlin comment-balance gate.

A blind `sed` that strips an opening `/*` leaves a file whose block comment
never closes: kotlinc then reports "Unclosed comment" and the raw chain stops.
This walks each Kotlin file as a lexer — code / line-comment / block-comment
(nestable) / string / raw-string / char — and fails if any block comment is
still open at EOF. It reads the bytes (SPI-2), never guesses.

  python3 tools/comment_balance.py [ROOT]
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

# Kotlin block comments NEST, so a depth counter is required, not a flag.
CODE, LINE, BLOCK, STR, RAW, CHR = range(6)


def scan(text: str) -> tuple[int, int, int]:
    """Return (unclosed_depth, line_of_first_unclosed_open, line_of_orphan_close).

    An orphan `*/` (a close with no open) is the fingerprint of a stripped `/*`:
    the block body survives as bare code lines ending in `*/`. Both an unclosed
    open and an orphan close are syntax errors, so both are reported.
    """
    state = CODE
    depth = 0
    open_line = 0
    orphan_line = 0
    line = 1
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if c == "\n":
            line += 1
        if state == CODE:
            if c == "/" and nxt == "/":
                state = LINE; i += 2; continue
            if c == "/" and nxt == "*":
                state = BLOCK; depth = 1; open_line = line; i += 2; continue
            if c == "*" and nxt == "/":
                if orphan_line == 0:
                    orphan_line = line
                i += 2; continue
            if c == '"':
                if text[i:i + 3] == '"""':
                    state = RAW; i += 3; continue
                state = STR; i += 1; continue
            if c == "'":
                state = CHR; i += 1; continue
        elif state == LINE:
            if c == "\n":
                state = CODE
        elif state == BLOCK:
            if c == "/" and nxt == "*":
                depth += 1; i += 2; continue
            if c == "*" and nxt == "/":
                depth -= 1; i += 2
                if depth == 0:
                    state = CODE
                continue
        elif state == STR:
            if c == "\\":
                i += 2; continue
            if c == '"':
                state = CODE
        elif state == RAW:
            if text[i:i + 3] == '"""':
                state = CODE; i += 3; continue
        elif state == CHR:
            if c == "\\":
                i += 2; continue
            if c == "'":
                state = CODE
        i += 1
    return depth, open_line, orphan_line


def main() -> int:
    files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "*.kt"],
                           capture_output=True, text=True).stdout.split()
    if not files:
        files = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*.kt")]
    bad = []
    for rel in files:
        p = ROOT / rel
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        depth, ln, orphan = scan(text)
        if depth:
            bad.append((rel, ln, f"unclosed block comment (depth {depth} at EOF)"))
        if orphan:
            bad.append((rel, orphan, "orphan '*/' with no opening '/*'"))
    if bad:
        print(f"comment_balance: FAIL — {len(bad)} problem(s) across the tree")
        for rel, ln, why in bad:
            print(f"  {rel}:{ln}  {why}")
        return 1
    print(f"comment_balance: PASS — {len(files)} Kotlin file(s), every block comment closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
