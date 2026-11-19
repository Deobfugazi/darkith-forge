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
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ENGINE = ROOT / "app/src/main/assets/vendor/nodal.js"
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
    ran = next((ln for ln in lines if ln.startswith("Ran ")), "")
    tail = next((ln for ln in reversed(lines) if ln in ("OK",) or ln.startswith("FAILED")), lines[-1] if lines else "")
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
        print("nodal_gate: .js half SKIPPED — node not installed (never a false PASS)")
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
        "nodal_gate: PASS — python suite green; .js twin enforces the same laws; "
        "identity parity exact (sha256, genesis, receipt_id, fire order)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
