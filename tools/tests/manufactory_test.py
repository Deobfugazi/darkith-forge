#!/usr/bin/env python3
import json, pathlib, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/"tools"))
import manufactory as m
def check(label,fn):
    try: assert fn(); print("PASS",label)
    except Exception as e: print("FAIL",label,e); raise
def main():
    d=m.create("fracture","project","https://example.org/issue/1")
    try: m.step(d,"ADMITTED",{"authority":"skip"}); raise AssertionError("skip accepted")
    except m.Refused: print("PASS stage skipping refused")
    stages=[("CONFIRMED",{"source":{"revision":"r1","content_sha256":"a"*64},"observed":"crash","expected":"works","reproduction":"steps"}),("ADMITTED",{"acceptance":["test passes"],"scope":"one module","authority":"maintainer"}),("COUPLED",{"adapter":{"name":"readonly","reads":["source"],"writes":[],"disconnect":"remove"}}),("ROUTED",{"participant":{"handle":"author","role":"developer","consent":True}}),("IN_PROGRESS",{"work":{"branch":"fix/x","base_revision":"b"*40,"author":"author","summary":"fix","tests":[{"command":"test","exit_code":0,"stdout_sha256":"c"*64}]}})]
    for s,e in stages: m.step(d,s,e)
    with tempfile.TemporaryDirectory() as td:
        p=pathlib.Path(td)/"patch.diff"; p.write_text("diff --git a/x b/x\n"); out=pathlib.Path(td)/"packet"
        m.packet(d,p,out); check("packet integrity",lambda:m.check_packet(out)==[])
        (out/"patch.diff").write_text("altered"); check("patch tamper detected",lambda:bool(m.check_packet(out)))
        proof=pathlib.Path(td)/"scout.json"; proof.write_text(json.dumps({"fractures":[{"title":"candidate","url":"https://example.org/1","source":"fixture"}]}))
        cand=m.import_scout(proof,1,"project"); check("Scout import stays DISCOVERED",lambda:cand["state"]=="DISCOVERED" and bool(cand["source"]["content_sha256"]))
    try: m.step(d,"VERIFIED",{"verification":{"reviewer":"author","independent":True,"tests":[{"exit_code":0,"source_revision":"b"*40,"stdout_sha256":"d"*64}]}}); raise AssertionError("self-verify accepted")
    except m.Refused: print("PASS self-verification refused")
    m.step(d,"VERIFIED",{"verification":{"reviewer":"reviewer","independent":True,"tests":[{"exit_code":0,"source_revision":"b"*40,"stdout_sha256":"d"*64}]}})
    m.step(d,"PRESERVED",{"preservation":{"license":"MIT","provenance":"source and patch","record_sha256":"e"*64}})
    check("evidence chain reaches PRESERVED",lambda:d["state"]=="PRESERVED"); print("MANUFACTORY TEST: PASS")
if __name__=="__main__": main()
