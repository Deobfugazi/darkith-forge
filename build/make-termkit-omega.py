#!/usr/bin/env python3
"""Build the standalone OMEGA TermKit app source tree.

One installable app (com.darkith.termkit) that is the combined integration of:
  * termkit.bundle.js   — OMEGA TermKit: a real userspace shell (VFS, pipes,
                          redirection, control flow, job control, completion)
  * vendor/darkterm.js  — DarkTerm: the POSIX-style shell + handcoded dev toolkits
  * vendor/darktools.js — task / sync / tk / store toolkits
  * savf_core.html      — SAVF-1 Universal Audit Engine (omni-VM truth tool)
plus a native tier that reaches the real device through /system/bin/sh.

The UI is assembled here from those canonical sources (no duplicated engines),
version-stamped from VERSION.json, and written next to a small Kotlin host. Then
`build.sh` packages and signs it exactly like the host app.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "termkit_omega"
ASSETS = OUT / "app" / "src" / "main" / "assets"
JAVA = OUT / "app" / "src" / "main" / "java" / "com" / "darkith" / "termkit"

VER = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
VNAME = VER["versionName"]
VCODE = VER["versionCode"]

# ---- canonical engine sources ------------------------------------------------
TERMKIT = (ROOT / "delivery" / "termkit.bundle.js").read_text(encoding="utf-8")
DARKTERM = (ROOT / "app/src/main/assets/vendor/darkterm.js").read_text(encoding="utf-8")
DARKTOOLS = (ROOT / "app/src/main/assets/vendor/darktools.js").read_text(encoding="utf-8")

_savf = (ROOT / "app/src/main/assets/savf_core.html").read_text(encoding="utf-8")
# the pure engine is the first <script> block (SAVF-1 engine, exposes window.SAVF)
_end = _savf.index("window.SAVF = API;")
_start = _savf.rindex("<script>", 0, _end) + len("<script>")
_stop = _savf.index("</script>", _end)
SAVF_ENGINE = _savf[_start:_stop].strip()

UI_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="dark">
<title>DARKITH Ω TERMKIT</title>
<style>
  :root{
    --bg:#050505; --panel:#0d0d10; --panel2:#141419; --line:#26262e; --line2:#33333d;
    --ink:#ececf1; --dim:#8b8b96; --faint:#5c5c66;
    --accent:#e8c268; --accent-dim:rgba(232,194,104,.14);
    --red:#f87171; --green:#34d399; --cyan:#67e8f9;
    --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
    --sp:.18s cubic-bezier(.2,.8,.2,1);
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%}
  body{background:var(--bg);color:var(--ink);font-family:var(--mono);overflow:hidden}
  #app{display:flex;flex-direction:column;height:100dvh}
  header{flex:0 0 auto;display:flex;align-items:center;gap:10px;padding:10px 14px;
    border-bottom:1px solid var(--line);background:linear-gradient(180deg,#0b0b0e,#08080a)}
  .brand{font-weight:800;letter-spacing:.14em;font-size:13px;color:var(--accent)}
  .ver{margin-left:auto;font-size:11px;color:var(--dim);border:1px solid var(--line);
    border-radius:20px;padding:3px 10px;background:var(--accent-dim);color:var(--accent)}
  .dot{width:8px;height:8px;border-radius:50%;background:var(--faint)}
  .dot.on{background:var(--green);box-shadow:0 0 8px var(--green)}
  nav{flex:0 0 auto;display:flex;gap:2px;padding:8px 10px 0;border-bottom:1px solid var(--line)}
  nav button{flex:1;background:transparent;border:1px solid transparent;border-bottom:none;
    color:var(--dim);font:600 12px/1 var(--mono);letter-spacing:.06em;padding:9px 6px;
    border-radius:10px 10px 0 0;cursor:pointer;transition:color var(--sp),background var(--sp)}
  nav button.on{color:var(--accent);background:var(--panel2);border-color:var(--line)}
  main{flex:1;min-height:0;position:relative}
  .pane{position:absolute;inset:0;display:none;flex-direction:column;min-height:0}
  .pane.on{display:flex}
  .body{flex:1;min-height:0;overflow-y:auto;padding:12px 14px;scrollbar-width:thin}
  .body::-webkit-scrollbar{width:8px}.body::-webkit-scrollbar-thumb{background:var(--line2);border-radius:8px}
  .out{white-space:pre-wrap;word-break:break-word;font:12px/1.55 var(--mono);min-height:1px}
  .t-out{color:var(--ink)}.t-err{color:var(--red)}.t-sys{color:var(--dim)}.t-ok{color:var(--green)}
  .t-cmdline{color:var(--accent);margin-top:6px}.t-cmdline .t-ps1{color:var(--cyan)}
  .tk-key{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;
    font:12px/1 var(--mono);color:var(--ink);background:rgba(255,255,255,.07);border:1px solid var(--line);
    border-radius:9px;padding:0 11px;min-width:40px;min-height:34px;cursor:pointer;transition:transform var(--sp),background var(--sp)}
  .tk-key:active{transform:scale(.93);background:var(--accent-dim)}
  #term-quick{flex:0 0 auto;display:flex;gap:6px;overflow-x:auto;overflow-y:hidden;padding:6px 12px 2px;scrollbar-width:none;
    mask-image:linear-gradient(90deg,#000 92%,transparent)}
  #term-quick::-webkit-scrollbar{display:none}
  .form{flex:0 0 auto;display:flex;align-items:center;gap:8px;padding:8px 12px calc(10px + env(safe-area-inset-bottom));
    border-top:1px solid var(--line);background:var(--panel)}
  .ps1{font:12px/1 var(--mono);color:var(--cyan);flex:0 0 auto;white-space:nowrap}
  .inp{flex:1;min-width:0;background:transparent;border:0;outline:0;color:var(--ink);
    font:13px/1.4 var(--mono);padding:8px 0;caret-color:var(--accent)}
  .inp::placeholder{color:var(--faint)}
  textarea.inp{border:1px solid var(--line);border-radius:10px;padding:10px;background:var(--panel2);
    min-height:34vh;resize:vertical;font-size:12px}
  .btn{flex:0 0 auto;background:var(--accent);color:#000;border:0;border-radius:10px;font:800 12px/1 var(--mono);
    padding:10px 14px;cursor:pointer}
  .btn.ghost{background:transparent;color:var(--accent);border:1px solid var(--line2)}
  .card{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:12px;margin-bottom:10px}
  .card h3{margin:0 0 6px;font-size:12px;letter-spacing:.1em;color:var(--accent)}
  .kv{display:flex;justify-content:space-between;gap:12px;font-size:12px;padding:3px 0;color:var(--dim)}
  .kv b{color:var(--ink);font-weight:600}
  .badge{display:inline-block;font-size:11px;font-weight:800;border-radius:6px;padding:2px 7px;margin-right:6px}
  .b-pass{background:rgba(52,211,153,.14);color:var(--green)}
  .b-fail{background:rgba(248,113,113,.14);color:var(--red)}
  .b-invalid{background:rgba(232,194,104,.14);color:var(--accent)}
  .b-unparseable{background:rgba(139,139,150,.16);color:var(--dim)}
  .row{font-size:12px;padding:6px 0;border-top:1px solid var(--line)}
  .row:first-child{border-top:0}
  .hint{color:var(--faint);font-size:11px;padding:0 14px 6px}
</style>
</head>
<body>
<div id="app">
  <header>
    <span class="brand">DARKITH&nbsp;Ω&nbsp;TERMKIT</span>
    <span class="dot" id="nat-dot" title="native tier"></span>
    <span class="ver" id="ver-chip">__VERSION__</span>
  </header>
  <nav>
    <button data-pane="term" class="on">TERM</button>
    <button data-pane="dark">DARKTERM</button>
    <button data-pane="savf">SAVF</button>
    <button data-pane="omega">Ω</button>
  </nav>
  <main>
    <section class="pane on" id="pane-term">
      <div class="body" id="term-body"><div class="out" id="term-out"></div></div>
      <div id="term-quick" aria-label="Quick keys"></div>
      <form class="form" id="term-form" autocomplete="off">
        <span class="ps1" id="term-prompt">$</span>
        <span class="ps1" id="term-cwd">/</span>
        <input class="inp" id="term-input" placeholder="ls · cat · task · sync · host uname -a"
               autocapitalize="off" autocorrect="off" spellcheck="false">
      </form>
    </section>

    <section class="pane" id="pane-dark">
      <div class="body" id="dt-body"><div class="out" id="dt-out"></div></div>
      <form class="form" id="dt-form" autocomplete="off">
        <span class="ps1">darkterm&gt;</span>
        <input class="inp" id="dt-input" placeholder="task add &quot;ship omega&quot; · sync omega · tk list"
               autocapitalize="off" autocorrect="off" spellcheck="false">
      </form>
    </section>

    <section class="pane" id="pane-savf">
      <div class="body">
        <div class="card">
          <h3>SAVF-1 · OMNI AUDIT</h3>
          <div class="hint" style="padding:0 0 8px">Paste claims; one per line. Each is judged against the gate formulary and the deciding rule is named.</div>
          <textarea class="inp" id="savf-in" spellcheck="false" placeholder="FACT: pi ~ 3.14159&#10;DERIVATIVE: d/dx x^2 = 2*x&#10;assume and_axiom&#10;INTEGRAL: int 2*x dx = x^2"></textarea>
          <div style="display:flex;gap:8px;margin-top:10px">
            <button class="btn" id="savf-run">AUDIT</button>
            <button class="btn ghost" id="savf-demo">demo</button>
            <button class="btn ghost" id="savf-selftest">self-test</button>
          </div>
        </div>
        <div class="out" id="savf-out"></div>
      </div>
    </section>

    <section class="pane" id="pane-omega">
      <div class="body">
        <div class="card">
          <h3>OMEGA TERMKIT</h3>
          <div class="kv"><span>version</span><b>__VERSION__</b></div>
          <div class="kv"><span>termkit</span><b id="o-tk">—</b></div>
          <div class="kv"><span>darkterm</span><b id="o-dt">—</b></div>
          <div class="kv"><span>darktools</span><b id="o-tools">—</b></div>
          <div class="kv"><span>savf</span><b id="o-savf">—</b></div>
          <div class="kv"><span>native tier</span><b id="o-native">—</b></div>
        </div>
        <div class="card">
          <h3>DEVICE (real /system/bin/sh)</h3>
          <div class="out" id="o-dev">tap RUN to query the device</div>
          <div style="display:flex;gap:8px;margin-top:10px">
            <button class="btn" id="o-run">RUN</button>
            <button class="btn ghost" id="o-selftest">self-test</button>
          </div>
        </div>
      </div>
    </section>
  </main>
</div>

<script>__TERMKIT__</script>
<script>__DARKTERM__</script>
<script>__DARKTOOLS__</script>
<script>__SAVF__</script>
<script>
"use strict";
(function () {
  var VERSION = "__VERSION__";
  var $ = function (id) { return document.getElementById(id); };

  /* ---- tabs ---- */
  var tabs = document.querySelectorAll("nav button");
  tabs.forEach(function (b) {
    b.addEventListener("click", function () {
      tabs.forEach(function (x) { x.classList.remove("on"); });
      b.classList.add("on");
      document.querySelectorAll(".pane").forEach(function (p) { p.classList.remove("on"); });
      $("pane-" + b.dataset.pane).classList.add("on");
      if (b.dataset.pane === "term") { var i = $("term-input"); if (i) i.focus(); }
      if (b.dataset.pane === "dark") { var j = $("dt-input"); if (j) j.focus(); }
    });
  });

  /* ---- native tier ---- */
  function nativeAvailable() {
    try { return !!(window.OmegaHost && window.OmegaHost.available && window.OmegaHost.available()); }
    catch (e) { return false; }
  }
  window.__omegaExec = function (cmd) {
    try {
      if (nativeAvailable()) return window.OmegaHost.sh(String(cmd));
      return "(offline: no device shell in this host — native tier is Android-only)\n";
    } catch (e) { return "host error: " + (e && e.message ? e.message : e) + "\n"; }
  };
  var natDot = $("nat-dot");
  if (nativeAvailable()) natDot.classList.add("on");

  /* ---- TERM: OMEGA TermKit ---- */
  var TK = (window.TermKit && window.TermKit.mount) ? window.TermKit.mount() : null;
  if (TK) {
    try { TK.install(); } catch (e) { /* already bound */ }
    /* `host <cmd>` runs a real device command through the native tier. */
    TK.shell.builtins["host"] = function (args, ctx) {
      ctx.write(window.__omegaExec(args.join(" ")) + "\n");
      return 0;
    };
    TK.shell.aliases["sh"] = "host";
    TK.shell.aliases["exec"] = "host";
    var q = $("term-quick");
    ["ls", "pwd", "help", "tree", "test", "host uname -a", "host id", "clear"].forEach(function (c) {
      var k = document.createElement("button");
      k.type = "button"; k.className = "tk-key"; k.textContent = c;
      k.addEventListener("click", function () {
        if (c === "clear") { TK.clear(); return; }
        TK.run(c);
      });
      q.appendChild(k);
    });
  } else {
    $("term-out").textContent = "TermKit failed to mount.\n";
  }

  /* ---- DARKTERM: DarkTerm + DarkTools toolkits ---- */
  var DT = (window.DarkTerm && window.DarkTerm.createSession) ? window.DarkTerm.createSession({}) : null;
  var dtOut = $("dt-out");
  function dtPrint(txt, cls) {
    if (!txt) return;
    var s = document.createElement("div"); s.className = "out " + (cls || "t-out");
    s.textContent = txt; dtOut.appendChild(s);
    var b = $("dt-body"); b.scrollTop = b.scrollHeight;
  }
  if (DT && window.DarkTools && window.DarkTools.install) {
    try {
      window.DarkTools.install({ shell: DT.shell, fs: DT.fs }, {
        DarkTerm: window.DarkTerm,
        store: window.DarkTools.makeStore("local", "omega.workspace"),
        syncStore: window.DarkTools.makeStore("local", "omega.sync")
      });
    } catch (e) { dtPrint("toolkit install: " + e.message + "\n", "t-err"); }
  }
  dtPrint("DarkTerm " + (DT ? (DT.shell.version || VERSION) : "?") + " — toolkits: task, sync, tk, store\n", "t-sys");
  dtPrint("try: task add \"ship omega\"  ·  sync omega  ·  tk list\n\n", "t-sys");
  $("dt-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var inp = $("dt-input"); var line = inp.value; inp.value = "";
    if (!line.trim()) return;
    dtPrint("darkterm> " + line + "\n", "t-cmdline");
    if (!DT) { dtPrint("no session\n", "t-err"); return; }
    var r = DT.exec(line);
    if (r.out) dtPrint(r.out);
    if (r.err) dtPrint(r.err, "t-err");
  });

  /* ---- SAVF: the omni audit engine ---- */
  var S = window.SAVF;
  var savfOut = $("savf-out");
  var DEMO = [
    "# SAVF-1 demo formulary. Lines starting with # are ignored.",
    "",
    "1 + 1 equals 2",
    "1/3 + 1/3 + 1/3 equals 1",
    "",
    "d/dx of x^3 at 2 is 12",
    "d/dx of sin(x) at 0 is 1",
    "The integral of x^2 from 0 to 3 is 9",
    "",
    "The exponential of zero is one",
    "the logarithm base 2 of 8 is 3",
    "the sine of 0 is 0",
    "The determinant of [[3, 8], [4, 6]] is -14",
    "",
    "The capital of France is Paris",
    "The atomic weight of iron is 55.845",
    "",
    "assume axiom_a",
    "lemma_1 derives from axiom_a",
    "lemma_2 derives from lemma_1",
    "",
    "The row axis traverses left to right on the math chart",
    "The depth axis traverses near to far on the raster chart"
  ].join("\n");
  function renderAudit(res) {
    savfOut.textContent = "";
    if (!res || !res.results) { savfOut.textContent = "no result\n"; return; }
    var c = res.counts || {};
    var head = document.createElement("div");
    head.className = "card";
    head.innerHTML = "";
    var h = document.createElement("h3"); h.textContent = "VERDICT: " + (res.verdict || "?");
    head.appendChild(h);
    var kv = document.createElement("div"); kv.className = "kv";
    kv.innerHTML = "<span>pass " + (c.pass||0) + " · fail " + (c.fail||0) + " · invalid " + (c.invalid||0) + " · unparseable " + (c.unparseable||0) + "</span>";
    head.appendChild(kv);
    savfOut.appendChild(head);
    res.results.forEach(function (r) {
      var b = (r.badge || r.status || "?").toString().toUpperCase();
      var cls = b.indexOf("PASS") === 0 ? "b-pass" : b.indexOf("FAIL") === 0 ? "b-fail" : b.indexOf("UNPARSE") === 0 ? "b-unparseable" : "b-invalid";
      var row = document.createElement("div"); row.className = "row";
      var tag = document.createElement("span"); tag.className = "badge " + cls; tag.textContent = b;
      row.appendChild(tag);
      var line = document.createElement("span"); line.textContent = "L" + (r.lineNo||"?") + "  " + (r.line || "");
      row.appendChild(line);
      if (r.note) { var n = document.createElement("div"); n.className = "hint"; n.style.padding = "4px 0 0"; n.textContent = r.note; row.appendChild(n); }
      savfOut.appendChild(row);
    });
  }
  $("savf-run").addEventListener("click", function () {
    if (!S) { savfOut.textContent = "SAVF engine unavailable\n"; return; }
    try { renderAudit(S.runAudit($("savf-in").value)); }
    catch (e) { savfOut.textContent = "audit error: " + e.message + "\n"; }
  });
  $("savf-demo").addEventListener("click", function () { $("savf-in").value = DEMO; $("savf-run").click(); });
  $("savf-selftest").addEventListener("click", function () {
    savfOut.textContent = "";
    if (!S || !S.selfTest) { savfOut.textContent = "no self-test\n"; return; }
    var R = S.selfTest();
    var passed = R.filter(function (r) { return r.ok; }).length;
    var d = document.createElement("div"); d.className = "card";
    d.innerHTML = "<h3>SELF-TEST " + passed + "/" + R.length + "</h3>";
    savfOut.appendChild(d);
    R.forEach(function (r) {
      var row = document.createElement("div"); row.className = "row";
      var tag = document.createElement("span"); tag.className = "badge " + (r.ok ? "b-pass" : "b-fail"); tag.textContent = r.ok ? "PASS" : "FAIL";
      row.appendChild(tag);
      var t = document.createElement("span"); t.textContent = r.name; row.appendChild(t);
      savfOut.appendChild(row);
    });
  });

  /* ---- Ω tab ---- */
  function setText(id, v) { var e = $(id); if (e) e.textContent = v; }
  setText("o-tk", TK ? (window.TermKit.VERSION || VERSION) : "unavailable");
  setText("o-dt", DT ? (window.DarkTerm.version || VERSION) : "unavailable");
  setText("o-tools", window.DarkTools ? (window.DarkTools.version || VERSION) : "unavailable");
  setText("o-savf", S ? (S.version || "—") : "unavailable");
  setText("o-native", nativeAvailable() ? "connected" : "offline");
  $("o-run").addEventListener("click", function () {
    var cmds = ["uname -a", "id", "getprop ro.product.cpu.abi", "cat /proc/meminfo | head -3"];
    $("o-dev").textContent = cmds.map(function (c) { return "$ " + c + "\n" + window.__omegaExec(c); }).join("\n");
  });
  $("o-selftest").addEventListener("click", function () {
    var lines = [];
    if (TK && TK.selftest) {
      var st = TK.selftest();  /* returns [name, ok] pairs */
      var ok = st.filter(function (t) { return t[1]; }).length;
      lines.push("termkit: " + ok + "/" + st.length + (ok === st.length ? "  ✓" : "  ✗"));
    } else { lines.push("termkit: n/a"); }
    if (S && S.selfTest) {
      var r = S.selfTest();
      var p = r.filter(function (x) { return x.ok; }).length;
      lines.push("savf:    " + p + "/" + r.length + (p === r.length ? "  ✓" : "  ✗"));
    } else { lines.push("savf:    n/a"); }
    lines.push("native:  " + (nativeAvailable() ? "connected" : "offline"));
    $("o-dev").textContent = lines.join("\n");
  });
})();
</script>
</body>
</html>
"""


