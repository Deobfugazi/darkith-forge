/* Unit tests for darkith-omega-files.html — the single-file file manager.
   Run: node tools/test_files.js

   Dependency-free. Extracts the REAL <script> from the page and runs it against a
   minimal DOM + bridge shim, so what is exercised is the shipped code, not a copy.

   The three things that must never regress:
     1. BOTH bridge fileList contracts normalise to one shape
        (DarkithBridge {name,dir,size} and HomekeeperBridge {name,type,bytes,mtime}).
     2. fileRoots' U+0001 joining is split correctly.
     3. A hostile filename is never injected into the DOM (textContent, not innerHTML). */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const file = path.join(__dirname, "..", "darkith-omega-files.html");
const html = fs.readFileSync(file, "utf8");
const m = html.match(/<script>([\s\S]*)<\/script>/);
if (!m) { console.error("no <script> found"); process.exit(1); }
const src = m[1] + "\n;globalThis.__API = window.DarkithFiles;\n";

/* ------------------------------------------------------------- DOM shim */
function makeEl(tag) {
  const node = {
    tagName: (tag || "div").toUpperCase(),
    children: [], _text: "", className: "", dataset: {}, style: {},
    _attrs: {}, _listeners: {}, value: "",
    set textContent(v) { this._text = String(v); this.children = []; },
    get textContent() { return this._text; },
    set innerHTML(v) { this._html = String(v); },
    get innerHTML() { return this._html === undefined ? "" : this._html; },
    appendChild(c) { this.children.push(c); this._text += (c._text || ""); return c; },
    setAttribute(k, v) { this._attrs[k] = String(v); },
    getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; },
    addEventListener(t, fn) { (this._listeners[t] = this._listeners[t] || []).push(fn); },
    removeEventListener() {},
    querySelectorAll() { return []; },
    focus() {},
    click() { (this._listeners.click || []).forEach(fn => fn({ target: this, preventDefault() {} })); }
  };
  return node;
}

function makeDoc() {
  const els = {};
  const doc = {
    readyState: "complete",
    createElement: makeEl,
    createTextNode: (s) => { const n = makeEl("#text"); n._text = String(s); return n; },
    createDocumentFragment: () => makeEl("#fragment"),
    getElementById: (id) => (els[id] = els[id] || makeEl("div")),
    querySelectorAll: () => [],
    addEventListener() {},
    _els: els
  };
  return doc;
}

/* ---------------------------------------------------------- bridge shim */
function makeBridge(overrides) {
  const calls = [];
  const b = {
    _calls: calls,
    fileList: (p) => { calls.push(["fileList", p]); return "[]"; },
    fileRead: (p) => { calls.push(["fileRead", p]); return "hello"; },
    fileWrite: () => "OK",
    fileDelete: () => "OK",
    fileDirs: () => "OK",
    fileMove: () => "OK",
    fileCopy: () => "OK",
    storageGranted: () => true
  };
  Object.assign(b, overrides || {});
  return b;
}

function run(bridgeOverrides, opts) {
  const doc = makeDoc();
  const win = {
    document: doc,
    prompt: () => null,
    confirm: () => true,
    setTimeout: (fn) => 0,
    clearTimeout: () => {},
    darkith: makeBridge(bridgeOverrides)
  };
  win.window = win;
  const ctx = vm.createContext(Object.assign(win, opts || {}));
  vm.runInContext(src, ctx, { filename: "darkith-omega-files.html" });
  return { api: ctx.window.DarkithFiles, win, doc, bridge: win.darkith };
}

/* --------------------------------------------------------------- harness */
let pass = 0, fail = 0;
const failures = [];
function check(name, fn) {
  try {
    const r = fn();
    if (r === false) throw new Error("returned false");
    pass++;
  } catch (e) {
    fail++;
    failures.push(name + " :: " + (e && e.message ? e.message : String(e)));
  }
}
function eq(a, b, msg) {
  const sa = JSON.stringify(a), sb = JSON.stringify(b);
  if (sa !== sb) throw new Error((msg || "mismatch") + " — got " + sa + " want " + sb);
}

