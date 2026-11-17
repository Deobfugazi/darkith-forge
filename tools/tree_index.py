#!/usr/bin/env python3
"""tree_index.py — emit an addressable coordinate index of a Kotlin source tree.

Why this exists: a tree you cannot enumerate is a tree you cannot account for. This walks
a source root and prints, for every .kt file, the exact coordinates you need to point at
any piece of it:

  file            path relative to the root
  tier            the package tier (dir-derived), e.g. "app" or "core"
  package         the `package` line, verbatim
  decl            every top-level declaration: kind, name, and the line it starts on
  ext             the external namespaces it imports (android.*, java.*, kotlin.*, ...)
  deps            other in-tree packages it references

It is stdlib-only and deterministic: same tree in, same bytes out, so two runs can be
diffed and any drift is visible. It never guesses — it reads the file and reports.

Usage:
  python3 tools/tree_index.py <root> [--json out.json] [--tsv out.tsv]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

# A top-level declaration starts at column 0 (no leading whitespace) in Kotlin.
RE_DECL = re.compile(
    r"^(?:@\w+[^\n]*\n\s*)*"                      # (loose) leading annotations
    r"(public|internal|private|protected|open|abstract|sealed|data|enum|annotation|value|inline)?\s*"
    r"(class|interface|object|fun|val|var|typealias)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)"
)
RE_PACKAGE = re.compile(r"^package\s+([\w.]+)\s*$")
RE_IMPORT = re.compile(r"^import\s+([\w.]+)(?:\.\*)?\s*$")
RE_MOD = re.compile(r"^\s*(?:public|internal|private|protected|open|abstract|sealed|data|enum|annotation|inline|operator|infix|suspend|tailrec|external|const|lateinit|override|final|actual|expect)\s+")


def tier_of(rel_parts: list[str], root_name: str) -> str:
    """Best-effort tier label: the path segment just under the package root.

    src/main/java/com/darkith/transliaison/core/X.kt -> "core"
    src/main/java/com/darkith/transliaison/X.kt      -> "(app)"
    """
    for marker in ("java", "kotlin"):
        if marker in rel_parts:
            i = rel_parts.index(marker)
            tail = rel_parts[i + 1:-1]        # drop the file name
            # the first three segments are the package (com/darkith/transliaison)
            extra = tail[3:] if len(tail) > 3 else []
            return extra[-1] if extra else "(app)"
    # no src/main/java marker: use the deepest directory name
    return rel_parts[-2] if len(rel_parts) > 1 else "(root)"


def strip_comments(lines: list[str]):
    """Blank out comments so declarations are not matched inside them.

    This is a scanner, not a parser (W-023: only kotlinc is authoritative). It tracks
    string and char literals so that a marker inside a string -- e.g. type = "*/*" --
    is NOT mistaken for a comment. Kotlin block comments nest, so depth is counted.
    Returns (lines, unterminated) where unterminated is True if a block comment is
    still open at EOF.
    """
    out = []
    depth = 0
    in_str = False      # "..."
    in_char = False     # '...'
    raw = 0             # """ raw string
    for ln in lines:
        buf = []
        i = 0
        n = len(ln)
        while i < n:
            c = ln[i]
            two = ln[i:i + 2]
            three = ln[i:i + 3]

            if raw:
                if three == '"""':
                    buf.append('"""')
                    raw -= 1
                    i += 3
                    continue
                buf.append(" ")
                i += 1
                continue
            if in_str:
                if c == "\\":
                    buf.append("  ")
                    i += 2
                    continue
                buf.append(" " if c != '"' else '"')
                if c == '"':
                    in_str = False
                i += 1
                continue
            if in_char:
                if c == "\\":
                    buf.append("  ")
                    i += 2
                    continue
                buf.append(" " if c != "'" else "'")
                if c == "'":
                    in_char = False
                i += 1
                continue

            # not inside any literal
            if three == '"""':
                buf.append('"""')
                raw += 1
                i += 3
                continue
            if depth:
                if two == "/*":
                    depth += 1
                    buf.append("  ")
                    i += 2
                    continue
                if two == "*/":
                    depth -= 1
                    buf.append("  ")
                    i += 2
                    continue
                buf.append(" ")
                i += 1
                continue
            if two == "/*":
                depth += 1
                buf.append("  ")
                i += 2
                continue
            if two == "//":
                buf.append(" " * (n - i))
                break
            if c == '"':
                in_str = True
                buf.append(c)
                i += 1
                continue
            if c == "'":
                in_char = True
                buf.append(c)
                i += 1
                continue
            buf.append(c)
            i += 1
        out.append("".join(buf))
    return out, depth > 0


