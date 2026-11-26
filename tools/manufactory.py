#!/usr/bin/env python3
"""Offline Darkith manufactory contract. No remote writes, command execution, minting or payment."""
import argparse, copy, hashlib, json, pathlib, re, sys, uuid
from datetime import datetime, timezone
from omega_time import iso as omega_iso
from urllib.parse import urlsplit

STATES=("DISCOVERED","CONFIRMED","ADMITTED","COUPLED","ROUTED","IN_PROGRESS","SUBMITTED","VERIFIED","PRESERVED")
NEXT=dict(zip(STATES,STATES[1:]))
HEX64=re.compile(r"^[0-9a-f]{64}$")
class Refused(ValueError): pass
def now():
    return omega_iso()
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else canon(x)).hexdigest()
def snap(d): return {k:copy.deepcopy(v) for k,v in d.items() if k not in ("history","origin")}
def merge(d,e):
    for k,v in e.items():
        if k=="actor": continue
        if isinstance(v,dict) and isinstance(d.get(k),dict): d[k].update(copy.deepcopy(v))
        else: d[k]=copy.deepcopy(v)
def create(title,project,url,source=""):
    u=urlsplit(url)
    if u.scheme!="https" or not u.hostname or not title.strip() or not project.strip(): raise Refused("title/project and valid HTTPS source required")
    d={"schema":"darkith.fracture-dossier/1","id":"FR-"+uuid.uuid4().hex[:12],"created_at":now(),"state":"DISCOVERED",
       "title":title.strip(),"project":project.strip(),"source":{"name":source,"url":url,"retrieved_at":now(),"revision":None,"content_sha256":None},
       "observed":None,"expected":None,"reproduction":None,"acceptance":None,"scope":None,"authority":None,
       "adapter":None,"participant":None,"work":None,"repair":None,"verification":None,"preservation":None,"history":[]}
    origin=copy.deepcopy(d); origin.pop("origin",None); origin.pop("history",None); d["origin"]=origin; validate(d); return d
def validate(d):
    if not isinstance(d,dict) or d.get("schema")!="darkith.fracture-dossier/1" or not re.fullmatch(r"FR-[0-9a-f]{12}",str(d.get("id",""))): raise Refused("schema/id invalid")
    if d.get("state") not in STATES: raise Refused("state invalid")
    u=urlsplit(str(d.get("source",{}).get("url","")))
    if u.scheme!="https" or not u.hostname or not d["source"].get("retrieved_at"): raise Refused("source must be valid HTTPS with retrieval time")
    if not d.get("title") or not d.get("project"): raise Refused("title/project required")
    origin=d.get("origin"); hist=d.get("history")
    if not isinstance(origin,dict) or origin.get("id")!=d["id"] or origin.get("state")!="DISCOVERED" or not isinstance(hist,list): raise Refused("origin/history invalid")
    replay=copy.deepcopy(origin); replay.pop("history",None); prev="0"*64
    for i,ev in enumerate(hist):
        if ev.get("seq")!=i+1 or ev.get("previous")!=prev or ev.get("from")!=replay["state"] or NEXT.get(replay["state"])!=ev.get("to"): raise Refused("history order/link invalid")
        merge(replay,ev.get("evidence",{})); replay["state"]=ev["to"]
        if ev.get("state_digest")!=sha(replay) or ev.get("hash")!=sha({k:v for k,v in ev.items() if k!="hash"}): raise Refused("history/state digest invalid")
        prev=ev["hash"]
    if replay!=snap(d): raise Refused("current bytes differ from hash-chained state")
    i=STATES.index(d["state"])
    req={
      "CONFIRMED":("source.revision","source.content_sha256","observed","expected","reproduction"),
      "ADMITTED":("acceptance","scope","authority"),
      "COUPLED":("adapter.name","adapter.reads","adapter.writes","adapter.disconnect"),
      "ROUTED":("participant.handle","participant.role","participant.consent"),
      "IN_PROGRESS":("work.branch","work.base_revision","work.author","work.summary","work.tests"),
      "SUBMITTED":("repair.patch_sha256","repair.summary","repair.tests"),
      "VERIFIED":("verification.reviewer","verification.independent","verification.tests"),
      "PRESERVED":("preservation.license","preservation.provenance","preservation.record_sha256")}
    for state in STATES[1:i+1]:
        for key in req[state]:
            v=d
            for part in key.split("."): v=v.get(part) if isinstance(v,dict) else None
            if v is None or v=="": raise Refused("missing "+key)
    if i>=1 and not HEX64.fullmatch(str(d["source"].get("content_sha256",""))): raise Refused("source snapshot SHA-256 required")
    if i>=4 and d["participant"].get("consent") is not True: raise Refused("explicit participant consent required")
    if i>=5 and not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})",str(d["work"].get("base_revision",""))): raise Refused("repair base must be pinned")
    if i>=6:
        if not HEX64.fullmatch(str(d["repair"].get("patch_sha256",""))) or not d["repair"]["tests"]: raise Refused("patch digest and executed test receipts required")
        if any(not isinstance(t,dict) or t.get("exit_code")!=0 or not HEX64.fullmatch(str(t.get("stdout_sha256",""))) for t in d["repair"]["tests"]): raise Refused("test receipts require exit 0 and output SHA-256")
    if i>=7:
        v=d["verification"]
        if v.get("independent") is not True or v.get("reviewer")==d["work"].get("author"): raise Refused("independent reviewer must differ from repair author")
        if not v.get("tests") or any(not isinstance(t,dict) or t.get("exit_code")!=0 or t.get("source_revision")!=d["work"]["base_revision"] or not HEX64.fullmatch(str(t.get("stdout_sha256",""))) for t in v["tests"]): raise Refused("verification must pass on exact base revision with output digest")
    if i>=8 and not HEX64.fullmatch(str(d["preservation"].get("record_sha256",""))): raise Refused("preservation SHA-256 required")
