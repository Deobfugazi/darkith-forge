#!/usr/bin/env python3
"""Regression test for exact and prefix echo semantics at realistic session size."""
import hashlib, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/"tools"))
import chat_gatekeeper as g
import chat_gatekeeper_perf_gate as gate
def main():
    messages=[]
    for i in range(6000):
        key=f"{i:08d}:"+hashlib.sha256(str(i).encode()).hexdigest()
        messages.append(key+" "+("payload-"+str(i))*4)
    assert gate.selftest()==0
    idx=g.AssistantEchoIndex(messages)
    assert len(idx.sorted)==6000
    assert idx.matches_normalized(messages[-1])
    assert idx.matches_normalized(messages[-1]+" user-side suffix")
    assert idx.matches_normalized(messages[-1][:100])
    assert not idx.matches_normalized("z"*120)
    assert g._is_echo("Operator — this is an agent report",idx)
    assert not g._is_echo("ordinary user request",idx)
    print("CHAT GATEKEEPER PERF TEST: PASS (6000 indexed messages)")
if __name__=="__main__": main()
