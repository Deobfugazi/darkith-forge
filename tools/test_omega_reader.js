/* Tests for omega-reader.html — the single-file library reader.
   Run: node tools/test_omega_reader.js

   Dependency-free: no browser, no jsdom, no npm. The test reads the built file,
   decodes the embedded corpus, and then exercises the renderer, the search
   index and the outline directly in a VM sandbox.

   What this proves:
     - the corpus in the file decodes and agrees with docs/kb_manifest.json
     - every indexed document is present, non-empty and byte-identical on disk
     - the markdown renderer emits only whitelisted tags (no injection surface)
     - hostile input cannot introduce a script, an on* attribute or a
       javascript: href
     - an unclosed fence cannot swallow the rest of the document
     - outline ids match the heading ids the renderer actually emits
     - search finds what exists and nothing that does not
     - the file on disk is the current build */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const zlib = require("zlib");

const root = path.join(__dirname, "..");
const file = path.join(root, "omega-reader.html");
const html = fs.readFileSync(file, "utf8");

let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? "  -> " + extra : "")); }
}

/* ---------------------------------------------------------------- payload */
const payloadMatch = html.match(
  /<script id="corpus-b64" type="text\/plain">([A-Za-z0-9+/=]+)<\/script>/);
ok("corpus payload present", !!payloadMatch);
if (!payloadMatch) { console.log("\nFAILED: no payload"); process.exit(1); }

const docs = JSON.parse(zlib.gunzipSync(Buffer.from(payloadMatch[1], "base64")).toString("utf8"));
ok("payload decodes to a document array", Array.isArray(docs) && docs.length > 0,
   "got " + (Array.isArray(docs) ? docs.length : typeof docs));

/* ------------------------------------------------------- manifest agreement */
const manifest = JSON.parse(fs.readFileSync(path.join(root, "docs", "kb_manifest.json"), "utf8"));
const indexed = manifest.files.filter((f) => f.path !== "omega-reader.html");
ok("document count matches the index", docs.length === indexed.length,
   docs.length + " in reader, " + indexed.length + " indexed");

const byPath = Object.create(null);
for (const d of docs) byPath[d.p] = d;

const missing = [], mismatched = [], empty = [];
for (const f of indexed) {
  const d = byPath[f.path];
  if (!d) { missing.push(f.path); continue; }
  if (d.n !== f.bytes) mismatched.push(f.path);
  if (!d.t || !d.t.length) empty.push(f.path);
}
ok("every indexed document is in the reader", missing.length === 0, missing.slice(0, 3).join(", "));
ok("every document's byte count matches the index", mismatched.length === 0, mismatched.slice(0, 3).join(", "));
ok("no document is empty", empty.length === 0, empty.slice(0, 3).join(", "));

const drifted = [];
for (const f of indexed) {
  const d = byPath[f.path];
  if (!d) continue;
  const disk = fs.readFileSync(path.join(root, f.path), "utf8");
  if (d.t !== disk) drifted.push(f.path);
}
ok("document text is byte-identical to the files on disk", drifted.length === 0,
   drifted.slice(0, 3).join(", "));

/* --------------------------------------------------------------- renderer */
const scriptBlocks = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map((m) => m[1]);
const appSrc = scriptBlocks.find((s) => s.includes("function markdown("));
ok("renderer script found", !!appSrc);
if (!appSrc) { console.log("\nFAILED: no renderer"); process.exit(1); }

/* A stub element that accepts anything the reader throws at it. The reader wires
   its listeners at module scope, so getElementById must never return null. */
function stubEl() {
  const n = {
    style: { setProperty() {}, getPropertyValue() { return ""; } },
    dataset: {}, classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    children: [], firstChild: null, textContent: "", innerHTML: "", value: "",
    scrollTop: 0, scrollHeight: 0, offsetHeight: 0, offsetTop: 0, tabIndex: 0,
    addEventListener() {}, removeEventListener() {}, appendChild() { return null; },
    removeChild() {}, insertBefore() { return null; }, setAttribute() {}, getAttribute() { return null; },
    removeAttribute() {}, focus() {}, blur() {}, click() {}, scrollTo() {}, scrollIntoView() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    getBoundingClientRect() { return { top: 0, left: 0, width: 0, height: 0, bottom: 0, right: 0 }; },
    closest() { return null; }, matches() { return false; }, contains() { return false; },
  };
  return n;
}

