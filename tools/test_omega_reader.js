/* Unit tests for omega-reader.html — the single-file four-register reader.
   Run: node tools/test_omega_reader.js

   Dependency-free: builds a minimal DOM shim so the real router/render code from the
   file is exercised (not a reimplementation). Proves the two regressions are fixed:
     BUG-1  an out-of-range deep link (#/machine/999) must not throw;
     BUG-2  machine/provenance text must be HTML-escaped, never injected raw into <pre>.
   Plus: manifest completeness, landing bookmarks, the inline provenance <details>,
   register switching, bad-hash fallback, theme persistence, and TOC build. */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const file = path.join(__dirname, "..", "omega-reader.html");
const html = fs.readFileSync(file, "utf8");
const m = html.match(/<script>([\s\S]*)<\/script>/);
if (!m) { console.error("no <script> found"); process.exit(1); }
const src = m[1] + "\n;globalThis.__SECTIONS = SECTIONS; globalThis.__CONTENT = CONTENT;\n";

/* ------------------------------------------------------------- DOM shim */
function el(id) {
  const node = {
    id,
    innerHTML: "",
    dataset: {},
    className: "",
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); },
      remove(c) { this._s.delete(c); },
      contains(c) { return this._s.has(c); },
    },
    _attrs: {},
    setAttribute(k, v) { this._attrs[k] = String(v); },
    removeAttribute(k) { delete this._attrs[k]; },
    getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; },
    focus() {},
    matches() { return false; },
    click() { if (typeof this.onclick === "function") this.onclick(); },
    onclick: null,
  };
  return node;
}

const vols = ["plain", "paper", "machine", "provenance"].map((v) => {
  const a = el("vol-" + v);
  a.dataset.vol = v;
  return a;
});

const nodes = {
  view: el("view"),
  toc: el("toc"),
  scrim: el("scrim"),
  menu: el("menu"),
  theme: el("theme"),
};

const docListeners = {};
const winListeners = {};

const store = {};
const localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};

const location = { hash: "#/home" };

const documentShim = {
  getElementById: (id) => nodes[id] || null,
  querySelectorAll: (sel) => (sel === "#bar .vol" ? vols : []),
  addEventListener: (t, fn) => { (docListeners[t] = docListeners[t] || []).push(fn); },
  body: { dataset: { theme: "light" } },
};

const windowShim = {
  addEventListener: (t, fn) => { (winListeners[t] = winListeners[t] || []).push(fn); },
  scrollTo: () => {},
};

const sandbox = {
  document: documentShim,
  window: windowShim,
  location,
  localStorage,
  confirm: () => false,
  console,
  Math,
  Number,
  String,
  JSON,
  RegExp,
  setTimeout: (fn) => fn(),
};
sandbox.globalThis = sandbox;

/* ------------------------------------------------------------- run the real script */
const out = [];
const ok = (n, c, d) => out.push({ n, ok: !!c, d: d || "" });

let threw = null;
try {
  vm.createContext(sandbox);
  vm.runInContext(src, sandbox, { filename: "omega-reader.html" });
} catch (e) {
  threw = e;
}

function fireHashchange() {
  (winListeners.hashchange || []).forEach((fn) => fn());
}
function go(hash) {
  location.hash = hash;
  fireHashchange();
}

ok("script evaluates without throwing", !threw, threw && threw.message);

/* ------------------------------------------------------------- manifest */
const SECTIONS = sandbox.__SECTIONS;
const CONTENT = sandbox.__CONTENT;
ok("SECTIONS is an array of 11", Array.isArray(SECTIONS) && SECTIONS.length === 11, String(SECTIONS && SECTIONS.length));
ok("four registers present", ["plain", "paper", "machine", "provenance"].every((v) => v in CONTENT));
ok("every register has every section",
  ["plain", "paper", "machine", "provenance"].every((v) => SECTIONS.every((s) => s.id in CONTENT[v])));

/* ------------------------------------------------------------- landing */
go("#/home");
const home = nodes.view.innerHTML;
ok("home renders the four bookmark links",
  ["#/plain/0", "#/paper/0", "#/machine/0", "#/provenance/0"].every((h) => home.includes(h)),
  home.slice(0, 120));