def step(d,target,evidence):
    validate(d)
    if NEXT.get(d["state"])!=target or not isinstance(evidence,dict) or not evidence: raise Refused("non-sequential transition or missing evidence")
    c=copy.deepcopy(d); merge(c,evidence); c["state"]=target
    ev={"seq":len(c["history"])+1,"at":now(),"from":d["state"],"to":target,"actor":evidence.get("actor","operator"),
        "evidence":{k:v for k,v in evidence.items() if k!="actor"},"previous":c["history"][-1]["hash"] if c["history"] else "0"*64}
    ev["state_digest"]=sha(snap(c)); ev["hash"]=sha(ev); c["history"].append(ev); validate(c); d.clear(); d.update(c); return d
def import_scout(path,index,project):
    raw=path.read_bytes(); proof=json.loads(raw); item=proof["fractures"][index-1]
    d=create(item["title"],project,item["url"],item.get("source","fracture-scout"))
    d["source"]["retrieved_at"]=omega_iso(datetime.fromtimestamp(path.stat().st_mtime,timezone.utc))
    d["source"]["revision"]="scout-run:"+hashlib.sha256(raw).hexdigest(); d["source"]["content_sha256"]=sha(item)
    d["scout"]={"proof_sha256":hashlib.sha256(raw).hexdigest(),"candidate_index":index,"candidate":item}
    origin=copy.deepcopy(d); origin.pop("origin",None); origin.pop("history",None); d["origin"]=origin; validate(d); return d
def packet(d,patch,out):
    validate(d)
    if d["state"]!="IN_PROGRESS": raise Refused("packet requires IN_PROGRESS")
    raw=patch.read_bytes()
    if not raw or b"GIT binary patch" in raw: raise Refused("patch must be non-empty inspectable text")
    d["repair"]={"patch_sha256":hashlib.sha256(raw).hexdigest(),"summary":d["work"]["summary"],"tests":d["work"]["tests"],"patch_file":"patch.diff"}
    d["state"]="SUBMITTED"; e={"repair":copy.deepcopy(d["repair"])}
    ev={"seq":len(d["history"])+1,"at":now(),"from":"IN_PROGRESS","to":"SUBMITTED","actor":"packet-builder","evidence":e,"previous":d["history"][-1]["hash"]}
    ev["state_digest"]=sha(snap(d)); ev["hash"]=sha(ev); d["history"].append(ev); validate(d)
    out.mkdir(parents=True,exist_ok=True); (out/"patch.diff").write_bytes(raw); (out/"dossier.json").write_bytes(canon(d)+b"\n")
    m={"schema":"darkith.repair-packet/1","fracture_id":d["id"],"source_revision":d["work"]["base_revision"],"patch_sha256":d["repair"]["patch_sha256"],"dossier_sha256":sha(d),"state":"SUBMITTED","target_project_disposition":"UNREVIEWED","compensation":"NOT_EXECUTED","nt_xii_issuance":"NOT_EXECUTED"}
    (out/"packet.json").write_bytes(canon(m)+b"\n"); return m