const sandbox = {
  console,
  document: {
    getElementById: () => stubEl(),
    querySelector: () => stubEl(),
    querySelectorAll: () => [],
    addEventListener: () => {},
    documentElement: stubEl(),
    createElement: () => stubEl(),
    body: stubEl(),
  },
  addEventListener: () => {},
  location: { hash: "" },
  localStorage: { getItem: () => null, setItem: () => {} },
  history: { replaceState: () => {} },
  setTimeout: () => 0,
  clearTimeout: () => {},
  atob: (s) => Buffer.from(s, "base64").toString("binary"),
  TextDecoder, Uint8Array, JSON, Math, Date, String, Number, Object, Array, RegExp, Error,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

const exposed = appSrc.replace(
  /boot\(\);\s*\}\)\(\);\s*$/,
  "globalThis.__T = { markdown: markdown, outlineFor: outlineFor," +
  " looksLikeMarkdown: looksLikeMarkdown, search: search," +
  " setCorpus: function(c){ CORPUS = c; SEARCH_INDEX = null; } };\n})();"
);
ok("renderer harness installed", exposed !== appSrc);

const ctx = vm.createContext(sandbox);
try {
  vm.runInContext(exposed, ctx);
} catch (e) {
  ok("renderer evaluates", false, e.message);
}
const T = sandbox.__T || {};
ok("renderer exposes its parts", !!T.markdown);

const ALLOWED = new Set(["H1", "H2", "H3", "H4", "H5", "H6", "P", "UL", "OL", "LI",
  "PRE", "CODE", "BLOCKQUOTE", "TABLE", "THEAD", "TBODY", "TR", "TH", "TD",
  "HR", "STRONG", "EM", "DEL", "A", "BR"]);

function tagsOf(s) {
  const out = [];
  for (const m of s.matchAll(/<\s*\/?\s*([a-zA-Z][a-zA-Z0-9]*)/g)) out.push(m[1].toUpperCase());
  return out;
}

