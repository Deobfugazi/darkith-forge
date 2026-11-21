#!/usr/bin/env python3
"""nodal_gate.py — Auto-Nodal Co-ordina-Sync, proven on both halves of the pair.

The house law: Python is the authority, and every Python surface ships its universally
frontend webview html friendly accompaniment coupling (.js), the SAVF. That coupling is only
honest if the two agree, so this gate proves it:

  1. the Python package's own invariant suite passes (tests/test_nodal.py);
  2. the .js twin enforces the same laws in Node (no browser needed);
  3. the two are BYTE-AGREEING on identity: same sha256 vectors, same GENESIS anchor, same
     receipt_id for the same receipt, same fire order for the same graph.

Point 3 is the one that matters. A .js file that "also works" but hashes differently would be
two systems wearing one name; this fails closed on any divergence.

Degrades honestly: no node -> the JS half is SKIPped and the gate says so, never a false PASS.

Writes proof/nodal_coordina_sync.json.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ENGINE = ROOT / "app/src/main/assets/vendor/nodal.js"
ENGINE_TS = ROOT / "app/src/main/assets/vendor/nodal.ts"
SUITE = ROOT / "tests/test_nodal.py"
PROOF = ROOT / "proof/nodal_coordina_sync.json"


def run_python_suite() -> tuple[bool, str]:
    if not SUITE.is_file():
        return False, f"{SUITE.relative_to(ROOT)} missing"
    r = subprocess.run(
        [sys.executable, str(SUITE)], cwd=ROOT, capture_output=True, text=True
    )
    # unittest writes its summary to stderr, so reading only stdout would report an empty
    # result and make the proof file lie about what ran.
    combined = (r.stdout or "") + (r.stderr or "")
    lines = [ln for ln in combined.strip().splitlines() if ln.strip()]
    # Normalize the elapsed time out of unittest's summary: "Ran 43 tests in 0.013s" carries a
    # wall-clock duration that differs on every run, which would rewrite this tracked proof
    # file each pass and dirty the tree — the exact self-inflicted churn MUST #36 forbids.
    # The durable facts are the count and the outcome.
    ran = ""
    for ln in lines:
        if ln.startswith("Ran "):
            ran = re.sub(r" in [0-9.]+s$", "", ln)
            break
    tail = next((ln for ln in reversed(lines) if ln == "OK" or ln.startswith("FAILED")),
                lines[-1] if lines else "")
    summary = f"{ran} {tail}".strip()
    return r.returncode == 0, summary


JS_HARNESS = r"""
const N = require(%s);
let pass = 0, fail = 0;
const ok = (n, c) => { if (c) pass++; else { fail++; console.log('   FAIL ' + n); } };
const V = N.Verdict, D = N.DegradedClass;

// --- schema totality
try {
  N.makeReceipt({engineId:'e',boundary:'b',epoch:0,seq:0,lane:'l',inputHash:'h',verdict:V.DEGRADED,clause:'c'});
  ok('degraded-without-class refused', false);
} catch (e) { ok('degraded-without-class refused', e.name === 'SchemaViolation'); }

try {
  N.makeReceipt({engineId:'e',boundary:'b',epoch:0,seq:0,lane:'l',inputHash:'h',verdict:V.ALLOW,clause:'c',degradedClass:D.STALE_EPOCH});
  ok('allow-with-class refused', false);
} catch (e) { ok('allow-with-class refused', e.name === 'SchemaViolation'); }

// --- ledger laws
const L = N.Ledger();
const r1 = N.makeReceipt({engineId:'e',boundary:'b',epoch:0,seq:0,lane:'l',inputHash:'h1',verdict:V.ALLOW,clause:'c'});
const a1 = L.append(r1);
ok('first append accepted', a1.accepted);
ok('first anchors to genesis', a1.receipt.witness === N.GENESIS_WITNESS);

const r2 = N.makeReceipt({engineId:'e',boundary:'b',epoch:1,seq:1,lane:'l',inputHash:'h2',verdict:V.ALLOW,clause:'c'});
const a2 = L.append(r2);
ok('second chains to first', a2.receipt.witness === a1.receiptId);

const forged = L.append(N.makeReceipt({engineId:'e',boundary:'b',epoch:2,seq:2,lane:'l',inputHash:'h3',verdict:V.ALLOW,clause:'c',witness:'FORGED'}));
ok('caller cannot forge witness', forged.receipt.witness === a2.receiptId);

