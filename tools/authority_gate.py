#!/usr/bin/env python3
"""Enforce a single canonical law source and reject implicit publication paths."""
from __future__ import annotations
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
SECONDARY = ("AGENTS.md", "TASKS.md", "README.md", "RESUME.md")
LAW21 = re.compile(r"^───\s*NEVER\s*#21\b", re.M)
CNS = re.compile(r"^## CNS-DIRECTIVE \(v1\)\b", re.M)
LAW_DECL = re.compile(r"^\s*───\s*(?:NEVER|MUST|SPI)\s*-?\s*#?\s*\d+\b", re.M)
STANDING = re.compile(r"^#{1,4}\s*STANDING-AUTHORITY\b", re.M)
BLANKET = re.compile(r"Agents publish without asking|standing authority to publish|never ask to push|with no approval|pre-authori[sz]ed.{0,40}push", re.I)
GENERATED_PREFIXES = ("proof/", "delivery/", "dl/")
GENERATED_SUFFIXES = (".pyc",)

def is_generated(path: str) -> bool:
    return (path.startswith(GENERATED_PREFIXES) or path.endswith(GENERATED_SUFFIXES)
            or "__pycache__/" in path)

def inspect(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    canonical = root / "DARKITH.md"
    if not canonical.is_file():
        return ["DARKITH.md is missing"]
    law = canonical.read_text(encoding="utf-8", errors="replace")
    if len(LAW21.findall(law)) != 1:
        errors.append(f"DARKITH.md must declare NEVER #21 exactly once; found {len(LAW21.findall(law))}")
    if len(CNS.findall(law)) != 1:
        errors.append(f"DARKITH.md must contain exactly one canonical CNS directive; found {len(CNS.findall(law))}")
    for name in SECONDARY:
        path = root / name
        if not path.is_file():
            errors.append(f"{name} is missing")
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        if CNS.search(body):
            errors.append(f"{name} contains a copied CNS directive")
        if LAW_DECL.search(body):
            errors.append(f"{name} declares a law outside DARKITH.md")
        if STANDING.search(body):
            errors.append(f"{name} contains a duplicate standing-authority block")
        if BLANKET.search(body):
            errors.append(f"{name} grants blanket publication authority")
    pulse = root / "tools" / "board_pulse.sh"
    if pulse.is_file() and re.search(r"^\s*git\s+push\b", pulse.read_text(errors="replace"), re.M):
        errors.append("board_pulse.sh contains a remote push")
    drift = root / "tools" / "drift_gate.py"
    if drift.is_file() and re.search(r'git\(\["push"', drift.read_text(errors="replace")):
        errors.append("drift_gate.py contains an automatic remote push")
    return errors

def selftest() -> int:
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "tools").mkdir()
        (root / "DARKITH.md").write_text(
            "─── NEVER #21 (NO UNAUTHORIZED PUBLICATION OR PROMOTION) ───\n"
            "## CNS-DIRECTIVE (v1)\nCanonical law.\n")
        for name in SECONDARY:
            (root / name).write_text("Read DARKITH.md for binding laws.\n")
        if inspect(root):
            print("authority_gate selftest: FAIL — clean single-source fixture rejected")
            return 1
        (root / "README.md").write_text(
            "## STANDING-AUTHORITY (NEVER #21)\nAgents publish without asking.\n")
        if not inspect(root):
            print("authority_gate selftest: FAIL — duplicate authority accepted")
            return 1
    print("authority_gate selftest: PASS — canonical source accepted; duplicate authority rejected")
    return 0

def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    errors = inspect()
    if errors:
        print(f"authority_gate: FAIL — {len(errors)} governance divergence(s)")
        for error in errors:
            print("  - " + error)
        return 1
    print("authority_gate: PASS — one law source; no copied authority or implicit push helper")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