if (T.markdown) {
  const normal = T.markdown([
    "# Title", "", "Text with **bold**, *italic*, `code` and [a link](https://example.com).",
    "", "## Section", "", "- one", "- two", "", "1. first", "2. second",
    "", "> quote", "", "| a | b |", "|---|---|", "| 1 | 2 |",
    "", "```js", "const x = 1;", "```", "", "---",
  ].join("\n"));
  const bad = tagsOf(normal).filter((t) => !ALLOWED.has(t));
  ok("normal markdown emits only whitelisted tags", bad.length === 0, bad.join(","));
  ok("headings are rendered", /<h1[^>]*>Title<\/h1>/.test(normal));
  ok("bold/italic/code are rendered", /<strong>bold<\/strong>/.test(normal)
     && /<em>italic<\/em>/.test(normal) && /<code>code<\/code>/.test(normal));
  ok("a safe link keeps its href", /<a href="https:\/\/example\.com"/.test(normal));
  ok("table becomes a table", /<table[^>]*>/.test(normal) && /<td>1<\/td>/.test(normal));
  ok("fenced code becomes pre/code", /<pre[^>]*><code[^>]*>const x = 1;<\/code><\/pre>/.test(normal));

  const hostile = [
    "<img src=x onerror=alert(1)>",
    "<script>alert(2)</script>",
    "[a](javascript:alert(3))",
    "[a](JaVaScRiPt:alert(4))",
    "[a](data:text/html,<script>alert(5)</script>)",
    "<iframe src=javascript:alert(6)></iframe>",
    "<svg onload=alert(7)>",
    '"><img src=x onerror=alert(8)>',
    "# <img src=x onerror=alert(9)>",
    "| a | <img src=x onerror=alert(10)> |",
    "|---|---|",
    "| b | c |",
    "> <img src=x onerror=alert(11)>",
    "- <img src=x onerror=alert(12)>",
    "```",
    "<script>alert(13)</script>",
    "```",
    "<object data=javascript:alert(14)>",
    "<style>@import 'javascript:alert(15)'</style>",
  ].join("\n");
  const evil = T.markdown(hostile);
  const evilBad = tagsOf(evil).filter((t) => !ALLOWED.has(t));
  ok("hostile input emits only whitelisted tags", evilBad.length === 0, evilBad.join(","));
  /* Escaped payload text legitimately contains the string "onerror="; only an
     attribute inside a real tag is a hole. Parse tags, then look for handlers. */
  const realTags = evil.match(/<[^>]+>/g) || [];
  const handlerTags = realTags.filter((t) => /\son[a-z]+\s*=/i.test(t));
  ok("no real tag carries an on* attribute", handlerTags.length === 0,
     handlerTags.slice(0, 2).join(" | "));
  ok("hostile input produces no javascript: href", !/href\s*=\s*["']?\s*javascript:/i.test(evil));
  ok("hostile input produces no script element", !/<\s*script/i.test(evil));
  ok("hostile input produces no iframe/svg/object/style",
     !/<\s*(iframe|svg|object|embed|style|meta|base)/i.test(evil));
  ok("the hostile payload is still visible to the reader", evil.includes("&lt;script&gt;"));

  const unclosed = T.markdown([
    "intro", "", "```bash", "echo hi", "", "## A real heading", "", "body text here",
  ].join("\n"));
  ok("an unclosed fence still yields the later heading",
     /<h2[^>]*>A real heading<\/h2>/.test(unclosed), unclosed.slice(0, 160));
  ok("an unclosed fence still yields the later paragraph", /body text here/.test(unclosed));

  const doc = { p: "t.md", t: "# One\n\n## Two\n\n### Three\n\n## Two\n" };
  const heads = T.outlineFor(doc);
  const ids = [...T.markdown(doc.t).matchAll(/<h[1-6]\s+id="([^"]+)"/g)].map((m) => m[1]);
  ok("outline produces one entry per heading", heads.length === 4, "got " + heads.length);
  ok("every outline id exists as a heading id", heads.every((h) => ids.includes(h.id)),
     JSON.stringify(heads.map((h) => h.id)) + " vs " + JSON.stringify(ids));
  ok("duplicate headings get distinct ids", new Set(ids).size === ids.length);

  ok("a markdown-shaped .txt is detected", T.looksLikeMarkdown("# A\n\n## B\n\ntext\n") === true);
  ok("a shell transcript is not treated as markdown",
     T.looksLikeMarkdown("```bash\n# comment\nls -la\n# another\n```\n") === false);
}

/* ----------------------------------------------------------------- search */
if (T.search && T.setCorpus) {
  T.setCorpus(docs);
  const hit = T.search("noveltreatise");
  ok("search finds a term that exists", hit.length > 0, "got " + hit.length);
  ok("search returns nothing for a term that does not",
     T.search("zzzznottinthecorpuszzzz").length === 0);
  ok("search ignores case", T.search("NOVELTREATISE").length === hit.length);
  ok("search results carry the document and a first-hit offset",
     hit.length > 0 && typeof hit[0].first === "number" && hit[0].doc && hit[0].doc.p);
  ok("an empty query matches nothing", T.search("").length === 0);
  /* A document whose text begins with the query matches at offset 0, which is
     falsy. Regression: a `!first` guard silently dropped every such document. */
  const firstWord = docs.find((d) => /^[A-Za-z]{4,}/.test(d.t));
  if (firstWord) {
    const w = firstWord.t.match(/^[A-Za-z]{4,}/)[0];
    const found = T.search(w).some((h) => h.doc.p === firstWord.p);
    ok("a document matching at offset 0 is still returned", found,
       w + " in " + firstWord.p);
  }
}

/* ------------------------------------------------------------- build state */
try {
  require("child_process").execFileSync(
    "python3", [path.join(__dirname, "reader_build.py"), "--check"], { stdio: "pipe" });
  ok("the reader on disk is the current build", true);
} catch (e) {
  const msg = ((e.stderr || e.stdout || "") + "").trim();
  ok("the reader on disk is the current build", false,
     msg.split("\n").pop() || "reader_build.py --check failed");
}

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail === 0 ? 0 : 1);
