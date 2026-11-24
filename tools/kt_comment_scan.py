#!/usr/bin/env python3
"""Kotlin comment/string-aware scanner (SPI-10: pattern-based, never line-number based).

Reports two defect classes, both symptoms of a stripped block-comment opener:
  UNCLOSED     a '/*' that never reaches a matching '*/' (nesting honored)
  ORPHAN_CLOSE a '*/' found in code state, i.e. a closer with no opener

Aware of: nested block comments, '//' line comments, "..." strings,
'...' char literals, \"\"\"...\"\"\" raw strings, and backslash escapes.
Exit 0 iff zero defects.
"""
import sys, os, json, argparse

def scan(src):
    n = len(src); i = 0; line = 1; col = 1
    state = 'code'; depth = 0; open_line = open_col = None
    defects = []
    while i < n:
        c = src[i]; nxt = src[i+1] if i+1 < n else ''
        if state == 'code':
            if c == '/' and nxt == '/':      state = 'line'; i += 2; col += 2; continue
            if c == '/' and nxt == '*':      state = 'block'; depth = 1; open_line, open_col = line, col; i += 2; col += 2; continue
            if c == '*' and nxt == '/':      defects.append(('ORPHAN_CLOSE', line, col)); i += 2; col += 2; continue
            if c == '"':
                if src[i:i+3] == '"""':      state = 'raw'; i += 3; col += 3; continue
                state = 'string'; i += 1; col += 1; continue
            if c == "'":                     state = 'char'; i += 1; col += 1; continue
            if c == '\n':                    line += 1; col = 1; i += 1; continue
            i += 1; col += 1; continue
        if state == 'line':
            if c == '\n':                    state = 'code'; line += 1; col = 1; i += 1; continue
            i += 1; col += 1; continue
        if state == 'block':
            if c == '/' and nxt == '*':      depth += 1; i += 2; col += 2; continue
            if c == '*' and nxt == '/':
                depth -= 1; i += 2; col += 2
                if depth == 0: state = 'code'
                continue
            if c == '\n':                    line += 1; col = 1; i += 1; continue
            i += 1; col += 1; continue
        if state == 'string':
            if c == '\\':                    i += 2; col += 2; continue
            if c == '"':                     state = 'code'; i += 1; col += 1; continue
            if c == '\n':                    state = 'code'; line += 1; col = 1; i += 1; continue
            i += 1; col += 1; continue
        if state == 'raw':
            if src[i:i+3] == '"""':          state = 'code'; i += 3; col += 3; continue
            if c == '\n':                    line += 1; col = 1; i += 1; continue
            i += 1; col += 1; continue
        if state == 'char':
            if c == '\\':                    i += 2; col += 2; continue
            if c == "'":                     state = 'code'; i += 1; col += 1; continue
            if c == '\n':                    state = 'code'; line += 1; col = 1; i += 1; continue
            i += 1; col += 1; continue
    if state == 'block':
        defects.append(('UNCLOSED', open_line, open_col))
    return defects

FIXTURES = {
    'clean.kt':            'package a\n/* ok */\nfun f() {}\n',
    'unclosed.kt':         'package a\n/* Copyright\n * line\nfun g() {}\n',
    'orphan_close.kt':     'package a\n * Copyright\n */\nfun h() {}\n',
    'nested.kt':           '/* a /* b */ c */\nfun i() {}\n',
    'string_has_comment.kt':'val s = "/* not a comment */"\nfun j() {}\n',
    'raw_has_comment.kt':  'val s = """/* neither */ */"""\nfun k() {}\n',
    'char_star.kt':        "val c = '*'\nfun l() {}\n",
}
EXPECT = {'clean.kt':0,'unclosed.kt':1,'orphan_close.kt':1,'nested.kt':0,
          'string_has_comment.kt':0,'raw_has_comment.kt':0,'char_star.kt':0}

def selftest():
    ok = True
    for name, src in FIXTURES.items():
        d = scan(src)
        got = len(d)
        want = EXPECT[name]
        flag = 'PASS' if got == want else 'FAIL'
        if got != want: ok = False
        print(f"  [{flag}] {name}: expected {want} defect(s), got {got} {d}")
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1

def discover():
    """Every Kotlin source under app/src. The default target, so a bare run is a real check."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = []
    for dirpath, _, names in os.walk(os.path.join(root, 'app', 'src')):
        out.extend(os.path.join(dirpath, n) for n in names if n.endswith('.kt'))
    return sorted(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    if a.selftest: return selftest()
    files = a.files or discover()
    if not files:
        print('DEFECT: no Kotlin sources found — a scan over zero files proves nothing',
              file=sys.stderr)
        return 1
    total = 0; report = []
    for f in files:
        src = open(f, 'r', encoding='utf-8', errors='surrogateescape').read()
        d = scan(src)
        report.append({'file': f, 'defects': d})
        total += len(d)
        for kind, ln, cl in d:
            print(f"  DEFECT: {f}:{ln}:{cl}: {kind}")
    if a.json: print(json.dumps(report, indent=2))
    print(f"TOTAL DEFECTS: {total}")
    return 0 if total == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
