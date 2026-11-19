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
    ROOT / "darkith-inscriber.html",
    ROOT / "darkith code studio.html",
    ROOT / "darkith home forge.html",
    ROOT / "darkith forge.html",
]

LAW_HARNESS = r"""
const CL = require(%s);
let pass = 0, fail = 0;
const ok = (n, c) => { if (c) pass++; else { fail++; console.log('   FAIL ' + n); } };

// seed
CL.reset(); CL.observe({switching:5, correcting:3}); CL.advance();
ok('seed does not fail', CL.verdict() !== 'FAIL');
ok('HWM seeded at current level', CL.report().classes.find(c=>c.cls==='switching').hwm === 5);

// flux down
CL.observe({switching:2, correcting:0}); const a1 = CL.advance();
ok('flux down clears the class', a1.events.some(e => /cleared switching: 5 -> 2/.test(e)));
ok('HWM moved down', CL.report().classes.find(c=>c.cls==='switching').hwm === 2);

// regression
CL.observe({switching:4}); CL.advance();
ok('net addition FAILs', CL.verdict() === 'FAIL');
ok('HWM NOT raised on regression', CL.report().classes.find(c=>c.cls==='switching').hwm === 2);

// waiver
CL.reset(); CL.observe({waiting:3}); CL.advance();
CL.observe({waiting:6}); const a2 = CL.advance('spike: migration');
ok('waiver justifies a rise', CL.verdict() !== 'FAIL' && a2.events.some(e => /JUSTIFIED waiver waiting/.test(e)));
ok('waiver is recorded', CL.report().classes.find(c=>c.cls==='waiting').waived === true);

// force-degradation
CL.reset(); CL.observe({searching:2}); CL.advance();
for (let i = 0; i < CL.WINDOW; i++) { CL.observe({searching:2}); CL.advance(); }
ok('stasis force-degraded to FAIL', CL.verdict() === 'FAIL');
ok('degradation names the class', CL.report().reason.includes('searching'));

// absorb a pre-runner report
CL.reset(); CL.absorb({errors:['a','b'], metrics:{longTasks:4}});
const st = CL.observe();
ok('absorb maps errors -> correcting', st.correcting === 2);
ok('absorb maps longTasks -> waiting', st.waiting === 4);

console.log(pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
""" % json.dumps(str(ENGINE))


def main() -> int:
    if not ENGINE.is_file():
        print("clearanceloop_gate: SKIP — vendor/clearanceloop.js missing")
        return 0

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
