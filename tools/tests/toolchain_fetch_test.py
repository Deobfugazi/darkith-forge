#!/usr/bin/env python3
"""Regression for retry/fallback behavior when Maven returns transient 429/5xx."""
import pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/"tools"))
import toolchain_fetch_gate as g
def main():
    t=g.SOURCE.read_text(encoding="utf-8"); assert g.check(t); assert g.patch_text(t)==t; assert g.selftest()==0
    print("TOOLCHAIN FETCH TEST: PASS")
if __name__=="__main__": main()
