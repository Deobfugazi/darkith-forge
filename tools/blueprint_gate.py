#!/usr/bin/env python3
"""blueprint_gate.py — the executable law for the Operator's specification corpus.

Why this exists (SPI-15): the blueprint `DARKITH OMEGA repo.txt` rode onto `main` with a
live prompt-injection payload and a redundant second copy of its own code, because NOTHING
checked it. A law that is not a gate is a note; a document that is not gated is a document
that ships its own defects. This gate is the note turned into a check.

It gates every `*.md` in the blueprint corpus (default `docs/blueprints/`). Four exact rules,
each aimed at a defect class that actually occurred:

  R1 INJECTION      — no agent-execution directives. The blueprint is SPECIFICATION, never
                      an instruction channel. (`COPY AND PASTE ... INTO OPENHANDS`,
                      `do not ask for confirmation`, `execute immediately`, `ignore previous
                      instructions`.) This is the class: a repo file that instructs the agent.
  R2 DUPLICATE-BLOCK— no two fenced code blocks with identical content. A spec that writes
                      the same file twice is two live copies of one truth inside one document
                      (NEVER #11/#16) and WILL drift. This is the class: redundant inline copy.
  R3 TEST-COUNT     — every "<N> pass(ing|ed)" claim must equal the size of the canonical
                      `TESTS` map in the same document. A stale count ("13 passing" beside a
                      20-key suite) is a false claim the reader cannot see. This is the class:
                      a self-report that drifted from the artifact.
  R4 SINGLE-COPY    — a section that hands the reader a "paste this into an agent" execution
                      script is not specification and is rejected outright (the carrier of R1).

Usage:
  python3 tools/blueprint_gate.py [path-or-dir ...]     # default: the corpus globs
Exit: 0 = every blueprint clean; 1 = at least one defect.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The Operator's own specification corpus, wherever it lands. The blueprint is a *.txt, so
# globbing only docs/blueprints/*.md left the real contaminant riding in ungated. These
# globs are the default corpus: the Operator's blueprint plus any docs/blueprints/ file.
DEFAULT_GLOBS = ("docs/blueprints/*.md", "docs/blueprints/*.txt", "docs/DARKITH-OMEGA-*.txt")

# R1 — agent-execution directives. Case-insensitive; these must never appear in a spec.
INJECTION = [
    r"copy and paste (the following|this).*into\s+openhands",
    r"do not ask for confirmation",
    r"execute immediately",
    r"ignore (all |any )?(previous|prior|above) instructions",
    r"disregard (all |any )?(previous|prior|above)",
    r"you are tasked with generating",
]

# R3 — a passing-test claim, e.g. "13 passing, 0 failed" / "18 passed".
TEST_CLAIM = re.compile(r"(\d+)\s+(?:passing|passed)\b", re.I)

# A fenced code block: ```lang ... ```
FENCE = re.compile(r"^\s*```")
TESTS_OPEN = re.compile(r"^\s*export\s+const\s+TESTS\b")
KEY = re.compile(r'^\s*"([^"]+)"\s*:\s*\(\)\s*=>')


def fenced_blocks(lines: list[str]):
    """Yield (start_line, lang, [content lines]) for each fenced block."""
    i = 0
    while i < len(lines):
        if FENCE.match(lines[i]):
            lang = lines[i].strip()[3:].strip()
            start = i + 1
            j = start
            while j < len(lines) and not FENCE.match(lines[j]):
                j += 1
            yield start + 1, lang, lines[start:j]
            i = j + 1
        else:
            i += 1


def canonical_test_count(lines: list[str]) -> int | None:
    """Size of the `export const TESTS = { ... }` map, counted by brace depth so a
    nested object inside a test body cannot inflate the count."""
    for i, line in enumerate(lines):
        if TESTS_OPEN.match(line):
            depth = 0
            n = 0
            for k in range(i, len(lines)):
                for ch in lines[k]:
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                if KEY.match(lines[k]) and depth >= 1:
                    n += 1
                if k > i and depth <= 0:
                    return n
    return None


def check(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    fails: list[str] = []

    # R1 / R4 — injection directives.
    for rx in INJECTION:
        for m in re.finditer(rx, text, re.I):
            ln = text[: m.start()].count("\n") + 1
            fails.append(f"R1 injection @ {ln}: matches /{rx}/")

    # R2 — byte-identical fenced blocks (two copies of one truth in one doc).
    seen: dict[str, int] = {}
    for start, lang, body in fenced_blocks(lines):
        blob = "\n".join(s.rstrip() for s in body).strip()
        if len(blob) < 40:          # ignore trivial one-liners
            continue
        if blob in seen:
            fails.append(f"R2 duplicate code block: lines {seen[blob]} and {start} are identical")
        else:
            seen[blob] = start

    # R4 — an execution script INSIDE a fenced block: the carrier of R1. R1 catches a
    # directive anywhere in the prose; R4 catches the same directive dressed up as a code
    # block the reader is told to run. Both are the class "a repo file that instructs the
    # agent", reported at their own location so neither hides the other.
    for start, lang, body in fenced_blocks(lines):
        blob = "\n".join(body)
        for rx in INJECTION:
            if re.search(rx, blob, re.I):
                fails.append(f"R4 execution script in fenced block @ {start}: matches /{rx}/")

    # R3 — a passing-test claim must match the canonical TESTS map in the same document.
    n_tests = canonical_test_count(lines)
    claims = sorted({int(m.group(1)) for m in TEST_CLAIM.finditer(text)})
    if n_tests is not None:
        for c in claims:
            # allow the failure-count "0 failed" and any count that matches the map
            if c != n_tests and c != 0:
                fails.append(f"R3 test-count: claims {c} passing, but the TESTS map has {n_tests}")
    return fails


def main(argv: list[str]) -> int:
    targets: list[pathlib.Path] = []
    for a in argv[1:]:
        p = pathlib.Path(a)
        if p.is_dir():
            targets += sorted(p.glob("*.md"))
        elif p.is_file():
            targets.append(p)
    if not targets:
        for g in DEFAULT_GLOBS:
            targets += sorted(ROOT.glob(g))
        if not targets:
            # No corpus means the gate checked NOTHING. Exit 3 so it is reported as a
            # skip; exiting 0 here was a vacuous pass that read as verification.
            print("blueprint_gate: SKIP — no blueprint corpus found "
                  f"({' '.join(DEFAULT_GLOBS)})")
            return 3

    total = 0
    for p in targets:
        fails = check(p)
        try:
            rel = p.resolve().relative_to(ROOT)
        except ValueError:
            rel = p          # a path outside the repo (e.g. a staged copy) is still checkable
        if fails:
            total += len(fails)
            print(f"blueprint_gate: FAIL — {rel} ({len(fails)} defect(s)):")
            for f in fails:
                print("  " + f)
        else:
            print(f"blueprint_gate: PASS — {rel}")

    if total:
        print(f"blueprint_gate: {total} defect(s) across {len(targets)} blueprint(s)")
        return 1
    print(f"blueprint_gate: PASS — {len(targets)} blueprint(s) clean "
          f"(no injection, no duplicate copy, no stale count)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