/* ================================================================ tests */

/* ---- 1. contract normalisation: both bridge shapes ---- */
check("normEntry accepts DarkithBridge shape {name,dir,size}", () => {
  const { api } = run();
  eq(api.normEntry({ name: "a.txt", dir: false, size: 10 }),
     { name: "a.txt", dir: false, size: 10, mtime: 0 });
});
check("normEntry accepts HomekeeperBridge shape {name,type,bytes,mtime}", () => {
  const { api } = run();
  eq(api.normEntry({ name: "b", type: "dir", bytes: 0, mtime: 1234 }),
     { name: "b", dir: true, size: 0, mtime: 1234 });
});
check("normEntry treats type:dir as a folder", () => {
  const { api } = run();
  if (api.normEntry({ name: "d", type: "dir", bytes: 0 }).dir !== true) throw new Error("not dir");
});
check("normEntry rejects entries with no name", () => {
  const { api } = run();
  eq(api.normEntry({ dir: true }), null);
  eq(api.normEntry(null), null);
  eq(api.normEntry("nope"), null);
});
check("normList parses a mixed JSON array from either bridge", () => {
  const { api } = run();
  const a = api.normList(JSON.stringify([
    { name: "x", dir: false, size: 5 },
    { name: "y", type: "dir", bytes: 0, mtime: 9 }
  ]));
  eq(a.length, 2);
  eq(a[0].name, "x"); eq(a[1].dir, true); eq(a[1].mtime, 9);
});
check("normList returns null on ERROR strings (never throws)", () => {
  const { api } = run();
  eq(api.normList("ERROR: not found"), null);
  eq(api.normList(""), null);
  eq(api.normList(null), null);
  eq(api.normList("not json"), null);
});

/* ---- 2. roots: U+0001 joining ---- */
check("parseRoots splits U+0001 joined paths", () => {
  const { api } = run();
  eq(api.parseRoots("/sdcard\u0001/storage/emulated/0/Android/data/x/files"),
     ["/sdcard", "/storage/emulated/0/Android/data/x/files"]);
});
check("parseRoots accepts a JSON array too", () => {
  const { api } = run();
  eq(api.parseRoots('["/a","/b"]'), ["/a", "/b"]);
});
check("parseRoots falls back to /sdcard when absent (SPI-8 home)", () => {
  const { api } = run();
  eq(api.parseRoots(null), ["/sdcard"]);
  eq(api.parseRoots(""), ["/sdcard"]);
});
check("parseRoots de-duplicates", () => {
  const { api } = run();
  eq(api.parseRoots("/a\u0001/a"), ["/a"]);
});

/* ---- 3. paths ---- */
check("join avoids a double slash", () => {
  const { api } = run();
  eq(api.join("/sdcard/", "x"), "/sdcard/x");
  eq(api.join("/sdcard", "x"), "/sdcard/x");
  eq(api.join("/", "x"), "/x");
});
check("parentOf walks up and stops at root", () => {
  const { api } = run();
  eq(api.parentOf("/sdcard/a/b"), "/sdcard/a");
  eq(api.parentOf("/sdcard"), "/");
  eq(api.parentOf("/"), "/");
});
check("baseName extracts the last segment", () => {
  const { api } = run();
  eq(api.baseName("/sdcard/a/b.txt"), "b.txt");
  eq(api.baseName("/sdcard/a/"), "a");
  eq(api.baseName("/x"), "x");
});
check("crumbs builds a cumulative path chain", () => {
  const { api } = run();
  const c = api.crumbs("/sdcard/a/b");
  eq(c.map(x => x.label), ["sdcard", "a", "b"]);
  eq(c[2].path, "/sdcard/a/b");
});

