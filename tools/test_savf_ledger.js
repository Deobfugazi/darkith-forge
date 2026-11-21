#!/usr/bin/env node
/*
 * Tests for `savf ledger` — the proof-carrying claims validator.
 *
 * The ledger is the part of SAVF that decides whether a claim is allowed to
 * stand, so it has to hold two lines at once:
 *
 *   1. A claim without evidence must never come out "verified".
 *   2. A malformed claim must be reported, never crash the tool. A validator
 *      that dies on bad input is a validator that can be silenced by bad input.
 *
 * Line 2 is a regression: a claim with no `id` used to hit
 * `f"{r['id']:8s}"` and raise TypeError, taking down the whole run.
 *
 * Run: node tools/test_savf_ledger.js
 */
"use strict";

const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const CLI = path.join(ROOT, "savf.py");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "savf-ledger-"));

let pass = 0;
let fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name + (detail ? "  -> " + detail : "")); }
}

function ledger(claims, run) {
  const file = path.join(tmp, "claims-" + Math.random().toString(36).slice(2) + ".json");
  fs.writeFileSync(file, JSON.stringify(claims));
  const args = [CLI, "ledger", file].concat(run ? ["--run"] : []);
  try {
    const out = execFileSync("python3", args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    return { code: 0, out };
  } catch (e) {
    return { code: e.status === undefined ? -1 : e.status, out: (e.stdout || "") + (e.stderr || "") };
  }
}

/* --- a claim without evidence is never verified ------------------------- */
const noEvidence = ledger([{ id: "a", kind: "N", statement: "x is true" }]);
ok("a claim with no evidence is not verified", !/verified/.test(noEvidence.out), noEvidence.out.trim());
ok("a claim with no evidence is reported as a problem", noEvidence.code === 1, "exit " + noEvidence.code);

/* --- a false claim fails when its evidence is run ----------------------- */
const lie = ledger([
  { id: "a", kind: "N", statement: "2+2=5",
    evidence: { cmd: "python3 -c \"assert 2+2==5\"", expect: "" } },
], true);
ok("a false claim's evidence fails", /failed/.test(lie.out), lie.out.trim());
ok("a false claim makes the run fail", lie.code === 1, "exit " + lie.code);

/* --- a true claim verifies when its evidence is run --------------------- */
const truth = ledger([
  { id: "a", kind: "N", statement: "2+2=4",
    evidence: { cmd: "python3 -c \"assert 2+2==4; print('ok')\"", expect: "ok" } },
], true);
ok("a true claim's evidence verifies", /verified/.test(truth.out), truth.out.trim());

/* --- derivation must not launder an unproven parent --------------------- */
const cascade = ledger([
  { id: "bad", kind: "N", statement: "2+2=5",
    evidence: { cmd: "python3 -c \"assert 2+2==5\"", expect: "" } },
  { id: "derived", kind: "R", statement: "from bad", derived_from: ["bad"] },
], true);
ok("a claim derived from a failed parent is not verified",
   /derived\s+R->R\s+unsupported/.test(cascade.out), cascade.out.trim());

/* --- a witness with no external referent is downgraded ------------------ */
const witness = ledger([{ id: "w", kind: "W", statement: "I saw it" }]);
ok("a witness with no external referent is downgraded",
   /w\s+W->D/.test(witness.out), witness.out.trim());

/* --- malformed claims are reported, never crash ------------------------- */
const malformed = [
  { kind: "D", statement: "no id at all" },
  { id: "k", kind: "Z", statement: "unknown kind" },
  { id: "dup", kind: "D", statement: "one" },
  { id: "dup", kind: "D", statement: "two" },
  { id: "c1", kind: "R", statement: "cycle a", derived_from: ["c2"] },
  { id: "c2", kind: "R", statement: "cycle b", derived_from: ["c1"] },
];
const bad = ledger(malformed);
ok("malformed claims do not crash the tool", bad.code !== -1 && !/Traceback/.test(bad.out),
   bad.out.trim().slice(0, 160));
ok("a claim with no id is reported", /no id/.test(bad.out), bad.out.trim().slice(0, 160));
ok("an unknown kind is reported", /unknown kind/.test(bad.out));
ok("a duplicate id is reported", /duplicate id/.test(bad.out));
ok("a cycle is reported", /cycle/.test(bad.out));
ok("malformed claims make the run fail", bad.code === 1, "exit " + bad.code);

/* --- a non-array ledger is refused with a message, not a traceback ------ */
const wrongShape = ledger({ not: "an array" });
ok("a non-array ledger is refused cleanly",
   wrongShape.code !== -1 && /array/.test(wrongShape.out) && !/Traceback/.test(wrongShape.out),
   wrongShape.out.trim().slice(0, 160));

fs.rmSync(tmp, { recursive: true, force: true });

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail === 0 ? 0 : 1);
