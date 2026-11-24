#!/usr/bin/env python3
"""Fail CI if the fresh-session formulary is not on AGENTS.md's first screen."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
agents = root / "AGENTS.md"
if not agents.is_file():
    print("SESSION BOOT FAIL: AGENTS.md is missing")
    raise SystemExit(1)
text = agents.read_text(encoding="utf-8")
first = "\n".join(text.splitlines()[:38])
required = (
    "## SESSION BOOT — MANDATORY, BEFORE ANY TASK",
    "bash tools/restore.sh",
    "python3 tools/autophagy.py",
    "python3 tools/revitalization.py selftest",
    "bash tools/ci.sh",
    "detection != repair",
)
missing = [item for item in required if item not in first]
if missing:
    print("SESSION BOOT FAIL: mandatory formulary is absent from AGENTS.md first screen")
    for item in missing:
        print(f"  missing: {item}")
    raise SystemExit(1)
print("SESSION BOOT PASS: fresh agents are directed to restore, heal to fixed point, self-test, verify, and preserve closure distinctions before task work")
