/* The exp/log pair must agree with itself at the extremes.

   Run: node tools/test_savf_numeric.js

   f maps [0,L] onto [0,1] and g is its inverse. Both are defined for every
   b>0, b!=1, k!=0, L>0, but the naive (b^(ks)-1)/(b^(kL)-1) overflows once
   k*L*log(b) exceeds ~709: the denominator becomes Infinity, and
   Infinity/Infinity is NaN -- at s=L, where the answer is exactly 1. Python
   raised OverflowError on the same inputs, so the two ports disagreed on a
   value both could compute. These cases pin the fix in both engines. */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const { execFileSync } = require("child_process");

const root = path.join(__dirname, "..");
let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? "  -> " + extra : "")); }
}

const html = fs.readFileSync(path.join(root, "savf.html"), "utf8");
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const sandbox = { console, Math, JSON, Error, isFinite, Infinity, NaN, Object, Array, String, Number };
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
const ctx = vm.createContext(sandbox);
for (const s of scripts) { if (!s.trim()) { continue; } try { vm.runInContext(s, ctx); } catch (e) {} }

ok("SAVF core is present", !!(sandbox.SAVF && sandbox.SAVF.core));
if (!sandbox.SAVF || !sandbox.SAVF.core) { console.log("\nFAILED"); process.exit(1); }
const C = sandbox.SAVF.core;

/* ---- f_exp: endpoints are exact, and nothing returns NaN ---- */
const F = [
  // [s, b, k, L, expected]
  [0, 2, 50, 50, 0],
  [50, 2, 50, 50, 1],
  [0, 10, 2, 50, 0],
  [50, 10, 2, 50, 1],
  [0, 0.5, -50, 50, 0],
  [50, 0.5, -50, 50, 1],
  [0, 2, 5, 10, 0],
  [10, 2, 5, 10, 1],
];
for (const [s, b, k, L, want] of F) {
  const v = C.fExp(s, b, k, L);
  ok(`fExp(${s},${b},${k},${L}) is ${want}`, v === want, String(v));
}

/* overflow region: a finite value, never NaN/Infinity */
for (const c of [[25, 2, 50, 50], [10, 2, 50, 50], [25, 0.5, -50, 50], [5, 2, 40, 50]]) {
  const v = C.fExp(c[0], c[1], c[2], c[3]);
  ok(`fExp(${c.join(",")}) is finite`, isFinite(v), String(v));
  ok(`fExp(${c.join(",")}) stays in [0,1]`, v >= 0 && v <= 1, String(v));
}

/* monotone in s where the map is not collapsed */
{
  let prev = -1, mono = true;
  for (let i = 0; i <= 20; i++) {
    const v = C.fExp(i * 0.05 * 10, 2, 5, 10);
    if (v < prev) { mono = false; }
    prev = v;
  }
  ok("fExp is non-decreasing in s", mono);
}

/* ---- g_log: inverts f at the extremes, refuses only where it must ---- */
const G = [
  [0.5, 2, 50, 50],
  [0.5, 2, 50, 25],
  [0.999, 2, 50, 50],
  [0.1, 10, 2, 20],
  [0.9, 3.7, 4, 9],
];
for (const [u, b, k, L] of G) {
  const s = C.gLog(u, b, k, L);
  ok(`gLog(${u},${b},${k},${L}) is finite`, isFinite(s), String(s));
  const back = C.fExp(s, b, k, L);
  ok(`fExp(gLog(u)) round-trips within 1e-9 (u=${u}, b=${b}, k=${k}, L=${L})`,
     Math.abs(back - u) < 1e-9, `${back} vs ${u}`);
}
ok("gLog(0, ...) is exactly 0", C.gLog(0, 2, 50, 50) === 0, String(C.gLog(0, 2, 50, 50)));

/* a collapsed f (k*L*log b below ~ -36.7) must still be refused, not silently wrong */
{
  let threw = false;
  try { C.gLog(0.5, 10, -30, 40); } catch (e) { threw = true; }
  ok("gLog refuses where f has collapsed", threw);
}

/* ---- the two ports must agree on every case above ---- */
const PY_PROBE = `
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("savfref", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
data = json.load(sys.stdin)
out = {"f": [m.f_exp(*c) for c in data["f"]], "g": [m.g_log(*c) for c in data["g"]]}
json.dump(out, sys.stdout)
`;
const pyCases = JSON.stringify({ f: F.map((c) => c.slice(0, 4)), g: G });
const py = execFileSync("python3", ["-c", PY_PROBE, path.join(root, "savf.py")], {
  input: pyCases, encoding: "utf8", stdio: ["pipe", "pipe", "pipe"],
});
const parsed = JSON.parse(py);
let diffs = [];
for (let i = 0; i < F.length; i++) {
  const js = C.fExp(F[i][0], F[i][1], F[i][2], F[i][3]);
  if (Math.abs(js - parsed.f[i]) > 1e-12 * Math.max(1, Math.abs(js))) {
    diffs.push(`f[${i}] js=${js} py=${parsed.f[i]}`);
  }
}
for (let i = 0; i < G.length; i++) {
  const js = C.gLog(G[i][0], G[i][1], G[i][2], G[i][3]);
  if (Math.abs(js - parsed.g[i]) > 1e-12 * Math.max(1, Math.abs(js))) {
    diffs.push(`g[${i}] js=${js} py=${parsed.g[i]}`);
  }
}
ok("python and browser agree on every numeric case", diffs.length === 0, diffs.join("; "));

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