def index_file(path: pathlib.Path, root: pathlib.Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    raw_lines = text.splitlines()
    lines, unterminated = strip_comments(raw_lines)
    rel = path.relative_to(root)
    package = None
    imports = []
    decls = []
    for i, ln in enumerate(lines, 1):
        m = RE_PACKAGE.match(ln.strip()) if package is None else None
        if m:
            package = m.group(1)
            continue
        mi = RE_IMPORT.match(ln.strip())
        if mi:
            imports.append(mi.group(1))
            continue
        md = RE_DECL.match(ln)
        if md:
            kind = md.group(2)
            name = md.group(3)
            decls.append({"kind": kind, "name": name, "line": i})
    return {
        "file": str(rel),
        "tier": tier_of(list(rel.parts), root.name),
        "package": package,
        "loc": len(raw_lines),
        "unterminated_block_comment": unterminated,
        "decls": decls,
        "imports": imports,
    }


def summarize(entry):
    ext = {}
    for imp in entry["imports"]:
        root_ns = imp.split(".")[0]
        ext[root_ns] = ext.get(root_ns, 0) + 1
    entry["ext"] = dict(sorted(ext.items()))
    in_tree = {}
    for imp in entry["imports"]:
        if imp.startswith("com.darkith."):
            parts = imp.split(".")
            pkg = ".".join(parts[:4]) if len(parts) >= 4 else imp
            in_tree[pkg] = in_tree.get(pkg, 0) + 1
    entry["deps"] = dict(sorted(in_tree.items()))
    return entry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=pathlib.Path)
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--tsv", type=pathlib.Path)
    args = ap.parse_args()

    root = args.root.resolve()
    files = sorted(root.rglob("*.kt"))
    entries = [summarize(index_file(p, root)) for p in files]

    # ── human report ──
    print(f"TREE INDEX  root={root}")
    print(f"  files: {len(entries)}")
    tiers = {}
    for e in entries:
        tiers[e["tier"]] = tiers.get(e["tier"], 0) + 1
    print(f"  tiers: {', '.join(f'{k}={v}' for k, v in sorted(tiers.items()))}")
    ns = {}
    for e in entries:
        for k, v in e["ext"].items():
            ns[k] = ns.get(k, 0) + v
    print(f"  external namespaces: {', '.join(f'{k}={v}' for k, v in sorted(ns.items()))}")
    unterminated = [e["file"] for e in entries if e["unterminated_block_comment"]]
    print(f"  unterminated block comments: {len(unterminated)}"
          + (f" -> {unterminated}" if unterminated else ""))
    print()
    for e in entries:
        print(f"  {e['file']}")
        print(f"    tier={e['tier']}  package={e['package']}  loc={e['loc']}")
        for d in e["decls"]:
            print(f"      L{d['line']:<5} {d['kind']:<10} {d['name']}")
        if e["ext"]:
            print(f"      ext: {e['ext']}")

    if args.json:
        args.json.write_text(json.dumps(entries, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nwrote {args.json}")
    if args.tsv:
        rows = ["file\ttier\tpackage\tkind\tname\tline"]
        for e in entries:
            for d in e["decls"]:
                rows.append(f"{e['file']}\t{e['tier']}\t{e['package']}\t{d['kind']}\t{d['name']}\t{d['line']}")
        args.tsv.write_text("\n".join(rows) + "\n", encoding="utf-8")
        print(f"wrote {args.tsv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
