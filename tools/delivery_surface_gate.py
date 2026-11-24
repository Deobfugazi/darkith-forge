#!/usr/bin/env python3
"""delivery_surface_gate.py — NEVER #26 / MUST #45. No link presented as a delivery.

Every href in a delivered document must be absolute, SHA-pinned, and carry a declared size
that matches the bytes it names. A relative href resolves against whatever surface renders it;
a branch href moves; a 200 with the wrong byte count is a green light over the wrong bytes.

Offline mode checks structure only (absolute + SHA-pinned + declared size present).
--fetch additionally resolves each link and compares byte counts.

Exit 0 = closed. Exit 1 = violation. Exit 3 = doc absent.
"""
from __future__ import annotations

import re
import sys
import pathlib
import urllib.request

DOC = pathlib.Path("docs/TEN-BURDENS-THREE-TONGUES.html")
# Only download links are delivery surfaces. In-page anchors (#r1) are navigation.
HREF = re.compile(r'<a class="dl" href="([^"]+)"')
SHA = re.compile(r"/[0-9a-f]{40}/")
SIZE = re.compile(r'<span class="sz">([0-9.]+)\s*(B|KB|MB)</span>')


def declared_bytes(n: float, unit: str) -> int:
    mult = {"B": 1, "KB": 1024, "MB": 1024 ** 2}[unit]
    return int(round(n * mult))


def scan(text: str) -> list[dict]:
    rows = []
    for m in HREF.finditer(text):
        url = m.group(1)
        tail = text[m.end():m.end() + 600]
        s = SIZE.search(tail)
        rows.append({
            "url": url,
            "absolute": url.startswith(("http://", "https://")),
            "sha_pinned": bool(SHA.search(url)),
            "declared": declared_bytes(float(s.group(1)), s.group(2)) if s else None,
        })
    return rows


def run(fetch: bool) -> int:
    if not DOC.exists():
        print("DELIVERY_SURFACE_GATE: SKIP doc_absent (a skip is never a pass, SPI-31)")
        return 3
    rows = scan(DOC.read_text())
    problems = []
    for r in rows:
        if not r["absolute"]:
            problems.append(f"RELATIVE {r['url']}")
        elif not r["sha_pinned"]:
            problems.append(f"UNPINNED {r['url']}")
        if r["declared"] is None:
            problems.append(f"NO_DECLARED_SIZE {r['url']}")

    fetched = 0
    if fetch:
        for r in rows:
            if not r["absolute"]:
                continue
            try:
                with urllib.request.urlopen(r["url"], timeout=30) as fh:
                    got = len(fh.read())
            except Exception as exc:
                problems.append(f"FETCH_FAILED {r['url']} {type(exc).__name__}")
                continue
            fetched += 1
            if r["declared"] is not None and got != r["declared"]:
                problems.append(f"SIZE_MISMATCH {r['url']} declared={r['declared']} got={got}")

    print("=" * 78)
    print("DELIVERY SURFACE GATE — absolute, SHA-pinned, size-verified")
    print("=" * 78)
    print(f"document      : {DOC}")
    print(f"links         : {len(rows)}")
    print(f"absolute      : {sum(1 for r in rows if r['absolute'])}")
    print(f"sha-pinned    : {sum(1 for r in rows if r['sha_pinned'])}")
    print(f"declared size : {sum(1 for r in rows if r['declared'] is not None)}")
    if fetch:
        print(f"fetched       : {fetched}")
    for p in problems:
        print(f"  [DEFECT] {p}")
    ok = not problems
    print("\n" + "=" * 78)
    print(f"VERDICT: {'BYTE_CLOSURE' if ok else 'SURFACE_DEFECT'}")
    print("=" * 78)
    return 0 if ok else 1


def selftest() -> int:
    sha = "a" * 40
    good = (f'<a class="dl" href="https://raw.githubusercontent.com/o/r/{sha}/docs/x.txt">'
            f'<span class="sz">7.7 KB</span></a>')
    rel = '<a class="dl" href="docs/x.txt"><span class="sz">1 KB</span></a>'
    branch = ('<a class="dl" href="https://raw.githubusercontent.com/o/r/main/docs/x.txt">'
              '<span class="sz">1 KB</span></a>')
    # a nav anchor is not a delivery surface and must be ignored
    nav = '<a href="#r1">jump</a>' + good
    results = []
    g = scan(good)
    results.append(("silent on pinned link",
                    g[0]["absolute"] and g[0]["sha_pinned"] and g[0]["declared"] == 7885,
                    f"{g}"))
    r = scan(rel)
    results.append(("fires on relative href", not r[0]["absolute"], f"{r[0]['url']}"))
    b = scan(branch)
    results.append(("fires on branch href", not b[0]["sha_pinned"], f"{b[0]['url']}"))
    n = scan(nav)
    results.append(("ignores in-page nav anchors", len(n) == 1, f"{len(n)} row(s)"))
    print("=" * 78)
    print("DELIVERY SURFACE GATE — SELFTEST")
    print("=" * 78)
    holes = 0
    for name, ok, detail in results:
        if not ok:
            holes += 1
        print(f"  [{'PASS' if ok else 'HOLE'}] {name}  {detail}")
    print(f"\nSELFTEST: {'PASS' if holes == 0 else 'FAIL'} ({holes} hole(s))")
    return 0 if holes == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv
             else run(fetch="--fetch" in sys.argv))
