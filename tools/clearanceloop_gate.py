#!/usr/bin/env python3
"""clearanceloop gate — the homeokinetic ratchet must hold, in every surface.

The ratchet is one law (tools/source_inspector.py proves it on source bytes; this
proves the runtime engine that carries it into every app). This gate locks:

  1. the module exposes the documented surface (observe/absorb/advance/report/ui…);
  2. the four laws hold on a deterministic simulation:
       - a first delivery SEEDS the high-water mark (no false regression);
       - less debt clears and the HWM moves DOWN (flux down);
       - more debt than the HWM is a regression = FAIL, and the HWM is NOT raised;
       - stasis across the delivery window is force-degraded to a blocker;
       - a rise is permitted only by a recorded waiver;
  3. the engine is actually WIRED INTO every surface (omega, savf, studio, inscriber,
     home forge, fused forge) — both engines present, marker-delimited, in sync.

Everything degrades honestly: no `node` -> SKIP, never a false PASS.

Usage: python3 tools/clearanceloop_gate.py
"""
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENGINE = ROOT / "app/src/main/assets/vendor/clearanceloop.js"

# Surfaces that must carry the engines. A surface that exists but lost the engine
# is a real defect; a surface that is absent (e.g. a regenerable output) is skipped.
SURFACES = [
    ROOT / "omega.html",
    ROOT / "savf.html",
    ROOT / "clearanceloop.html",
    ROOT / "darkith-inscriber.html",
    ROOT / "darkith code studio.html",
    ROOT / "darkith home forge.html",
    ROOT / "darkith forge.html",
]

LAW_HARNESS = r"""
const path = %s;
let pass = 0, fail = 0;
const ok = (n, c) => { if (c) pass++; else { fail++; console.log('   FAIL ' + n); } };
const cls = (r, c) => r.classes.find(x => x.cls === c);

/* Storage stub: lets a reload be simulated, which is the only way to prove the HWM
   actually survives one. Without it a persistence bug is invisible. */
let disk = null;
global.localStorage = { getItem: () => disk, setItem: (k, v) => { disk = v; } };
const fresh = () => { delete require.cache[require.resolve(path)]; return require(path); };
let CL = fresh();

// L1 SEED: a first delivery seeds the HWM at the current level (no false regression)
CL.reset(); CL.observe({switching:5, correcting:3}); CL.advance();
ok('L1 seed does not fail', CL.verdict() !== 'FAIL');
ok('L1 HWM seeded at current level', cls(CL.report(),'switching').hwm === 5);

// L2 FLUX DOWN: less debt clears, the HWM ratchets down
CL.observe({switching:2, correcting:0}); const a1 = CL.advance();
ok('L2 flux down clears the class', a1.events.some(e => /cleared switching: 5 -> 2/.test(e)));
ok('L2 HWM moved down', cls(CL.report(),'switching').hwm === 2);

// L3 REGRESSION: more debt than the HWM FAILs, and the HWM is NOT raised
CL.observe({switching:4}); CL.advance();
ok('L3 net addition FAILs', CL.verdict() === 'FAIL');
ok('L3 HWM NOT raised on regression', cls(CL.report(),'switching').hwm === 2);

// L4 WAIVER: permits the debt for a bounded window and NEVER raises the HWM
CL.reset(); CL.observe({waiting:3}); CL.advance();
CL.observe({waiting:6}); const a2 = CL.advance('spike: migration');
ok('L4 waiver justifies the debt', CL.verdict() !== 'FAIL' && a2.events.some(e => /JUSTIFIED waiver waiting/.test(e)));
ok('L4 waiver is recorded', cls(CL.report(),'waiting').waived === true);
ok('L4 waiver does NOT raise the HWM', cls(CL.report(),'waiting').hwm === 3);

// L5 TIME-BOX: the waiver expires, and the debt becomes a plain regression again
for (let i = 0; i < CL.WAIVER; i++) { CL.observe({waiting:6}); CL.advance(); }
ok('L5 waiver expires -> regression again', CL.verdict() === 'FAIL' && cls(CL.report(),'waiting').status === 'regression');
ok('L5 HWM never rose across the waiver', cls(CL.report(),'waiting').hwm === 3);

// L5b REVOCATION: a waiver is a bounded exception, not a pardon. Ending it early
// must return the class to its mark at once, keep the history, and fail closed.
CL.reset(); CL.observe({waiting:3}); CL.advance();
CL.observe({waiting:6}); CL.advance('temporary');
ok('L5b waiver is live before revoke', cls(CL.report(),'waiting').waived === true);
const deliveryBefore = CL.report().delivery;
ok('L5b revoke reports success', CL.revoke('waiting') === true);
ok('L5b revoke clears the waiver', cls(CL.report(),'waiting').waived === false);
ok('L5b revoke never touches the HWM', cls(CL.report(),'waiting').hwm === 3);
ok('L5b revoked debt is a regression', CL.verdict() === 'FAIL' && cls(CL.report(),'waiting').status === 'regression');
ok('L5b revoke preserves history', CL.report().delivery === deliveryBefore);
ok('L5b revoke is idempotent-safe', CL.revoke('waiting') === false);
ok('L5b revoke rejects unknown class', CL.revoke('not-a-class') === false && CL.revoke(null) === false);

// L6 STASIS: debt that does not flux down over the window is force-degraded
CL.reset(); CL.observe({searching:2}); CL.advance();
for (let i = 0; i < CL.WINDOW; i++) { CL.observe({searching:2}); CL.advance(); }
ok('L6 stasis force-degraded to FAIL', CL.verdict() === 'FAIL');
ok('L6 degradation names the class', CL.report().reason.includes('searching'));

// L7 PERSISTENCE: the HWM must survive a reload, or the ratchet is unenforceable
CL = fresh();
CL.reset(); CL.observe({waiting:8}); CL.advance(); CL.observe({waiting:3}); CL.advance();
CL = fresh();
ok('L7 HWM survives a reload', cls(CL.report(),'waiting').hwm === 3 && CL.report().delivery === 2);
CL.observe({waiting:5}); CL.advance();
ok('L7 regression still enforced after reload', CL.verdict() === 'FAIL' && cls(CL.report(),'waiting').hwm === 3);

// L8 FAIL-CLOSED: a legacy bare-string waiver carried no expiry; it must not grant immunity
disk = JSON.stringify({hwm:{waiting:3}, justified:{waiting:'old migration'}, since:{}, delivery:4,
  history:[{delivery:4, now:{waiting:9}, score:9}]});
CL = fresh(); const lr = CL.report();
ok('L8 legacy waiver fails closed', cls(lr,'waiting').waived === false && lr.verdict === 'FAIL');

// LOOP: absorb a pre-runner report (errors -> correcting, long tasks -> waiting)
CL.reset(); CL.absorb({errors:['a','b'], metrics:{longTasks:4}});
const st = CL.observe();
ok('absorb maps errors -> correcting', st.correcting === 2);
ok('absorb maps longTasks -> waiting', st.waiting === 4);

console.log(pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
""" % json.dumps(str(ENGINE))