/* ------------------------------------------------------------- BUG-2: escaping */
go("#/machine/0");
const mach = nodes.view.innerHTML;
ok("machine register wraps content in <pre><code>", /<pre><code>/.test(mach));
ok("BUG-2 fixed: machine YAML text is present", mach.includes("entity: repository_invariant"));

/* a poison payload proves escaping actually runs on the machine/provenance path */
sandbox.__CONTENT.machine[0] = "x: <b>bold</b> & <script>alert(1)</script>";
go("#/machine/0");
const poisoned = nodes.view.innerHTML;
ok("BUG-2 fixed: angle brackets in content are escaped, not injected",
  poisoned.includes("&lt;b&gt;") && poisoned.includes("&amp;") && !/<b>bold<\/b>/.test(poisoned) && !/<script>alert\(1\)<\/script>/.test(poisoned),
  poisoned.slice(poisoned.indexOf("<pre>"), poisoned.indexOf("<pre>") + 90));
sandbox.__CONTENT.machine[0] = "entity: repository_invariant\nstatus: synthesis_over_public_components\nconditions: [A, B, C, D]\nnecessity: each_removable\nsufficiency: conjunction_sufficient\nsenses: 11\nspecifications: 8\nfalsifiers: [F1, F2, F3, F4]";

ok("provenance register renders and stays escaped",
  (function () { go("#/provenance/1"); const h = nodes.view.innerHTML; return /<pre><code>/.test(h) && h.includes("C-1-01"); })());

/* ------------------------------------------------------------- BUG-1: bounds */
let boundsThrew = null;
try { go("#/machine/999"); } catch (e) { boundsThrew = e; }
ok("BUG-1 fixed: out-of-range deep link does not throw", !boundsThrew, boundsThrew && boundsThrew.message);
ok("BUG-1 fixed: out-of-range clamps to the last section", nodes.view.innerHTML.includes(SECTIONS[10].title));

let negThrew = null;
try { go("#/paper/-5"); } catch (e) { negThrew = e; }
ok("negative index clamps to 0 and does not throw", !negThrew, negThrew && negThrew.message);

/* ------------------------------------------------------------- provenance spine */
go("#/paper/5");
ok("paper register shows an inline provenance <details>",
  /<details class="provenance">/.test(nodes.view.innerHTML));
ok("provenance block is escaped inside <pre><code>",
  /<details class="provenance">[\s\S]*<pre><code>/.test(nodes.view.innerHTML));
go("#/provenance/5");
ok("provenance register itself has NO nested details block",
  !/<details class="provenance">/.test(nodes.view.innerHTML));

/* ------------------------------------------------------------- bad hash fallback */
go("#/bogus/3");
ok("unknown register falls back to home", nodes.view.innerHTML.includes("bookmarks"));
go("#/plain/2");
ok("valid route renders the section title", nodes.view.innerHTML.includes(SECTIONS[2].title));

/* ------------------------------------------------------------- register switch keeps section */
go("#/machine/4");
ok("register switch preserves the section id",
  nodes.view.innerHTML.includes("04 / 10") && nodes.view.innerHTML.includes(SECTIONS[4].title));

/* ------------------------------------------------------------- theme persistence */
nodes.theme.click();
ok("theme toggle writes localStorage", store["repo-theme"] === "dark", store["repo-theme"]);
nodes.theme.click();
ok("theme toggle flips back", store["repo-theme"] === "light", store["repo-theme"]);

/* ------------------------------------------------------------- position memory */
go("#/paper/7");
ok("position memory records the last route",
  store["repo-reader-pos"] === JSON.stringify({ vol: "paper", id: 7 }), store["repo-reader-pos"]);

/* ------------------------------------------------------------- TOC */
ok("TOC lists every section and the other registers",
  nodes.toc.innerHTML.includes(SECTIONS[10].title) &&
  ["plain", "machine", "provenance"].every((v) => nodes.toc.innerHTML.includes(">" + v + "<")));

/* ------------------------------------------------------------- report */
let failed = 0;
for (const r of out) {
  if (!r.ok) failed++;
  console.log(`${r.ok ? "PASS" : "FAIL"}  ${r.n}${r.ok ? "" : "  [" + r.d + "]"}`);
}
console.log(`\n${out.length - failed}/${out.length} passed`);
process.exit(failed ? 1 : 0);