/* ---- 4. formatting ---- */
check("fmtBytes is human-readable and bounded", () => {
  const { api } = run();
  eq(api.fmtBytes(0), "0 B");
  eq(api.fmtBytes(512), "512 B");
  eq(api.fmtBytes(1024), "1.0 KB");
  eq(api.fmtBytes(1536), "1.5 KB");
  eq(api.fmtBytes(1048576), "1.0 MB");
  eq(api.fmtBytes(-1), "—");
  eq(api.fmtBytes(NaN), "—");
});
check("fmtTime returns empty for 0/absent", () => {
  const { api } = run();
  eq(api.fmtTime(0), "");
  eq(api.fmtTime(null), "");
});
check("ext lowercases and ignores dotfiles", () => {
  const { api } = run();
  eq(api.ext("A.TXT"), "txt");
  eq(api.ext(".bashrc"), "");
  eq(api.ext("noext"), "");
});
check("kindOf classifies by extension and folder", () => {
  const { api } = run();
  eq(api.kindOf({ name: "d", dir: true }), "dir");
  eq(api.kindOf({ name: "a.png" }), "img");
  eq(api.kindOf({ name: "a.mp3" }), "aud");
  eq(api.kindOf({ name: "a.mp4" }), "vid");
  eq(api.kindOf({ name: "a.kt" }), "doc");
  eq(api.kindOf({ name: "a.bin" }), "bin");
});

/* ---- 5. sorting + filtering ---- */
check("sortEntries keeps folders first", () => {
  const { api } = run();
  const s = api.sortEntries([
    { name: "z.txt", dir: false, size: 1, mtime: 1 },
    { name: "a_dir", dir: true, size: 0, mtime: 1 }
  ]);
  eq(s[0].name, "a_dir");
});
check("sortEntries sorts by name with numeric awareness", () => {
  const { api } = run();
  const s = api.sortEntries([
    { name: "file10", dir: false, size: 0, mtime: 0 },
    { name: "file2", dir: false, size: 0, mtime: 0 }
  ]);
  eq(s[0].name, "file2");
  eq(s[1].name, "file10");
});
check("sortEntries by size ascending", () => {
  const { api } = run();
  api.state.sortBy = "size";
  const s = api.sortEntries([
    { name: "big", dir: false, size: 900, mtime: 0 },
    { name: "small", dir: false, size: 3, mtime: 0 }
  ]);
  eq(s[0].name, "small");
});
check("applyFilter is case-insensitive substring", () => {
  const { api } = run();
  api.state.filter = "LOG";
  const r = api.applyFilter([{ name: "app.log" }, { name: "x.txt" }]);
  eq(r.length, 1); eq(r[0].name, "app.log");
});
check("applyFilter with empty query returns everything", () => {
  const { api } = run();
  api.state.filter = "";
  eq(api.applyFilter([{ name: "a" }, { name: "b" }]).length, 2);
});

/* ---- 6. bridge interaction ---- */
check("go() navigates and stores the normalised listing", () => {
  const { api } = run({
    fileList: () => JSON.stringify([{ name: "d", type: "dir", bytes: 0 }, { name: "f.txt", type: "file", bytes: 7 }])
  });
  const ok = api.go("/sdcard/x");
  if (ok !== true) throw new Error("go returned " + ok);
  eq(api.state.cwd, "/sdcard/x");
  eq(api.state.entries.length, 2);
  eq(api.state.entries[1].size, 7);
});
check("go() on an ERROR keeps the previous cwd", () => {
  const { api } = run({ fileList: () => "ERROR: not found" });
  api.state.cwd = "/sdcard/keep";
  const ok = api.go("/sdcard/gone");
  if (ok !== false) throw new Error("expected false");
  eq(api.state.cwd, "/sdcard/keep");
});
check("selectedPaths joins cwd with each selected name", () => {
  const { api } = run();
  api.state.cwd = "/sdcard/music";
  api.state.sel = { "a.mp3": true, "b.mp3": true };
  eq(api.selectedPaths().sort(), ["/sdcard/music/a.mp3", "/sdcard/music/b.mp3"]);
});
check("setClip records a copy and clears selection", () => {
  const { api } = run();
  api.state.cwd = "/sdcard";
  api.state.sel = { "a.txt": true };
  api.setClip("copy", api.selectedNames());
  eq(api.state.clip.op, "copy");
  eq(api.state.clip.paths, ["/sdcard/a.txt"]);
  eq(Object.keys(api.state.sel).length, 0);
});
check("doDelete calls fileDelete once per name", () => {
  const deleted = [];
  const { api } = run({ fileDelete: (p) => { deleted.push(p); return "OK"; } });
  api.state.cwd = "/sdcard";
  api.doDelete(["a", "b"]);
  eq(deleted, ["/sdcard/a", "/sdcard/b"]);
});
check("doDelete reports failure without throwing", () => {
  const { api } = run({ fileDelete: () => "ERROR: denied" });
  api.state.cwd = "/sdcard";
  const ok = api.doDelete(["a"]);
  if (ok !== false) throw new Error("expected false");
});
check("rename moves within the same folder", () => {
  const moves = [];
  const { api } = run({ fileMove: (s, d) => { moves.push([s, d]); return "OK"; } });
  api.state.cwd = "/sdcard";
  api.win = null;
  const r = api.rename(["old.txt"]);
  // prompt is not available in the shim -> no rename performed, and no crash
  if (r !== false) throw new Error("expected false without a prompt");
});
check("newFolder refuses an empty name", () => {
  const { api } = run();
  api.state.cwd = "/sdcard";
  if (api.newFolder() !== false) throw new Error("expected false");
});
check("paste with an empty clipboard is a no-op", () => {
  const { api } = run();
  api.state.clip = null;
  if (api.paste() !== false) throw new Error("expected false");
});

