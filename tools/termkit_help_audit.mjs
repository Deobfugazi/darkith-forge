#!/usr/bin/env node
/* =====================================================================
   termkit_help_audit.mjs — the invariant debugger for TermKit help.

   The dual-register manual (build/termkit-help.js) claims specific outputs
   for specific commands. This tool does not trust the claim: it extracts the
   REAL TermKit 2.0 core from the canonical shell, runs every fixture in a
   fresh Shell, and compares stdout + exit status to what the manual shows.

   It then drives the help builtin itself and checks both registers render,
   so a manual that ships without its engine wiring is caught here.

   Usage:
       node tools/termkit_help_audit.mjs [--verbose]
   Exit 0 = the manual and the engine agree on every fixture.
   ===================================================================== */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const here = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(here, "..");
const SHELL = path.join(ROOT, "darkith home forge.html");
const PAYLOAD = path.join(ROOT, "build", "termkit-help.js");

let pass = 0, fail = 0;
const failures = [];
function ok(name, cond, detail) {
  if (cond) { pass++; if (process.argv.includes("--verbose")) console.log(`  ok   ${name}`); }
  else { fail++; failures.push(name + (detail ? "  -- " + detail : "")); console.log(`  FAIL ${name}${detail ? "  -- " + detail : ""}`); }
}

/* ---- extract the TermKit core (Part A + Part B) from the shell ---------- */
function extractCore(src) {
  const lines = src.split("\n");
  let a = -1, b = -1;
  for (let i = 0; i < lines.length; i++) {
    if (a < 0 && /Darkith Forge Terminal — TermKit 2\.0/.test(lines[i])) a = i;
    if (lines[i].includes("global.__TermKitPartB = { Shell: Shell, VERSION: VERSION };")) b = i;
  }
  if (a < 0 || b < 0) throw new Error("could not locate the TermKit core in " + SHELL);
  let open = a;
  while (open < lines.length && !/^\(function \(global\) \{/.test(lines[open])) open++;
  return lines.slice(open, b + 2).join("\n");   // +2: include the IIFE close
}

const src = fs.readFileSync(SHELL, "utf8");
const core = extractCore(src);
const tmp = path.join(ROOT, ".forge_work", "termkit-core.audit.js");
fs.mkdirSync(path.dirname(tmp), { recursive: true });
fs.writeFileSync(tmp, "const window = globalThis;\n" + core + "\n");

const require = createRequire(import.meta.url);
require(tmp);
require(PAYLOAD);

const T = globalThis.TermKit;
const H = globalThis.__TermKitHelp;

ok("engine: TermKit.Shell exported", T && typeof T.Shell === "function");
ok("manual: __TermKitHelp exported", H && typeof H.render === "function");

/* ---- run every fixture against the real engine ------------------------- */
function run(cmd) {
  const sh = new T.Shell();
  const r = sh.run(cmd);
  return { out: (r.text || "").replace(/\n$/, ""), status: r.status, err: (r.err || []).join("\n") };
}

for (const f of H.fixtures) {
  let got;
  try { got = run(f.cmd); }
  catch (e) { got = { out: "THREW: " + e.message, status: -1, err: "" }; }
  ok(`fixture ${f.id}`,
     got.out === f.expect && got.status === f.status,
     `cmd=${JSON.stringify(f.cmd)} expected=${JSON.stringify(f.expect)}(${f.status}) got=${JSON.stringify(got.out)}(${got.status})`);
}

/* ---- the manual's dev table must equal the engine's results ------------- */
const dev = H.render("dev");
ok("dev register renders", Array.isArray(dev) && dev.length > 20);
ok("dev register names the debugger", dev.some(l => l.includes("termkit_help_audit.mjs")));
for (const f of H.fixtures) {
  const exp = f.expect === "" ? "(none)" : f.expect.replace(/\n/g, "\\n");
  ok(`dev table shows ${f.id}`, dev.some(l => l.includes("$ " + f.cmd) && l.includes(exp)));
}

/* ---- the beginner register must be novice-facing and sample-bearing ----- */
const beg = H.render("beginner");
ok("beginner register renders", Array.isArray(beg) && beg.length > 20);
ok("beginner teaches with samples", beg.filter(l => /^\s{2}\$ /.test(l)).length >= 5);
ok("beginner avoids the word 'invariant'", !beg.join("\n").toLowerCase().includes("invariant"));
ok("beginner points at help dev", beg.some(l => l.includes("help dev")));

/* ---- the manual's builtin list must equal the engine's ---------------- */
{
  const sh = new T.Shell();
  const engine = Object.keys(sh.builtins).sort();
  const listed = H.builtins.slice().sort();
  ok("builtin list matches the engine",
     JSON.stringify(engine) === JSON.stringify(listed),
     `engine=${engine.length} manual=${listed.length}`);
}

/* ---- the fracture-closure section must exist and be reasoned ----------- */
ok("closure section present", H.closure.length >= 5);
ok("every closure has a reason", H.closure.every(c => c.because && c.because.length > 40));
ok("comparison table present", H.compare.length >= 8);

/* ---- drive the help builtin itself (both registers) -------------------- */
if (T && typeof T.Shell === "function") {
  const sh = new T.Shell();
  const b = sh.run("help beginner");
  const d = sh.run("help dev");
  ok("help beginner runs", b.status === 0 && /beginner guide/.test(b.text));
  ok("help dev runs", d.status === 0 && /developer \/ AI register/.test(d.text));
  ok("help beginner != help dev", b.text !== d.text);
  const plain = sh.run("help");
  ok("plain help still lists commands", /COMMANDS/.test(plain.text) || /stateful shell/.test(plain.text));
}

console.log(`\n  TERMKIT-HELP-AUDIT: ${fail === 0 ? "PASS" : "FAIL"} (${pass} passed, ${fail} failed, ${H.fixtures.length} fixtures)`);
if (fail) { for (const x of failures) console.log("    " + x); process.exit(1); }