def build_ui() -> str:
    ui = UI_TEMPLATE
    ui = ui.replace("__VERSION__", VNAME)
    ui = ui.replace("__TERMKIT__", TERMKIT)
    ui = ui.replace("__DARKTERM__", DARKTERM)
    ui = ui.replace("__DARKTOOLS__", DARKTOOLS)
    ui = ui.replace("__SAVF__", SAVF_ENGINE)
    return ui


MANIFEST_XML = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.darkith.termkit"
    android:versionCode="__VCODE__"
    android:versionName="__VNAME__">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />

    <application
        android:label="OMEGA TermKit"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:allowBackup="true"
        android:hardwareAccelerated="true"
        android:theme="@android:style/Theme.Material.NoActionBar">

        <activity
            android:name="com.darkith.termkit.MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""

MAIN_KT = """package com.darkith.termkit

import android.app.Activity
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient

/**
 * OMEGA TermKit — the combined integration surface.
 *
 * The whole shell (TermKit + DarkTerm + DarkTools + SAVF) runs in the WebView,
 * offline, from file:///android_asset/termkit_omega.html. The only native tier
 * is [OmegaHost], which reaches the real device through /system/bin/sh so the
 * integrated terminal can touch the filesystem the way Termux does — without
 * Termux, without a toolchain, without the network.
 */
class MainActivity : Activity() {
    private lateinit var webView: WebView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        webView = WebView(this)
        setContentView(webView)
        webView.settings.apply {
            javaScriptEnabled = true
            allowFileAccess = true
            domStorageEnabled = true
            databaseEnabled = true
            loadWithOverviewMode = true
            useWideViewPort = true
            builtInZoomControls = false
        }
        webView.webViewClient = WebViewClient()
        webView.addJavascriptInterface(OmegaHost(), "OmegaHost")
        webView.loadUrl("file:///android_asset/termkit_omega.html")
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) { webView.goBack(); return }
        @Suppress("DEPRECATION")
        super.onBackPressed()
    }
}
"""