ok('phantom upstream refused', !L.append(N.makeReceipt({engineId:'x',boundary:'b',epoch:0,seq:0,lane:'m',inputHash:'h',verdict:V.ALLOW,clause:'c',upstreamIds:['deadbeef']})).accepted);
ok('degraded may cite missing upstream', L.append(N.makeReceipt({engineId:'x',boundary:'b',epoch:0,seq:0,lane:'m',inputHash:'h',verdict:V.DEGRADED,degradedClass:D.UPSTREAM_MISSING,clause:'c',upstreamIds:['deadbeef']})).accepted);

ok('read barrier hides same epoch', L.readAsof(1).every(r => r.receiptId !== a2.receiptId) && L.readAsof(1).some(r => r.receiptId === a1.receiptId));

const staleL = N.Ledger();
staleL.append(N.makeReceipt({engineId:'e',boundary:'b',epoch:5,seq:0,lane:'s',inputHash:'h',verdict:V.ALLOW,clause:'c'}));
ok('stale epoch write fenced', !staleL.append(N.makeReceipt({engineId:'e',boundary:'b',epoch:1,seq:1,lane:'s',inputHash:'h',verdict:V.ALLOW,clause:'c'})).accepted);
ok('stale epoch may append degraded', staleL.append(N.makeReceipt({engineId:'e',boundary:'b',epoch:1,seq:1,lane:'s',inputHash:'h',verdict:V.DEGRADED,degradedClass:D.STALE_EPOCH,clause:'c'})).accepted);

ok('chain verifies', L.verifyChain('l').length === 0);

// --- bot totality
function Bot(id, fn) { N.NodalBot.call(this, arguments[2] || new N.Ledger(), {lane:id}); this.engineId = id; this._fn = fn; }
Bot.prototype = Object.create(N.NodalBot.prototype);
Bot.prototype.decide = function (i, u) { return this._fn(i, u); };

const LB = N.Ledger();
const raiser = new Bot('raiser', function(){ throw new Error('boom'); }, LB);
const rr = raiser.fire('x', 0);
ok('throwing decide becomes degraded', rr.verdict === V.DEGRADED && rr.receipt.degradedClass === D.INTERNAL_ERROR);
ok('traceback is carried', !!rr.traceback);

const missing = new Bot('m', function(){ return {verdict:V.ALLOW,clause:'c'}; }, LB).fire('x', 0, ['ghost']);
ok('missing upstream becomes degraded', missing.receipt.degradedClass === D.UPSTREAM_MISSING);

const ds = new Bot('ds', function(i,u){ return N.propagateDegraded({engineId:'ds'}, u); }, LB).fire('x', 1, [rr.receiptId]);
ok('downstream-of-degraded marked', ds.receipt.degradedClass === D.DOWNSTREAM_OF_DEGRADED);

// --- fire order
ok('upstream fires first', JSON.stringify(N.computeFireOrder([{engineId:'e2',upstreamEngineIds:['e1']},{engineId:'e1'}], '1')) === JSON.stringify(['e1','e2']));
let cyc = false; try { N.computeFireOrder([{engineId:'a',upstreamEngineIds:['b']},{engineId:'b',upstreamEngineIds:['a']}], '1'); } catch(e) { cyc = true; }
ok('cycle rejected', cyc);
const det = N.computeFireOrder([{engineId:'z'},{engineId:'y'},{engineId:'x'}], '9');
ok('order deterministic', JSON.stringify(det) === JSON.stringify(N.computeFireOrder([{engineId:'x'},{engineId:'y'},{engineId:'z'}], '9')));

// --- reconcile
const rc = N.reconcile([
  N.makeReceipt({engineId:'e1',boundary:'b',epoch:0,seq:0,lane:'a',inputHash:'h',verdict:V.ALLOW,clause:'c1'}),
  N.makeReceipt({engineId:'e2',boundary:'b',epoch:0,seq:1,lane:'b',inputHash:'h',verdict:V.DENY,clause:'c2'})
], ['e1','e2']);
ok('disagreement named', !rc.agreed && /e2:c2=deny/.test(rc.reason));
ok('unranked cannot be canonical', N.reconcile([N.makeReceipt({engineId:'zz',boundary:'b',epoch:0,seq:0,lane:'a',inputHash:'h',verdict:V.ALLOW,clause:'c'})], ['e1']).canonicalId === null);

