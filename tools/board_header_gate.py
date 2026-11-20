#!/usr/bin/env python3
"""board_header_gate.py — a generator may not delete a board's title or governance prose.

Why this exists: commit 67ea976 ("regenerate artifacts on the merged tree") removed 340
lines from TASKS.md, including `# TASKS — the durable board` and the whole
`## STANDING-AUTHORITY (NEVER #21)` section. Every gate stayed green because the generator
that replaced the file was itself the thing being trusted, and the prose it destroyed had
no hash anyone checked. The loss surfaced only later, as an authority_gate failure whose
message ("the standing authority is not written down") named the symptom, not the cause.

The class: a file that mixes hand-written governance with a generated block. If the
generator's boundary is wrong — a missing `# ` title means praxis inserts at line 0 and can
push the header out — the hand-written part is destroyed and nothing notices.

This gate pins the parts no generator owns. It checks, for each guarded board:
  - the first line is the board's own `# ` title, unchanged;
  - every required sentinel section heading is present;
  - the hand-written prefix (everything before the first generated marker) has not shrunk
    below its recorded baseline.

Baselines live in `tools/board_header_baseline.json`, are generated on first run with
--write, and are committed, so a shrink is a diff a reviewer can see.

  python3 tools/board_header_gate.py --check
  python3 tools/board_header_gate.py --write   # (re)record baselines after an intended edit

Exit: 0 = intact; 1 = a guarded header was damaged; 2 = could not read a board; 3 = skip.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tools" / "board_header_baseline.json"

# marker -> the generated block it opens. A hand-written prefix ends at the first of these.
MARKERS = ("<!-- PRAXIS:BEGIN", "<!-- CNS:BEGIN", "<!-- AUTOGEN:BEGIN")

# The sentinel is checked as a heading at any level: the CNS generator emits it as `###`
# while the earlier hand-written boards used `##`. Pinning the level would fail a board for
# a cosmetic difference, so the gate pins the token and that it is a heading at all.
SENTINEL = "STANDING-AUTHORITY (NEVER #21)"
SENTINEL_HEADING = re.compile(r"^#{2,4}\s*" + re.escape(SENTINEL), re.M)

GUARDED = {
    "TASKS.md": {
        "title": "# TASKS — the durable board",
        "required": [SENTINEL],
    },
    "AGENTS.md": {"required": [SENTINEL]},
    "RESUME.md": {"required": [SENTINEL]},
}


def prefix_len(text: str) -> int:
    cut = len(text)
    for m in MARKERS:
        i = text.find(m)
        if 0 <= i < cut:
            cut = i
    return cut


def inspect(name: str, spec: dict) -> list[str]:
    p = ROOT / name
    if not p.is_file():
        return [f"{name}: missing"]
    text = p.read_text(encoding="utf-8", errors="replace")
    problems = []

    if "title" in spec:
        first = text.splitlines()[0] if text.splitlines() else ""
        if first != spec["title"]:
            problems.append(f"{name}: title line is {first!r}, expected {spec['title']!r}")

    for req in spec.get("required", []):
        if req == SENTINEL:
            if not SENTINEL_HEADING.search(text):
                problems.append(f"{name}: required heading {req!r} is gone")
        elif req not in text:
            problems.append(f"{name}: required section {req!r} is gone")

    return problems


def fix() -> list[str]:
    """Restore a missing title. Deterministic: prepend the pinned title line."""
    done = []
    for name, spec in GUARDED.items():
        if "title" not in spec:
            continue
        p = ROOT / name
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        first = text.splitlines()[0] if text.splitlines() else ""
        if first != spec["title"]:
            p.write_text(spec["title"] + "\n\n" + text.lstrip("\n"), encoding="utf-8")
            done.append(f"{name}: restored title")
    return done


def load_baseline() -> dict:
    if not BASELINE.is_file():
        return {}
    try:
        return json.loads(BASELINE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def main(argv: list[str]) -> int:
    write = "--write" in argv
    repair = "--fix" in argv

    if repair:
        for line in fix():
            print(f"board_header_gate: FIXED — {line}")

    baseline = load_baseline()
    problems: list[str] = []

    for name, spec in GUARDED.items():
        problems.extend(inspect(name, spec))
        p = ROOT / name
        if p.is_file():
            n = prefix_len(p.read_text(encoding="utf-8", errors="replace"))
            base = baseline.get(name, {}).get("prefix_len")
            if write:
                baseline[name] = {"prefix_len": n}
            elif base is not None and n < base:
                problems.append(
                    f"{name}: hand-written prefix shrank {base} -> {n} chars "
                    f"(a generator ate governance prose)"
                )

    if write:
        BASELINE.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(f"board_header_gate: wrote baselines for {len(baseline)} board(s) -> "
              f"{BASELINE.relative_to(ROOT)}")

    if problems:
        print(f"board_header_gate: FAIL — {len(problems)} damaged header(s):")
        for pr in problems:
            print(f"  - {pr}")
        print("  a generated block must never delete a board's title or governance prose")
        return 1

    print(f"board_header_gate: PASS — {len(GUARDED)} guarded board(s) intact")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
