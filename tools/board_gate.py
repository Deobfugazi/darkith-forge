#!/usr/bin/env python3
"""Fail if the durable board (TASKS.md) rots: a `done` row with no evidence, or a row whose
cited evidence path does not exist.

Why this exists: the in-session task tracker is per-conversation and wiped with the VM, so a
task list that is not a tracked, gated file is not durable — it vanished once already and the
omega vision with it (see TASKS.md header). This gate makes the board as binding as any other
law: an item marked done must carry a checkable artifact.

Rule (deliberately simple and exact):
  - TASKS.md must exist;
  - every markdown table row with a status cell of `done` must have a non-empty evidence cell;
  - a `todo`/`in_progress`/`blocked` row may have any evidence;
  - any evidence cell that looks like a repo path (`word/word...`) must resolve on disk.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOARD = ROOT / "TASKS.md"
STATUSES = {"done", "in_progress", "todo", "blocked"}
REPO_ROOTS = {"app", "tools", "build", "libs", "docs", "proof", "delivery", ".github", ".tools"}
# Generated output trees: regenerable, gitignored (see .gitignore). Evidence may cite a
# path here (e.g. a built APK) because it IS checkable after a build, but it is never in a
# fresh checkout, so a `done` row must not fail merely because the artifact is unbuilt.
GENERATED_ROOTS = {"delivery", "dl"}


def tracked_set() -> set[str]:
    """Paths git actually publishes. A generated artifact that is not tracked is expected
    to be absent in a fresh checkout, so its absence must never fail the board."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                             capture_output=True, text=True, check=True).stdout
        return set(out.split())
    except Exception:
        return set()


def cells(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def main() -> int:
    if not BOARD.is_file():
        print("board_gate: FAIL — no TASKS.md (the durable board is missing)")
        return 1

    fails = []
    rows = 0
    TRACKED = tracked_set()
    for i, line in enumerate(BOARD.read_text(encoding="utf-8").splitlines(), 1):
        if not line.lstrip().startswith("|") or set(line) <= set("|-: "):
            continue
        c = cells(line)
        if len(c) < 4 or c[2] not in STATUSES:
            continue
        rows += 1
        status, evidence = c[2], c[3]
        if status == "done" and (not evidence or evidence in {"-", "—"}):
            fails.append(f"TASKS.md:{i}: '{c[1][:40]}' is done with no evidence")
        for m in re.finditer(r"\b[\w.-]+/[\w./-]+\b", evidence):
            tok = m.group(0).rstrip(".,;:")
            # Only repo-relative paths are checkable here. Skip absolute paths, URLs,
            # and device/OS paths (`/proc/...`, `/sdcard/...`, `file:///...`).
            if tok.startswith(("/", "http", "file:")) or tok.split("/", 1)[0] not in REPO_ROOTS:
                continue
            # Generated output trees (delivery/, dl/) hold gitignored build artifacts,
            # so a fresh checkout legitimately has none. Judge such a path only when it is
            # TRACKED (a committed artifact that moved is a real deficit); an untracked
            # build output is never a failure — otherwise building one artifact would
            # red-light every other unbuilt one.
            if tok.split("/", 1)[0] in GENERATED_ROOTS and tok not in TRACKED:
                continue
            if not (ROOT / tok).exists():
                fails.append(f"TASKS.md:{i}: evidence path does not resolve: {tok}")

    if fails:
        print(f"board_gate: FAIL — {len(fails)} problem(s):")
        for f in fails:
            print("  " + f)
        return 1
    print(f"board_gate: PASS — {rows} board row(s); every done item carries evidence")
    return 0


if __name__ == "__main__":
    sys.exit(main())
