#!/usr/bin/env python3
"""Restore a mangled block-comment CLOSER (SPI-2: read bytes, verify, then write).

The 19-file briefing assumed a stripped OPENER ('/*' removed). The physical bytes
show the opposite: the OPENER is intact and the CLOSER was mangled to '//'.
This tool only rewrites a line that the scanner proves sits inside an unclosed
block comment, and only when that line's non-space content is exactly '//'.
Nothing else is touched. Idempotent.
"""
import sys, re
from kt_comment_scan import scan

def fix(path):
    with open(path, 'r', encoding='utf-8', errors='surrogateescape') as fh:
        lines = fh.readlines()
    before = scan(''.join(lines))
    unclosed = [d for d in before if d[0] == 'UNCLOSED']
    if not unclosed:
        return path, 'NO_CHANGE (no UNCLOSED defect)', None
    open_line = unclosed[0][1]
    changed = []
    for idx in range(open_line - 1, len(lines)):
        if re.fullmatch(r'[ \t]*//[ \t]*\n?', lines[idx]):
            changed.append(idx)
    if len(changed) != 1:
        return path, f'REFUSE (found {len(changed)} candidate closer lines)', None
    i = changed[0]
    original = lines[i]
    lines[i] = ' */\n'
    after = scan(''.join(lines))
    if after:
        return path, f'REFUSE (post-fix still defective: {after})', None
    with open(path, 'w', encoding='utf-8', errors='surrogateescape') as fh:
        fh.writelines(lines)
    return path, f'FIXED line {i+1}: {original!r} -> {lines[i]!r}', (open_line, i+1)

TARGETS = sys.argv[1:]
rc = 0
for p in TARGETS:
    path, msg, detail = fix(p)
    print(f"  {msg}\n    {path}")
    if not msg.startswith('FIXED') and not msg.startswith('NO_CHANGE'):
        rc = 1
sys.exit(rc)
