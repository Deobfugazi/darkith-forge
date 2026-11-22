#!/usr/bin/env node
/*
 * Tests for verdict honesty in `savf gate`.
 *
 * The formulary's whole claim is that a verdict means something. That claim
 * breaks if a mistyped argument convicts the code under audit.
 *
 * phi4 (reach) and phi7 (mutation) shell out to a caller-supplied command.
 * When that command is wrong -- a --reach-test module that does not import, or
 * baseline tests that are red before any mutation -- the harness raises. Those
 * exceptions were caught and recorded as "fail", and phi4/phi7 are hard/soft
 * gates, so a typo produced:
 *
 *     VERDICT: LIED
 *
 * LIED is the strongest accusation the tool can make: the code lies. A broken
 * command line says nothing whatsoever about the source. The verdict must fall
 * back to REVIEW ("nobody attested this"), the same rule the scanner already
 * applies to source too deep to parse.
 *
 * These tests pin that boundary in both directions, so the fix cannot silently
 * become a blanket pass: real tamper must still be LIED, and a genuinely weak
 * test suite must still be BLOCKED.
 *
 * Run: node tools/test_savf_gate_verdict.js
 */
"use strict";

const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const CLI = path.resolve(__dirname, "..", "savf.py");
const KEY = "gate-verdict-test-key";

let pass = 0;
let fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name + (detail ? "  -> " + detail : "")); }
}

/* The manifest gate needs a key; supply one here so the test is self-contained
   and does not depend on the caller's environment. */
const ENV = Object.assign({}, process.env, { SAVF_KEY: KEY });

function sh(cmd, args, cwd) {
  try {
    return { code: 0, out: execFileSync(cmd, args, { cwd, env: ENV, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }) };
  } catch (e) {
    return { code: e.status === undefined ? -1 : e.status, out: (e.stdout || "") + (e.stderr || "") };
  }
}

const savf = (cwd, args) => sh("python3", [CLI].concat(args), cwd);

/* A throwaway project: one module, one test that genuinely kills its mutants. */
function project({ source, test }) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "savf-gate-"));
  fs.writeFileSync(path.join(dir, "mod.py"), source);
  fs.writeFileSync(path.join(dir, "test_mod.py"), test);
  fs.writeFileSync(path.join(dir, "runner.py"),
    "import mod\nassert mod.f(1)==2\nassert mod.f(0)==1\nassert mod.f(-1)==0\n");
  return dir;
}

const GOOD_SRC = "def f(x):\n    return x + 1\n";
const GOOD_TEST = "import mod\nassert mod.f(1)==2\nassert mod.f(0)==1\nassert mod.f(-1)==0\n";

function frozen(opts) {
  const dir = project(opts);
  savf(dir, ["freeze", "mod.py", "test_mod.py"]);
  savf(dir, ["manifest", "create", "mod.py", "test_mod.py"]);
  return dir;
}

function verdictOf(dir, reach) {
  const r = savf(dir, ["gate", "--src", "mod.py", "--test-cmd", "python3 runner.py",
                       "--reach-test", reach]);
  const line = (r.out.match(/VERDICT:\s*(\w+)/) || [])[1] || "";
  return { verdict: line, out: r.out };
}

/* --- 1. a mistyped --reach-test must not convict ------------------------- */
{
  const dir = frozen({ source: GOOD_SRC, test: GOOD_TEST });
  const r = savf(dir, ["gate", "--src", "mod.py", "--test-cmd", "python3 runner.py",
                       "--reach-test", "no_such_module_xyz"]);
  ok("a --reach-test module that does not import does not yield LIED",
     !/VERDICT:\s*LIED/.test(r.out), r.out.match(/VERDICT:.*/)?.[0]);
  ok("it reports the harness error as unattested",
     /harness error, nothing attested/.test(r.out),
     (r.out.match(/phi4.*/) || [""])[0].slice(0, 120));
  ok("phi4 is marginal, not fail",
     /phi4\s+marginal/.test(r.out), (r.out.match(/phi4.*/) || [""])[0].slice(0, 80));
}

/* --- 2. red baseline tests must not convict either ---------------------- */
{
  const dir = frozen({ source: GOOD_SRC, test: GOOD_TEST });
  fs.writeFileSync(path.join(dir, "red.py"), "import mod\nassert mod.f(1)==999\n");
  const r = savf(dir, ["gate", "--src", "mod.py", "--test-cmd", "python3 red.py",
                       "--reach-test", "test_mod"]);
  ok("baseline-red tests do not yield LIED", !/VERDICT:\s*LIED/.test(r.out),
     r.out.match(/VERDICT:.*/)?.[0]);
  ok("phi7 is marginal with a harness note", /phi7\s+marginal/.test(r.out),
     (r.out.match(/phi7.*/) || [""])[0].slice(0, 80));
}

/* --- 3. the fix must not become a blanket pass -------------------------- */
{
  const dir = frozen({ source: GOOD_SRC, test: GOOD_TEST });
  fs.writeFileSync(path.join(dir, "weak.py"), "import mod\nassert callable(mod.f)\n");
  const r = savf(dir, ["gate", "--src", "mod.py", "--test-cmd", "python3 weak.py",
                       "--reach-test", "test_mod"]);
  ok("genuinely weak tests still fail phi7", /phi7\s+fail/.test(r.out),
     (r.out.match(/phi7.*/) || [""])[0].slice(0, 80));
  ok("genuinely weak tests still block the verdict", /VERDICT:\s*BLOCKED/.test(r.out),
     r.out.match(/VERDICT:.*/)?.[0]);
}

/* --- 4. real tamper must still be LIED ---------------------------------- */
{
  const dir = frozen({ source: GOOD_SRC, test: GOOD_TEST });
  fs.writeFileSync(path.join(dir, "mod.py"), "def f(x):\n    return x + 5\n");
  const r = verdictOf(dir, "test_mod");
  ok("tampering with a frozen file still yields LIED", r.verdict === "LIED", r.verdict);
  ok("phi0 still names the changed file", /changed after freeze: mod\.py/.test(r.out),
     (r.out.match(/phi0.*/) || [""])[0].slice(0, 80));
}

/* --- 5. a clean, attested run reaches REVIEW, never a bare PASS --------- */
{
  const dir = frozen({ source: GOOD_SRC, test: GOOD_TEST });
  const r = verdictOf(dir, "test_mod");
  ok("with phi5/phi8/phi9 unattested the verdict is REVIEW", r.verdict === "REVIEW", r.verdict);
  ok("it never claims PASS without evidence", r.verdict !== "PASS", r.verdict);
  ok("phi4 and phi7 actually pass on a good project",
     /phi4\s+pass/.test(r.out) && /phi7\s+pass/.test(r.out),
     [ (r.out.match(/phi4.*/) || [""])[0].slice(0, 40),
       (r.out.match(/phi7.*/) || [""])[0].slice(0, 40) ].join(" | "));
}

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail === 0 ? 0 : 1);