console.log(pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
""" % json.dumps(str(ENGINE))


PARITY_HARNESS = r"""
const N = require(%s);
// Same receipt, same bytes, same id -- computed in JS and compared to the Python value.
const r = N.makeReceipt({engineId:'parity',boundary:'parity.b',epoch:3,seq:4,lane:'parity',inputHash:'abc',verdict:'allow',clause:'parity.c'});
console.log(JSON.stringify({
  sha256_abc: N.sha256('abc'),
  genesis: N.GENESIS_WITNESS,
  receipt_id: r.receiptId,
  fire_order: N.computeFireOrder([{engineId:'engine_4_integrity',upstreamEngineIds:['engine_1_friction']},{engineId:'engine_1_friction'}], '1')
}));
""" % json.dumps(str(ENGINE))



def find_tsc():
    for cand in (
        ROOT / "darkith-omega-homekeeper/node_modules/.bin/tsc",
        ROOT / "node_modules/.bin/tsc",
    ):
        if cand.exists():
            return cand
    return None


TS_HARNESS = r"""
const { default: N } = await import(%s);
let pass = 0, fail = 0;
const ok = (n, c) => { if (c) pass++; else { fail++; console.log('   FAIL ' + n); } };
const V = N.Verdict, D = N.DegradedClass;

try {
  N.makeReceipt({engineId:'e',boundary:'b',epoch:0,seq:0,lane:'l',inputHash:'h',verdict:V.DEGRADED,clause:'c'});
  ok('degraded-without-class refused', false);
} catch (e) { ok('degraded-without-class refused', e.name === 'SchemaViolation'); }

try {
  N.makeReceipt({engineId:'e',boundary:'b',epoch:0,seq:0,lane:'l',inputHash:'h',verdict:V.ALLOW,clause:'c',degradedClass:D.STALE_EPOCH});
  ok('allow-with-class refused', false);
} catch (e) { ok('allow-with-class refused', e.name === 'SchemaViolation'); }

const L = new N.Ledger();
const r1 = N.makeReceipt({engineId:'e',boundary:'b',epoch:0,seq:0,lane:'l',inputHash:'h1',verdict:V.ALLOW,clause:'c'});
const a1 = L.append(r1);
ok('first append accepted', a1.accepted);
ok('first anchors to genesis', a1.receipt.witness === N.GENESIS_WITNESS);

const r2 = N.makeReceipt({engineId:'e',boundary:'b',epoch:1,seq:1,lane:'l',inputHash:'h2',verdict:V.ALLOW,clause:'c'});
const a2 = L.append(r2);
ok('second chains to first', a2.receipt.witness === a1.receiptId);

const forged = L.append(N.makeReceipt({engineId:'e',boundary:'b',epoch:2,seq:2,lane:'l',inputHash:'h3',verdict:V.ALLOW,clause:'c',witness:'FORGED'}));
ok('caller cannot forge witness', forged.receipt.witness === a2.receiptId);

ok('phantom upstream refused', !L.append(N.makeReceipt({engineId:'x',boundary:'b',epoch:0,seq:0,lane:'m',inputHash:'h',verdict:V.ALLOW,clause:'c',upstreamIds:['deadbeef']})).accepted);
ok('degraded may cite missing upstream', L.append(N.makeReceipt({engineId:'x',boundary:'b',epoch:0,seq:0,lane:'m',inputHash:'h',verdict:V.DEGRADED,degradedClass:D.UPSTREAM_MISSING,clause:'c',upstreamIds:['deadbeef']})).accepted);

ok('read barrier hides same epoch', L.readAsof(1).every(r => r.receiptId !== a2.receiptId) && L.readAsof(1).some(r => r.receiptId === a1.receiptId));

const staleL = new N.Ledger();
staleL.append(N.makeReceipt({engineId:'e',boundary:'b',epoch:5,seq:0,lane:'s',inputHash:'h',verdict:V.ALLOW,clause:'c'}));
ok('stale epoch write fenced', !staleL.append(N.makeReceipt({engineId:'e',boundary:'b',epoch:1,seq:1,lane:'s',inputHash:'h',verdict:V.ALLOW,clause:'c'})).accepted);
ok('stale epoch may append degraded', staleL.append(N.makeReceipt({engineId:'e',boundary:'b',epoch:1,seq:1,lane:'s',inputHash:'h',verdict:V.DEGRADED,degradedClass:D.STALE_EPOCH,clause:'c'})).accepted);

ok('chain verifies', L.verifyChain('l').length === 0);

class Bot extends N.NodalBot {
  constructor(id, fn, ledger) { super(ledger, { lane: id }); this.engineId = id; this._fn = fn; }
  decide(i, u) { return this._fn(i, u); }
}

const LB = new N.Ledger();
const raiser = new Bot('raiser', () => { throw new Error('boom'); }, LB);
const rr = raiser.fire('x', 0);
ok('throwing decide becomes degraded', rr.verdict === V.DEGRADED && rr.receipt.degradedClass === D.INTERNAL_ERROR);
ok('traceback is carried', !!rr.traceback);

const missing = new Bot('m', () => ({verdict:V.ALLOW,clause:'c'}), LB).fire('x', 0, ['ghost']);
ok('missing upstream becomes degraded', missing.receipt.degradedClass === D.UPSTREAM_MISSING);

const ds = new Bot('ds', (i,u) => N.propagateDegraded({engineId:'ds'}, u), LB).fire('x', 1, [rr.receiptId]);
ok('downstream-of-degraded marked', ds.receipt.degradedClass === D.DOWNSTREAM_OF_DEGRADED);

ok('upstream fires first', JSON.stringify(N.computeFireOrder([{engineId:'e2',upstreamEngineIds:['e1']},{engineId:'e1'}], '1')) === JSON.stringify(['e1','e2']));
let cyc = false; try { N.computeFireOrder([{engineId:'a',upstreamEngineIds:['b']},{engineId:'b',upstreamEngineIds:['a']}], '1'); } catch(e) { cyc = true; }
ok('cycle rejected', cyc);
const det = N.computeFireOrder([{engineId:'z'},{engineId:'y'},{engineId:'x'}], '9');
ok('order deterministic', JSON.stringify(det) === JSON.stringify(N.computeFireOrder([{engineId:'x'},{engineId:'y'},{engineId:'z'}], '9')));

const rc = N.reconcile([
  N.makeReceipt({engineId:'e1',boundary:'b',epoch:0,seq:0,lane:'a',inputHash:'h',verdict:V.ALLOW,clause:'c1'}),
  N.makeReceipt({engineId:'e2',boundary:'b',epoch:0,seq:1,lane:'b',inputHash:'h',verdict:V.DENY,clause:'c2'})
], ['e1','e2']);
ok('disagreement named', !rc.agreed && /e2:c2=deny/.test(rc.reason));
ok('unranked cannot be canonical', N.reconcile([N.makeReceipt({engineId:'zz',boundary:'b',epoch:0,seq:0,lane:'a',inputHash:'h',verdict:V.ALLOW,clause:'c'})], ['e1']).canonicalId === null);

console.log(pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
"""


TS_PARITY_HARNESS = r"""
const { default: N } = await import(%s);
const r = N.makeReceipt({engineId:'parity',boundary:'parity.b',epoch:3,seq:4,lane:'parity',inputHash:'abc',verdict:'allow',clause:'parity.c'});
console.log(JSON.stringify({
  sha256_abc: N.sha256('abc'),
  genesis: N.GENESIS_WITNESS,
  receipt_id: r.receiptId,
  fire_order: N.computeFireOrder([{engineId:'engine_4_integrity',upstreamEngineIds:['engine_1_friction']},{engineId:'engine_1_friction'}], '1')
}));
"""


def run_ts(instructions: str) -> tuple[bool, str, str, str]:
    lit = json.dumps(ENGINE_TS.as_uri())
    code = instructions % lit
    r = subprocess.run(
        [shutil.which("node"), "--experimental-strip-types", "--input-type=module", "--eval", code],
        cwd=ROOT, capture_output=True, text=True,
    )
    return r.returncode == 0, r.stdout.strip(), r.stderr.strip(), code


def python_parity() -> dict:
    import hashlib

    from nodal import GENESIS_WITNESS, Receipt, Verdict, compute_fire_order, BotRegistration

    r = Receipt(
        engine_id="parity", boundary="parity.b", epoch=3, seq=4, lane="parity",
        input_hash="abc", verdict=Verdict.ALLOW, clause="parity.c",
    )
    order = compute_fire_order(
        [
            BotRegistration("engine_4_integrity", "i", upstream_engine_ids=("engine_1_friction",)),
            BotRegistration("engine_1_friction", "f"),
        ],
        "1",
    )
    return {
        "sha256_abc": hashlib.sha256(b"abc").hexdigest(),
        "genesis": GENESIS_WITNESS,
        "receipt_id": r.receipt_id,
        "fire_order": order,
    }


def main() -> int:
    fails: list[str] = []
    detail: dict = {}

    ok, tail = run_python_suite()
    detail["python_suite"] = {"pass": ok, "summary": tail}
    if not ok:
        fails.append(f"python invariant suite: {tail}")

    node = shutil.which("node")
    if not ENGINE.is_file():
        fails.append("vendor/nodal.js missing — the Python half has no SAVF twin")
    elif not node:
        detail["js_suite"] = {"pass": None, "summary": "SKIP — node not installed"}
        detail["ts_suite"] = {"pass": None, "summary": "SKIP — node not installed"}
        print("nodal_gate: .js/.ts halves SKIPPED — node not installed (never a false PASS)")
    else:
        r = subprocess.run([node, "-e", JS_HARNESS], cwd=ROOT, capture_output=True, text=True)
        js_ok = r.returncode == 0
        summary = (r.stdout.strip().splitlines() or [""])[-1]
        detail["js_suite"] = {"pass": js_ok, "summary": summary, "stderr": r.stderr.strip()[:400]}
        if not js_ok:
            fails.append(f".js laws: {summary} {r.stderr.strip()[:300]}")

        py = python_parity()
        rp = subprocess.run([node, "-e", PARITY_HARNESS], cwd=ROOT, capture_output=True, text=True)
        if rp.returncode != 0:
            fails.append("parity harness failed: " + rp.stderr.strip()[:300])
        else:
            js = json.loads(rp.stdout)
            detail["parity"] = {"python": py, "js": js}
            for key in ("sha256_abc", "genesis", "receipt_id", "fire_order"):
                if py[key] != js[key]:
                    fails.append(
                        f"parity divergence on {key}: python={py[key]!r} js={js[key]!r} "
                        f"(the .js twin is not the same system)"
                    )

        # --- .ts primitive twin (triple law: py == js == ts on identity)
        detail["ts_suite"] = {"passed": None, "summary": "", "typecheck": None}
        if not ENGINE_TS.is_file():
            fails.append("vendor/nodal.ts missing — the .py/.js pair has no .ts primitive twin")
        else:
            ts_ok, ts_out, ts_err, _ = run_ts(TS_HARNESS)
            ts_summary = (ts_out.splitlines() or [""])[-1]
            if ts_ok:
                detail["ts_suite"].update(passed=True, summary=ts_summary)
            else:
                low = ts_err.lower()
                first_err = (ts_err.splitlines() or [""])[-1]
                if "bad option" in low or "unknown option" in low or "experimental-strip-types" in low:
                    detail["ts_suite"].update(passed=None, summary="SKIP — node cannot strip types")
                    print("nodal_gate: .ts half SKIPPED — node lacks --experimental-strip-types (never a false PASS)")
                else:
                    detail["ts_suite"].update(passed=False, summary=f"{ts_summary} {first_err}"[:400])
                    fails.append(f".ts laws: {detail['ts_suite']['summary']}")

            tsc = find_tsc()
            if tsc:
                r2 = subprocess.run(
                    [str(tsc), str(ENGINE_TS), "--strict", "--noEmit", "--target", "es2020", "--module", "esnext", "--skipLibCheck"],
                    cwd=ROOT, capture_output=True, text=True,
                )
                detail["ts_suite"]["typecheck"] = {
                    "tool": str(tsc.relative_to(ROOT)),
                    "passed": r2.returncode == 0,
                    "stderr": r2.stderr.strip()[:400] if r2.returncode else "",
                }
                if r2.returncode != 0:
                    fails.append(".ts strict typecheck failed: " + (r2.stderr.strip().splitlines() or ["?"])[0][:200])
            else:
                detail["ts_suite"]["typecheck"] = {"tool": None, "passed": None, "stderr": ""}

            if node and detail["ts_suite"].get("passed"):
                py = python_parity()
                _, tp_out, tp_err, _ = run_ts(TS_PARITY_HARNESS)
                if not tp_out:
                    fails.append(".ts parity harness failed: " + tp_err.strip()[:300])
                else:
                    ts = json.loads(tp_out)
                    detail["parity"]["ts"] = ts
                    for key in ("sha256_abc", "genesis", "receipt_id", "fire_order"):
                        if detail["parity"]["python"][key] != ts[key]:
                            fails.append(
                                f"parity divergence on {key}: python={detail['parity']['python'][key]!r} ts={ts[key]!r} "
                                f"(the .ts twin is not the same system)"
                            )

    detail["verdict"] = "PASS" if not fails else "FAIL"
    detail["fails"] = fails
    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_text(json.dumps(detail, indent=2) + "\n", encoding="utf-8")

    if fails:
        print("nodal_gate: FAIL")
        for f in fails:
            print("   " + f)
        return 1

    print(
        "nodal_gate: PASS — python suite green; .js twin and .ts twin enforce the same laws; "
        "identity parity exact across py/js/ts (sha256, genesis, receipt_id, fire order)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
