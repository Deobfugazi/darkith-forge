#!/usr/bin/env python3
"""Measure local uncommitted-work dwell only (DARKITH.md MUST #36)."""
from __future__ import annotations
import json, pathlib, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parent.parent
CONFIG=ROOT/"STALL_BUDGET.json"
PROOF=ROOT/"proof"/"stall_clock.json"

def git(*args):
    return subprocess.run(["git",*args],cwd=ROOT,capture_output=True,text=True)

def main(argv):
    try:
        cfg=json.loads(CONFIG.read_text(encoding="utf-8"))
        budget=cfg.get("dirty_seconds")
        if not isinstance(budget,int) or budget<=0: raise ValueError("dirty_seconds must be a positive integer")
    except Exception as exc:
        print(f"stall_clock: FAIL — invalid STALL_BUDGET.json: {exc}"); return 1
    status=git("status","--porcelain")
    if status.returncode:
        print("stall_clock: FAIL — git status unavailable"); return 1
    now=int(time.time()); dirty=[]
    for line in status.stdout.splitlines():
        if not line: continue
        path=line[3:].strip().strip('"')
        if " -> " in path: path=path.split(" -> ",1)[1].strip().strip('"')
        target=ROOT/path
        if target.is_file(): dirty.append({"path":path,"mtime":int(target.stat().st_mtime)})
    oldest=min(dirty,key=lambda row:row["mtime"]) if dirty else None
    dwell=now-oldest["mtime"] if oldest else 0
    breaches=[f"uncommitted local work dwell {dwell}s exceeds {budget}s ({len(dirty)} path(s))"] if dirty and dwell>budget else []
    record={"verdict":"FAIL" if breaches else "PASS","measured_at":now,"dirty":{"count":len(dirty),"dwell_seconds_floor":dwell,"budget_seconds":budget,"oldest_path":oldest["path"] if oldest else None},"breaches":breaches}
    if "--write" in argv:
        PROOF.parent.mkdir(parents=True,exist_ok=True); PROOF.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    if "--json" in argv: print(json.dumps(record,indent=2))
    else:
        print(f"stall_clock: {record['verdict']} — {len(dirty)} dirty path(s), {dwell}s/{budget}s; committed unpublished work is not measured")
        for item in breaches: print("  LOCAL DWELL: "+item)
    return 1 if breaches else 0

if __name__=="__main__": sys.exit(main(sys.argv[1:]))
