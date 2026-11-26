#!/usr/bin/env python3
"""Ensure toolchain probe timeouts are bounded in the repair cycle."""
import pathlib,sys,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/"tools"))
import toolchain_gate as g
def main():
    seen={}; original=g.subprocess.run
    def fake(cmd,**kwargs):
        seen.update(kwargs); return subprocess.CompletedProcess(cmd,0,stdout="info: kotlin version",stderr="")
    g.subprocess.run=fake
    try: ok,_=g.kotlinc_runs()
    finally: g.subprocess.run=original
    assert ok and seen.get("timeout",999)<=30
    print("TOOLCHAIN GATE TEST: PASS")
if __name__=="__main__": main()
