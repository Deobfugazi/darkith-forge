#!/usr/bin/env python3
"""kotlin_comment_repair.py — detect, repair, and PROVE the `sed`-stripped opener defect.

The defect: a blind `sed` removed the opening `/*` from a block comment. The file then has a
`*/` with no opener, and Kotlin reports "Unclosed comment" — or, worse, swallows the rest of
the file. `tools/syntax_gate.py` detects it. Detection alone leaves the repair unproven, and a
repair nobody rehearsed is a guess (SPI-2: read the exact bytes, do not guess).

This tool closes the loop in one pass over a COPY of the tree:
  strip   remove `/*` at each stated line   -> gate MUST fail
  restore re-inject `/*` at each stated line -> gate MUST pass
  diff    compare against the pristine tree  -> MUST be byte-identical

If the restored copy is byte-identical to the original, the repair is not a plausible fix: it
is the inverse of the damage, exactly. Anything less and this tool exits non-zero.

Usage:
  python3 tools/kotlin_comment_repair.py --selftest          # build a synthetic case
  python3 tools/kotlin_comment_repair.py --rehearse <pristine-tree> <table.json>
"""
from __future__ import annotations

import filecmp
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kt_comment_scan import scan  # noqa: E402  (the canonical lexer, SPI-27)


def indent_of(s: str) -> int:
    """Count leading spaces/tabs only.

    str.lstrip() also strips '\\n', which pushes an injected marker past the line break when
    the line held nothing but the opener. That bug produced two corrupted files in the first
    rehearsal of this very tool; the byte-identity check is what caught it.
    """
    n = 0
    for ch in s:
        if ch in " \t":
            n += 1
        else:
            break
    return n


def strip_openers(root: pathlib.Path, table: dict[str, int]) -> int:
    files = {p.name: p for p in root.rglob("*.kt")}
    done = 0
    for name, line in table.items():
        p = files.get(name)
        if p is None:
            continue
        lines = p.read_text().splitlines(keepends=True)
        if line - 1 >= len(lines):
            continue
        s = lines[line - 1]
        i = indent_of(s)
        # Only the sed fingerprint: the opener is the first thing on the line and is not
        # followed by a space. `/** ... */` and a bare `/*` both qualify. A `/* text` line
        # does NOT: stripping it leaves a leading space, and no blind restore can tell that
        # space from the indent, so the repair would be a guess. Refuse it instead.
        if s[i:i + 2] != "/*" or s[i + 2:i + 3] == " ":
            continue
        lines[line - 1] = s[:i] + s[i + 2:]
        p.write_text("".join(lines))
        done += 1
    return done


def restore_openers(root: pathlib.Path, table: dict[str, int]) -> int:
    files = {p.name: p for p in root.rglob("*.kt")}
    done = 0
    for name, line in table.items():
        p = files.get(name)
        if p is None:
            continue
        lines = p.read_text().splitlines(keepends=True)
        if line - 1 >= len(lines):
            continue
        s = lines[line - 1]
        i = indent_of(s)
        if s[i:i + 2] == "/*":
            continue
        lines[line - 1] = s[:i] + "/*" + s[i:]
        p.write_text("".join(lines))
        done += 1
    return done


def defects(root: pathlib.Path) -> int:
    n = 0
    for p in root.rglob("*.kt"):
        n += sum(1 for k, _, _ in scan(p.read_text(errors="replace"))
                 if k in ("UNCLOSED", "ORPHAN_CLOSE"))
    return n


def trees_identical(a: pathlib.Path, b: pathlib.Path) -> list[str]:
    diffs = []
    for p in sorted(a.rglob("*.kt")):
        q = b / p.relative_to(a)
        if not q.exists() or not filecmp.cmp(p, q, shallow=False):
            diffs.append(str(p.relative_to(a)))
    return diffs