def check_packet(p):
    try:
        m=json.loads((p/"packet.json").read_text()); d=json.loads((p/"dossier.json").read_text()); patch=(p/"patch.diff").read_bytes(); validate(d)
    except Exception as e: return [str(e)]
    errs=[]
    if m.get("fracture_id")!=d.get("id") or m.get("dossier_sha256")!=sha(d): errs.append("dossier identity/digest mismatch")
    if m.get("patch_sha256")!=hashlib.sha256(patch).hexdigest() or m.get("state")!="SUBMITTED" or d.get("state")!="SUBMITTED": errs.append("patch/state mismatch")
    if m.get("source_revision")!=d.get("work",{}).get("base_revision") or m.get("patch_sha256")!=d.get("repair",{}).get("patch_sha256"): errs.append("packet source/repair binding mismatch")
    if m.get("target_project_disposition")!="UNREVIEWED" or m.get("compensation")!="NOT_EXECUTED" or m.get("nt_xii_issuance")!="NOT_EXECUTED": errs.append("downstream state falsely promoted")
    return errs
def selftest():
    d=create("fixture","project","https://example.org/issue/1")
    stages=[("CONFIRMED",{"source":{"revision":"rev1","content_sha256":"a"*64},"observed":"bad","expected":"good","reproduction":"steps"}),("ADMITTED",{"acceptance":["test"],"scope":"one module","authority":"maintainer"}),("COUPLED",{"adapter":{"name":"ro","reads":["source"],"writes":[],"disconnect":"remove"}}),("ROUTED",{"participant":{"handle":"author","role":"developer","consent":True}}),("IN_PROGRESS",{"work":{"branch":"repair/x","base_revision":"b"*40,"author":"author","summary":"fix","tests":[{"command":"test","exit_code":0,"stdout_sha256":"c"*64}]}})]
    for s,e in stages: step(d,s,e)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p=pathlib.Path(td)/"fix.diff"; p.write_text("diff --git a/x b/x\n")
        packet(d,p,pathlib.Path(td)/"packet"); assert check_packet(pathlib.Path(td)/"packet")==[]
        (pathlib.Path(td)/"packet"/"patch.diff").write_text("tampered"); assert check_packet(pathlib.Path(td)/"packet")
    step(d,"VERIFIED",{"verification":{"reviewer":"independent","independent":True,"tests":[{"command":"test","exit_code":0,"source_revision":"b"*40,"stdout_sha256":"d"*64}]}})
    step(d,"PRESERVED",{"preservation":{"license":"MIT","provenance":"source+patch","record_sha256":"e"*64}})
    assert d["state"]=="PRESERVED"; print("MANUFACTORY SELFTEST: PASS"); return 0
def write_json(path,d):
    temp=path.with_name(path.name+".tmp-"+uuid.uuid4().hex)
    try:
        temp.write_bytes(canon(d)+b"\n"); temp.replace(path)
    finally:
        try: temp.unlink()
        except FileNotFoundError: pass
def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True); sub.add_parser("selftest")
    p=sub.add_parser("create"); p.add_argument("--title",required=True); p.add_argument("--project",required=True); p.add_argument("--url",required=True); p.add_argument("--source",default=""); p.add_argument("--out",type=pathlib.Path,required=True)
    p=sub.add_parser("import-scout"); p.add_argument("--proof",type=pathlib.Path,default=pathlib.Path("proof/fracture_scout.json")); p.add_argument("--index",type=int,required=True); p.add_argument("--project",required=True); p.add_argument("--out",type=pathlib.Path,required=True)
    p=sub.add_parser("transition"); p.add_argument("dossier",type=pathlib.Path); p.add_argument("--to",choices=STATES,required=True); p.add_argument("--evidence",type=pathlib.Path,required=True)
    p=sub.add_parser("packet"); p.add_argument("dossier",type=pathlib.Path); p.add_argument("patch",type=pathlib.Path); p.add_argument("--out",type=pathlib.Path,required=True)
    p=sub.add_parser("verify-packet"); p.add_argument("packet",type=pathlib.Path)
    a=ap.parse_args()
    try:
        if a.cmd=="selftest": return selftest()
        if a.cmd=="create": d=create(a.title,a.project,a.url,a.source)
        elif a.cmd=="import-scout": d=import_scout(a.proof,a.index,a.project)
        elif a.cmd=="transition":
            d=json.loads(a.dossier.read_text()); validate(d); step(d,a.to,json.loads(a.evidence.read_text())); write_json(a.dossier,d)
        elif a.cmd=="packet":
            d=json.loads(a.dossier.read_text()); validate(d); packet(d,a.patch,a.out); write_json(a.dossier,d); return 0
        elif a.cmd=="verify-packet":
            errs=check_packet(a.packet); print("PACKET VALID" if not errs else "\n".join(errs)); return int(bool(errs))
        if a.cmd in ("create","import-scout"): a.out.parent.mkdir(parents=True,exist_ok=True); write_json(a.out,d); print(d["id"]+" DISCOVERED")
        return 0
    except (Refused,OSError,ValueError,KeyError,IndexError,json.JSONDecodeError) as e: print("REFUSED:",e,file=sys.stderr); return 2
if __name__=="__main__": sys.exit(main())
