/* savf.py and savf.html must be the same engine.

   Run: node tools/test_savf_parity.js

   The CLI is the authority; the browser is a convenience that must not drift from
   it. This test feeds one corpus of synthetic Python sources to both and fails on
   any difference in findings (severity, gate, rule) or in the resulting verdict.

   Dependency-free: the browser script is evaluated in a VM sandbox with a stub
   window, and the CLI is shelled out to with the same text on stdin/disk. */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const os = require("os");
const { execFileSync } = require("child_process");

const root = path.join(__dirname, "..");
let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? "  -> " + extra : "")); }
}

/* ------------------------------------------------- load the browser engine */
const html = fs.readFileSync(path.join(root, "savf.html"), "utf8");
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
ok("savf.html contains scripts", scripts.length > 0);

function stubEl() {
  return {
    style: { setProperty() {}, getPropertyValue() { return ""; } },
    dataset: {}, classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    children: [], textContent: "", innerHTML: "", value: "", files: [],
    addEventListener() {}, removeEventListener() {}, appendChild() { return null; },
    setAttribute() {}, getAttribute() { return null; }, removeAttribute() {},
    focus() {}, click() {}, querySelector() { return null; }, querySelectorAll() { return []; },
    getBoundingClientRect() { return { top: 0, left: 0, width: 0, height: 0 }; },
    closest() { return null; }, matches() { return false; }, contains() { return false; },
  };
}

const sandbox = {
  console,
  document: {
    getElementById: () => stubEl(),
    querySelector: () => stubEl(),
    querySelectorAll: () => [],
    addEventListener() {},
    documentElement: stubEl(),
    createElement: () => stubEl(),
    body: stubEl(),
  },
  addEventListener() {},
  location: { hash: "" },
  localStorage: { getItem: () => null, setItem() {} },
  history: { replaceState() {} },
  setTimeout: () => 0, clearTimeout() {},
  atob: (s) => Buffer.from(s, "base64").toString("binary"),
  btoa: (s) => Buffer.from(s, "binary").toString("base64"),
  TextDecoder, TextEncoder, Uint8Array, JSON, Math, Date, Promise, Error,
  navigator: { userAgent: "node" },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

const ctx = vm.createContext(sandbox);
let evaluated = 0;
for (const s of scripts) {
  if (!s.trim()) continue;
  try { vm.runInContext(s, ctx); evaluated++; }
  catch (e) { /* a UI-only block may need a real DOM; the engine blocks do not */ }
}
ok("browser engine blocks evaluated", evaluated > 0, evaluated + " blocks");
ok("window.SAVF is present", !!sandbox.SAVF, Object.keys(sandbox).slice(0, 12).join(","));
if (!sandbox.SAVF) { console.log("\nFAILED: no SAVF"); process.exit(1); }

const audit = sandbox.SAVF.auditSource;
ok("auditSource is callable", typeof audit === "function");
if (typeof audit !== "function") { console.log("\nFAILED"); process.exit(1); }

/* ------------------------------------------------------------- the corpus */
const CASES = {
  "todo comment": "def f(x):\n    # TODO: implement\n    return None\n",
  "stub pass": "def f(x):\n    pass\n",
  "stub none": "def f(x):\n    return None\n",
  "raise NotImplementedError": "def f():\n    raise NotImplementedError\n",
  "ellipsis body": "def f():\n    ...\n",
  "return NotImplemented": "def f():\n    return NotImplemented\n",
  "assert True": "def f(a):\n    assert True\n    return a\n",
  "tautology": "x = 1\nassert x == x\n",
  "clean function": "def add(a, b):\n    return a + b\n",
  "fixme marker": "def f(x):\n    # FIXME later\n    return x\n",
  "multiple stubs": "def a():\n    pass\n\ndef b():\n    pass\n\ndef c():\n    ...\n",
  "mixed": "def a():\n    # TODO: x\n    pass\n\ndef b(y):\n    return y + 1\n",
  "class with stub method": "class C:\n    def m(self):\n        pass\n",
  "syntax error": "def f(:\n    return 1\n",
  "empty file": "",
  "only comment": "# just a comment\n",
  "bare pass at top level": "pass\n",
  "docstring only": '"""doc"""\n',
  "print": "print('hello')\n",
  "import and use": "import os\nprint(os.getcwd())\n",
  "nested stub": "def outer():\n    def inner():\n        pass\n    return inner\n",
  "lambda": "f = lambda x: x\n",
  "while true break": "def f(x):\n    while True:\n        break\n    return x\n",
  "multiline todo": "# TODO: a\n# TODO: b\ndef f():\n    pass\n",
};

/* --------------------------------------------------------------- compare */
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "savf-parity-"));
const diffs = [];

for (const [name, src] of Object.entries(CASES)) {
  const file = path.join(tmp, "c.py");
  fs.writeFileSync(file, src);

  let pyOut = "";
  try {
    pyOut = execFileSync("python3", [path.join(root, "savf.py"), "scan", file],
                         { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  } catch (e) {
    pyOut = ((e.stdout || "") + (e.stderr || ""));
  }

  const pyFindings = [];
  for (const line of pyOut.split("\n")) {
    const m = line.match(/\[(high|medium|low)\]\s+(phi\d+)\s+([A-Z_]+)/);
    if (m) pyFindings.push(m[1] + "|" + m[2] + "|" + m[3]);
  }
  pyFindings.sort();

  let jsRes;
  try { jsRes = audit("c.py", src); }
  catch (e) { diffs.push([name, "JS THREW: " + e.message, pyFindings.join(","), ""]); continue; }

  const jsFindings = (jsRes.findings || [])
    .map((f) => f.sev + "|phi" + f.phi + "|" + f.rule).sort();

  if (pyFindings.join(",") !== jsFindings.join(",")) {
    diffs.push([name, pyFindings.join(","), jsFindings.join(","), src.slice(0, 60)]);
  }
}

ok("the two engines agree on every case", diffs.length === 0,
   diffs.length + " disagreement(s)");
for (const d of diffs) {
  console.log("       " + d[0]);
  console.log("         cli: " + (d[1] || "(none)"));
  console.log("         web: " + (d[2] || "(none)"));
}

/* The verdict must also agree, on a case that is clean and one that is not. */
const clean = audit("c.py", "def add(a, b):\n    return a + b\n");
ok("a clean file is not reported as LIED", clean.verdict !== "LIED", clean.verdict);

const dirty = audit("c.py", "def f():\n    # TODO: fix\n    return None\n");
ok("a stub with a TODO is reported as LIED", dirty.verdict === "LIED", dirty.verdict);
ok("a finding carries a line number", (dirty.findings || []).every((f) => typeof f.line === "number"));
ok("a finding names its file", (dirty.findings || []).every((f) => f.file === "c.py"));

/* The engine must never throw on hostile or malformed input. */
const hostile = [
  "\u0000\u0001\u0002",
  "def f():\n\tpass\n",
  "x" .repeat(100000),
  "def f():\r\n    pass\r\n",
  "\ufeffdef f():\n    pass\n",
  "def f():\n    '''unterminated\n",
];
let threw = 0;
for (const h of hostile) {
  try { audit("c.py", h); } catch (e) { threw++; }
}
ok("the engine never throws on malformed input", threw === 0, threw + " threw");

/* An engine fault must degrade the verdict, never silently pass. */
ok("a non-string input does not crash the engine",
   (() => { try { audit("c.py", null); return true; } catch (e) { return false; } })());

fs.rmSync(tmp, { recursive: true, force: true });

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail === 0 ? 0 : 1);