def rehearse(pristine: pathlib.Path, table: dict[str, int]) -> int:
    work = pathlib.Path(tempfile.mkdtemp(prefix="kt-rehearse-"))
    try:
        shutil.copytree(pristine, work / "tree")
        t = work / "tree"
        print(f"  pristine: {pristine}  ({len(list(t.rglob('*.kt')))} .kt)")
        if defects(t):
            print("  REFUSED: the pristine tree is already damaged; cannot rehearse from it")
            return 1
        stripped = strip_openers(t, table)
        if stripped == 0:
            # A run that removed nothing proves nothing. Reporting PASS here is the vacuous
            # pass (SPI-31): the gate ran, the tree was untouched, and the verdict is green.
            print("  FAIL: 0 openers matched — the table did not bind to this tree. "
                  "A rehearsal that damages nothing proves nothing.")
            return 1
        dmg = defects(t)
        print(f"  strip:   {stripped} opener(s) removed -> {dmg} defect(s)")
        if dmg < stripped:
            print(f"  FAIL: the lexer saw {dmg} defects for {stripped} removals — a blind spot")
            return 1
        restored = restore_openers(t, table)
        if restored != stripped:
            print(f"  FAIL: stripped {stripped} but restored {restored} — not an inverse")
            return 1
        left = defects(t)
        print(f"  restore: {restored} opener(s) re-injected -> {left} defect(s) remaining")
        if left:
            print("  FAIL: repair left the tree damaged")
            return 1
        diffs = trees_identical(pristine, t)
        if diffs:
            print(f"  FAIL: not byte-identical to pristine ({len(diffs)} file(s)):")
            for d in diffs[:10]:
                print(f"    {d}")
            return 1
        print("  PASS: byte-identical to pristine — the repair is the exact inverse")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


def selftest() -> int:
    work = pathlib.Path(tempfile.mkdtemp(prefix="kt-selftest-"))
    try:
        tree = work / "t"
        tree.mkdir()
        # the shape that broke the first rehearsal: an opener alone on its own line
        (tree / "A.kt").write_text("package a\n\nclass A {\n    /*\n     * doc\n     */\n}\n")
        # a one-liner opener: the character after `/*` is `*`, so the strip is unambiguous
        (tree / "B.kt").write_text("package b\n\n/** One-liner doc. */\nclass B\n")
        table = {"A.kt": 4, "B.kt": 3}
        checks = []
        checks.append(("pristine is clean", defects(tree) == 0, ""))
        strip_openers(tree, table)
        checks.append(("strip creates 2 defects", defects(tree) == 2, f"{defects(tree)}"))
        restore_openers(tree, table)
        checks.append(("restore clears them", defects(tree) == 0, f"{defects(tree)}"))
        orig = work / "orig"
        orig.mkdir()
        (orig / "A.kt").write_text("package a\n\nclass A {\n    /*\n     * doc\n     */\n}\n")
        (orig / "B.kt").write_text("package b\n\n/** One-liner doc. */\nclass B\n")
        checks.append(("restore is byte-exact", trees_identical(orig, tree) == [], ""))
        # the lstrip bug must be caught, not repeated
        bad = "    \n"
        checks.append(("indent_of survives a bare-newline line", indent_of(bad) == 4, ""))
        # a `/* text` opener is refused rather than guessed at
        amb = work / "amb"
        amb.mkdir()
        (amb / "C.kt").write_text("package c\n\n/* text */\n")
        skipped = strip_openers(amb, {"C.kt": 3})
        checks.append(("ambiguous `/* text` opener is refused", skipped == 0, f"{skipped}"))

        print("=" * 78)
        print("KOTLIN COMMENT REPAIR — SELFTEST")
        print("=" * 78)
        holes = 0
        for name, ok, detail in checks:
            holes += not ok
            print(f"  [{'PASS' if ok else 'HOLE'}] {name}  {detail}")
        print(f"\nSELFTEST: {'PASS' if holes == 0 else 'FAIL'} ({holes} hole(s))")
        return 0 if holes == 0 else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    if "--rehearse" in argv:
        i = argv.index("--rehearse")
        try:
            pristine = pathlib.Path(argv[i + 1])
            raw = json.loads(pathlib.Path(argv[i + 2]).read_text())
            table = raw.get("files", raw) if isinstance(raw, dict) else raw
        except (IndexError, OSError, json.JSONDecodeError) as exc:
            print(f"usage: --rehearse <pristine-tree> <table.json>  ({exc})", file=sys.stderr)
            return 2
        return rehearse(pristine, table)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
