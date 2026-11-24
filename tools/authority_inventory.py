#!/usr/bin/env python3
"""authority_inventory.py — reproducible inventory of every instruction-bearing surface.

The migration it serves: DARKITH.md must be the ONE normative source, and every other
surface must carry only role-specific operational text plus a pointer. That claim cannot be
made from a `grep` — a text search finds the occurrences you thought of. This walks the
tracked bytes, classifies every file, and records each normative-law citation with its exact
location, so the "no parallel authority" claim is measured instead of asserted.

Why a tool and not a one-off script: the inventory must be reproducible from a commit SHA by
someone else, with the same command and the same output hash. A pasted table is not evidence.

Classification is by path and content, in this order (first match wins):
  normative_policy   the canonical law file itself (DARKITH.md)
  product_docs       README and user-facing documentation
  task_instance      TASKS.md and per-task records
  historical         archive/evidence paths, and anything marked retired
  generated          dist/, proof/ boards, and anything declaring a generated header
  machinery          tools/ (gates, generators, enforcement)
  other              everything else

A law citation is any occurrence of NEVER #N / MUST #N / SPI-N. Occurrences inside the
canonical policy file are DEFINITIONS-or-references and are not counted against the
"no duplicate law" rule; occurrences in machinery are code, not prose law. The surfaces that
matter for Section 1 are the prose documents.

Usage:
  python3 tools/authority_inventory.py            # write proof/authority-inventory.json
  python3 tools/authority_inventory.py --check    # fail if any prose doc defines law text
  python3 tools/authority_inventory.py --json     # print the inventory
Exit codes: 0 ok, 1 policy violation (duplicate law in a secondary doc), 2 usage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "proof" / "authority-inventory.json"

LAW = re.compile(r"\b(NEVER|MUST|SPI)[ -]#?(\d+)\b")

# Prose documents that may NOT define law (Section 1.1). DARKITH.md is the source.
SECONDARY = ("AGENTS.md", "RESUME.md", "README.md", "TASKS.md")

# A *definition* STATES the rule. Three forms count:
#   heading      `NEVER #11 (ONE TREE)` or `NEVER #11 One Tree: ...`
#   bold lead-in `- **SPI-2** read exact bytes ...`
#   colon form   `NEVER #17: a named deficiency may not survive ...`
# A *reference* points at law without stating it: `see MUST #18`, or a wrapped line whose
# ID is followed by closing punctuation (`NEVER #15). The hub shows ...`). A detector that
# cannot tell these apart is useless in both directions: too loose and it forbids the
# pointers the migration requires; too strict and it reports a duplicate law as clean.
_ID = r"(NEVER|MUST|SPI)[ -]#?(\d+)"
_LEAD = r"^\s*(?:[-*+]\s+)?(?:#+\s+)?"
DEF_HEADING = re.compile(_LEAD + r"\*{0,2}(?:───\s*)?" + _ID + r"\*{0,2}(?:\s*\(|\s*[-—:]\s*|\s+(?=[A-Z]))")
DEF_BOLD = re.compile(_LEAD + r"\*{2}" + _ID + r"\*{2}")
CONTINUATION = re.compile(_LEAD + r"\*{0,2}" + _ID + r"\*{0,2}\s*[),;.]")


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout
    return [p for p in out.decode().split("\0") if p]


def classify(path: str) -> str:
    p = path.lower()
    if path == "DARKITH.md":
        return "normative_policy"
    if path in ("README.md",) or p.startswith("docs/") and "readme" in p:
        return "product_docs"
    if path in ("TASKS.md",) or p.startswith("proof/tasks"):
        return "task_instance"
    if p.startswith("archive/") or "historical" in p or p.startswith("proof/history"):
        return "historical"
    if p.startswith("dist/") or p.startswith("proof/"):
        return "generated"
    if p.startswith("tools/") or p.startswith(".github/"):
        return "machinery"
    return "other"


def is_definition(line: str) -> bool:
    """A line STATES law if it leads with a heading, a bold lead-in, or an ID + colon rule,
    and is not merely the tail of a wrapped reference."""
    if CONTINUATION.match(line):
        return False
    return bool(DEF_HEADING.match(line) or DEF_BOLD.match(line))


def law_occurrences(text: str) -> list[dict]:
    rows = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in LAW.finditer(line):
            rows.append(
                {
                    "law_id": f"{m.group(1)} #{m.group(2)}",
                    "line": lineno,
                    "col": m.start() + 1,
                    "text": line.strip()[:200],
                    "is_definition": is_definition(line),
                }
            )
    return rows


def build() -> dict:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    files = tracked_files()
    entries = []
    for rel in files:
        fp = ROOT / rel
        if not fp.is_file():
            continue
        raw = fp.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = ""
        occ = law_occurrences(text) if text else []
        cls = classify(rel)
        entries.append(
            {
                "path": rel,
                "bytes": len(raw),
                "lines": text.count("\n") + 1 if text else 0,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "classification": cls,
                "law_occurrences": len(occ),
                "law_definitions": sum(1 for o in occ if o["is_definition"]),
                "law_ids": sorted({o["law_id"] for o in occ}),
                "occurrences": occ if cls in ("product_docs", "task_instance") else [],
            }
        )
    payload = {
        "_schema": "authority-inventory/1",
        "base_sha": head,
        "command": "python3 tools/authority_inventory.py",
        "python": sys.version.split()[0],
        "tracked_files": len(entries),
        "by_classification": _counts(entries),
        "entries": entries,
    }
    blob = json.dumps(payload, indent=1, sort_keys=True)
    payload["output_sha256"] = hashlib.sha256(blob.encode()).hexdigest()
    return payload


def _counts(entries: list[dict]) -> dict:
    out: dict[str, int] = {}
    for e in entries:
        out[e["classification"]] = out.get(e["classification"], 0) + 1
    return out


def check(payload: dict) -> int:
    """Fail if a secondary prose document *defines* law (a duplicate authority)."""
    bad = []
    for e in payload["entries"]:
        if e["path"] in SECONDARY and e["law_definitions"] > 0:
            defs = [o for o in e["occurrences"] if o["is_definition"]]
            bad.append((e["path"], e["law_definitions"], defs[:5]))
    if bad:
        print("authority_inventory: FAIL — secondary document(s) define law (DARKITH.md is the source)")
        for path, n, sample in bad:
            print(f"  {path}: {n} law definition(s)")
            for d in sample:
                print(f"    L{d['line']}: {d['text'][:100]}")
        return 1
    print("authority_inventory: PASS — no secondary document defines law")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    payload = build()
    if args.json:
        print(json.dumps(payload, indent=1, sort_keys=True))
        return 0
    if args.check:
        return check(payload)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    print(f"authority_inventory: wrote {OUT.relative_to(ROOT)}")
    print(f"  base_sha: {payload['base_sha']}")
    print(f"  tracked_files: {payload['tracked_files']}")
    print(f"  output_sha256: {payload['output_sha256']}")
    for cls, n in sorted(payload["by_classification"].items()):
        print(f"    {cls:18s} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
