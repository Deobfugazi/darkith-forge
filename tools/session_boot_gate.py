#!/usr/bin/env python3
"""Fail CI if the mandatory fresh-session boot protocol is missing or buried."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MARKER = "## SESSION BOOT — EXECUTE BEFORE ANY TASK (MANDATORY)"
REQUIRED = (
    "bash tools/restore.sh",
    "Read the COMPLETE contents",
    "python3 tools/autophagy.py",
    "python3 tools/revitalization.py selftest",
    "bash tools/ci.sh",
)

def main() -> int:
    failures = []
    for name in ("AGENTS.md", "RESUME.md"):
        path = ROOT / name
        if not path.is_file():
            failures.append(f"{name}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if MARKER not in lines[:8]:
            failures.append(f"{name}: boot marker is not in the first 8 lines")
        marker_at = text.find(MARKER)
        boot = text[marker_at:marker_at + 2400] if marker_at >= 0 else ""
        for item in REQUIRED:
            if item not in boot:
                failures.append(f"{name}: boot block omits {item!r}")
    if failures:
        print("SESSION BOOT GATE: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("SESSION BOOT GATE: PASS — mandatory formulary is front-loaded in AGENTS.md and RESUME.md")
    return 0

if __name__ == "__main__":
    sys.exit(main())