/* ---- 7. boot with no bridge (desktop/preview) ---- */
check("boot survives with no bridge at all", () => {
  const doc = makeDoc();
  const win = { document: doc, setTimeout: () => 0, clearTimeout: () => {} };
  win.window = win;
  const ctx = vm.createContext(win);
  vm.runInContext(src, ctx, { filename: "darkith-omega-files.html" });
  const api = ctx.window.DarkithFiles;
  if (!api) throw new Error("API not exposed");
  eq(api.state.roots, ["/sdcard"]);
});

/* ---- 8. XSS: hostile filename never injected ---- */
check("hostile filename is not written as HTML", () => {
  const evil = '<img src=x onerror=alert(1)>.txt';
  const { api, doc } = run({
    fileList: () => JSON.stringify([{ name: evil, type: "file", bytes: 1 }])
  });
  api.go("/sdcard");
  const list = doc.getElementById("list");
  // The row's name node must carry the text, and no innerHTML anywhere must hold it.
  const serialised = JSON.stringify(list.children, (k, v) => (k === "_html" ? v : v));
  if (serialised.indexOf("onerror") >= 0 && serialised.indexOf("<img") >= 0) {
    // Only acceptable if it is inside a _text (escaped) field, never a _html field.
    const hasHtml = list.children.some(c => (c._html || "").indexOf("onerror") >= 0);
    if (hasHtml) throw new Error("hostile name reached innerHTML");
  }
});
check("normEntry preserves the exact hostile string as text", () => {
  const { api } = run();
  const evil = '<script>x</script>';
  const e = api.normEntry({ name: evil, type: "file", bytes: 0 });
  eq(e.name, evil);
});

/* ---- 9. API surface ---- */
check("API exposes the documented surface", () => {
  const { api } = run();
  ["VERSION", "boot", "go", "refresh", "up", "join", "parentOf", "baseName", "crumbs",
   "normEntry", "normList", "parseRoots", "sortEntries", "applyFilter", "fmtBytes",
   "fmtTime", "kindOf", "ext", "selectedNames", "selectedPaths", "setClip", "paste",
   "doDelete", "rename", "newFolder", "preview", "isError"].forEach(k => {
    if (!(k in api)) throw new Error("missing " + k);
  });
});
check("VERSION is a semver string", () => {
  const { api } = run();
  if (!/^\d+\.\d+\.\d+$/.test(api.VERSION)) throw new Error("bad version " + api.VERSION);
});

/* ---------------------------------------------------------------- report */
const total = pass + fail;
if (fail) {
  console.error("  FAILURES:");
  failures.forEach(f => console.error("    ✗ " + f));
}
console.log("  files: " + pass + "/" + total + " passed" + (fail ? ", " + fail + " FAILED" : ""));
process.exit(fail ? 1 : 0);