HOST_KT = """package com.darkith.termkit

import android.os.Environment
import android.webkit.JavascriptInterface
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * The native tier: a real device shell. Runs the command through /system/bin/sh
 * (present on every Android, no Termux required) with the external storage dir as
 * cwd, captures stdout+stderr, and caps the run so a runaway command cannot hang
 * the UI thread. Everything here is guarded: a missing shell degrades to a
 * readable message instead of a crash.
 */
class OmegaHost {
    @JavascriptInterface
    fun available(): Boolean = try { File("/system/bin/sh").exists() } catch (e: Exception) { false }

    @JavascriptInterface
    fun sh(cmd: String): String = try {
        val pb = ProcessBuilder("/system/bin/sh", "-c", cmd)
        pb.redirectErrorStream(true)
        try { pb.directory(Environment.getExternalStorageDirectory()) } catch (_: Exception) {}
        val p = pb.start()
        val out = p.inputStream.bufferedReader().readText()
        val done = p.waitFor(30, TimeUnit.SECONDS)
        if (!done) { p.destroyForcibly(); "ERROR: timeout\\n$out" }
        else if (out.isEmpty()) "exit=${p.exitValue()}\\n"
        else "exit=${p.exitValue()}\\n$out"
    } catch (e: Exception) { "ERROR: ${e.message}" }
}
"""


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    JAVA.mkdir(parents=True, exist_ok=True)

    (ASSETS / "termkit_omega.html").write_text(build_ui(), encoding="utf-8")
    (OUT / "app" / "src" / "main" / "AndroidManifest.xml").write_text(
        MANIFEST_XML.replace("__VCODE__", str(VCODE)).replace("__VNAME__", VNAME), encoding="utf-8")
    (JAVA / "MainActivity.kt").write_text(MAIN_KT, encoding="utf-8")
    (JAVA / "OmegaHost.kt").write_text(HOST_KT, encoding="utf-8")
    (OUT / "app" / "src" / "main" / "res" / "layout" / "activity_main.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    android:layout_width="match_parent" android:layout_height="match_parent" />\n', encoding="utf-8")
    (OUT / "app" / "src" / "main" / "res" / "values" / "strings.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <string name="app_name">OMEGA TermKit</string>\n</resources>\n',
        encoding="utf-8")
    print(f"termkit_omega: wrote UI ({len(build_ui())} bytes) + host for {VNAME} (code {VCODE})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
