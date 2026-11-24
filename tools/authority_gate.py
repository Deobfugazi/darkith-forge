#!/usr/bin/env python3
"""Enforce one canonical governance source; never infer publication permission."""
from pathlib import Path
import re, sys
ROOT=Path(__file__).resolve().parent.parent
SECONDARY=("AGENTS.md","TASKS.md","RESUME.md","README.md")
LAW="─── NEVER #21 (NO UNAUTHORIZED PUBLICATION OR PROMOTION) ───"
CNS="## CNS-DIRECTIVE (v1)"
OLD="STANDING-AUTHORITY (NEVER #21)"

def inspect(root=ROOT):
    errors=[]; canon=root/"DARKITH.md"
    if not canon.is_file(): return ["DARKITH.md is missing"]
    text=canon.read_text(encoding="utf-8",errors="replace")
    if text.count(LAW)!=1: errors.append(f"DARKITH.md must declare NEVER #21 exactly once; found {text.count(LAW)}")
    if text.count(CNS)!=1: errors.append(f"DARKITH.md must contain exactly one CNS directive; found {text.count(CNS)}")
    if OLD in text: errors.append("retired standing-authority sentinel remains in DARKITH.md")
    for name in SECONDARY:
        path=root/name
        if not path.is_file(): errors.append(f"{name} is missing"); continue
        body=path.read_text(encoding="utf-8",errors="replace")
        if OLD in body or re.search(r"^## CNS-DIRECTIVE \\(v1\\)",body,re.M):
            errors.append(f"{name} duplicates canonical governance content; replace it with a pointer")
        if re.search(r"^## STANDING-AUTHORITY|^### STANDING-AUTHORITY",body,re.M):
            errors.append(f"{name} contains a standing-publication authority block")
    return errors

def selftest():
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as raw:
        root=Path(raw); (root/"DARKITH.md").write_text(LAW+"\\n\\n"+CNS+"\\n")
        for name in SECONDARY: (root/name).write_text("Pointer to DARKITH.md.\\n")
        if inspect(root): print("authority_gate selftest: FAIL — canonical fixture rejected"); return 1
        (root/"README.md").write_text(CNS+" duplicate\\n")
        if not inspect(root): print("authority_gate selftest: FAIL — duplicate fixture accepted"); return 1
    print("authority_gate selftest: PASS — canonical source accepted; duplicate rejected"); return 0

def main(argv):
    if "--selftest" in argv: return selftest()
    errors=inspect()
    if errors:
        print(f"authority_gate: FAIL — {len(errors)} governance divergence(s)")
        for error in errors: print("  - "+error)
        return 1
    print("authority_gate: PASS — one canonical law source; no copied authority blocks")
    return 0

if __name__=="__main__": sys.exit(main(sys.argv[1:]))
