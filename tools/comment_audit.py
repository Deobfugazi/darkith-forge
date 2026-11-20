#!/usr/bin/env python3
"""Gate: every block comment in every Kotlin file is closed.

This closes the class permanently. It does not re-litigate the 2026-11-10 briefing that
claimed 19 files had lost their opening '/*': that briefing was measured against a stale
fork, the real defect was a mangled CLOSER ('//' where '*/' belonged) in exactly 2 files
(core/CssLite.kt, core/SubstrateIngestor.kt), and both were repaired to byte-identical with
the reconciled tree. Re-raising that premise is what this file used to do, and it cost
every fresh agent a delivery cycle. The bytes are authoritative; the briefing is closed.

Exit 0 = every block comment closed. Exit 1 = defect present, with file and line.
Exit 3 = SKIP, the scan could not run (never report a pass for work not done, SPI-31/32).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kt_comment_scan import scan  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The whole repo, not just the app tree: a defect in omega-app/ or tools/ is the same
# defect, and a gate that scans a subset reports a pass over files it never read.
TREES = ["."]
# Exempt only what cannot hold authored source. 'build' is NOT exempt: it holds real .kt
# files (build/omega/*.kt), and skipping a directory that contains source is a pass over
# files never read.
EXEMPT = {".git", "dist", "proof", "node_modules", ".tools", ".agent_tmp",
          ".forge_work", "__pycache__"}


def kotlin_files(tree):
    out = []
    for dp, dns, fns in os.walk(os.path.join(ROOT, tree)):
        dns[:] = [d for d in dns if d not in EXEMPT]
        if dp.rstrip("/") == os.path.join(ROOT, ".").rstrip("/") or dp == ROOT:
            dns[:] = [d for d in dns if d not in EXEMPT]
        out += [os.path.join(dp, f) for f in fns if f.endswith(".kt")]
    return sorted(out)


def main():
    files = []
    for t in TREES:
        files += kotlin_files(t)
    if not files:
        print("comment_audit: SKIP - 0 .kt files found under "
              + ", ".join(TREES) + "; nothing examined, so nothing is proven")
        return 3

    defects = []
    for p in files:
        with open(p, encoding="utf-8", errors="surrogateescape") as fh:
            err = scan(fh.read())
        if err:
            defects.append((os.path.relpath(p, ROOT), err))

    if defects:
        print(f"comment_audit: FAIL - {len(defects)} unclosed block comment(s) in "
              f"{len(files)} file(s):")
        for path, err in defects:
            print(f"  {path}: {err}")
        return 1

    print(f"comment_audit: PASS - {len(files)} .kt files, every block comment closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