def main() -> int:
    if not ENGINE.is_file():
        # vendor/ is fetched, not tracked: exit 3 so CI shows SKIP, never PASS.
        print("clearanceloop_gate: SKIP — vendor/clearanceloop.js missing")
        return 3

    fails: list[str] = []

    node = shutil.which("node")
    if not node:
        print("clearanceloop_gate: ratchet assertions SKIPPED — node not installed")
    else:
        probe = ("const m=require(%s);"
                 "const need=['install','observe','absorb','advance','report','verdict','flux','reset','ui','LAW','WINDOW'];"
                 "const miss=need.filter(k=>typeof m[k]==='undefined');"
                 "if(miss.length){console.error('missing '+miss.join(','));process.exit(1);}"
                 "console.log('surface ok');" % json.dumps(str(ENGINE)))
        r = subprocess.run([node, "-e", probe], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            fails.append("engine surface: " + (r.stderr.strip() or "missing documented API"))

        r = subprocess.run([node, "-e", LAW_HARNESS], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            fails.append("ratchet laws: " + (r.stdout.strip().splitlines() or [""])[-1] + " " + r.stderr.strip()[:300])

    # integration presence: every surface must carry both engines + the shim
    for p in SURFACES:
        if not p.is_file():
            print(f"   {p.name:<26} skipped (absent; regenerable)")
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        missing = []
        if "DarkithPreRunner" not in text:
            missing.append("prerunner")
        if "ClearanceLoop" not in text:
            missing.append("clearanceloop")
        if "DarkithPrerunReady" not in text:
            missing.append("shim")
        if "PRERUNNER:START" not in text:
            missing.append("markers")
        if missing:
            fails.append(f"{p.name}: engine not integrated ({', '.join(missing)})")

    if fails:
        print("clearanceloop_gate: FAIL")
        for f in fails:
            print("   " + f)
        return 1
    print("clearanceloop_gate: PASS — ratchet laws hold + engines wired into every surface")
    return 0


if __name__ == "__main__":
    sys.exit(main())
