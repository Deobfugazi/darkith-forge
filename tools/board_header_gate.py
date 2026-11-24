#!/usr/bin/env python3
"""Protect generated board titles and boundaries without requiring duplicated law blocks."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tools" / "board_header_baseline.json"
MARKERS = ("<!-- PRAXIS:BEGIN", "<!-- CNS:BEGIN", "<!-- AUTOGEN:BEGIN")
GUARDED = {"TASKS.md": {"title": "# TASKS — the durable board"}}

def prefix_len(text: str) -> int:
    cut = len(text)
    for marker in MARKERS:
        index = text.find(marker)
        if 0 <= index < cut:
            cut = index
    return cut

def inspect(name: str, spec: dict) -> list[str]:
    path = ROOT / name
    if not path.is_file():
        return [f"{name}: missing"]
    text = path.read_text(encoding="utf-8", errors="replace")
    first = text.splitlines()[0] if text.splitlines() else ""
    if "title" in spec and first != spec["title"]:
        return [f"{name}: title is {first!r}, expected {spec['title']!r}"]
    return []

def load_baseline() -> dict:
    try:
        return json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.is_file() else {}
    except (OSError, json.JSONDecodeError):
        return {}

def main(argv: list[str]) -> int:
    baseline = load_baseline()
    problems = []
    for name, spec in GUARDED.items():
        problems.extend(inspect(name, spec))
        path = ROOT / name
        if not path.is_file():
            continue
        size = prefix_len(path.read_text(encoding="utf-8", errors="replace"))
        if "--write" in argv:
            baseline[name] = {"prefix_len": size}
        elif name in baseline and size < baseline[name].get("prefix_len", 0):
            problems.append(f"{name}: generated-boundary prefix shrank "
                            f"{baseline[name]['prefix_len']} -> {size}")
    if "--write" in argv:
        BASELINE.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    if problems:
        print(f"board_header_gate: FAIL — {len(problems)} board invariant(s)")
        for problem in problems:
            print("  - " + problem)
        return 1
    print("board_header_gate: PASS — durable board title and generated boundary intact")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
