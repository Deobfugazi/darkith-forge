#!/usr/bin/env python3
"""Integrate the pre-runner + ClearanceLoop engines into every HTML surface.

Two engines, one integration step, the same discipline as build-forge.py:

    app/src/main/assets/vendor/prerunner.js     diagnostic truth (pre-run)
    app/src/main/assets/vendor/clearanceloop.js the homeokinetic debt ratchet

Every surface gains the SAME runtime surface:

    window.DarkithPreRunner   the pre-runner (run / ui / register / transpile)
    window.DarkithPrerun      this surface's binding: pre-run the current editor
                              content (HTML/JS) or a built-in self-check page
    window.ClearanceLoop      the ratchet: observe / absorb / advance / report / ui
    window.DarkithCL          this surface's binding: .advance() absorbs the last
                              pre-run report, then .ui() opens the ratchet report

...plus a floating "▶" launcher, a `prerun` terminal command and a `clearance`
terminal command wherever the surface has a terminal, and a ClearanceLoop
toolbar entry wherever the surface has a command registry.

Each injected block is delimited by a marker pair and replaced on each run, so
running twice never doubles a payload.

Home forge is injected in BOTH places it needs to be: its own shell, and the
`studio-src` carrier it embeds — because build/build-forge.py regenerates the
standalone studio AND the fused forge FROM that carrier.

Run:  python3 build/integrate-engines.py
      python3 build/integrate-engines.py --check     (verify, write nothing)
"""
import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENGINES = [
    ROOT / "app/src/main/assets/vendor/prerunner.js",
    ROOT / "app/src/main/assets/vendor/clearanceloop.js",
]

# HTML surfaces that are plain documents.
SHELLS = [ROOT / "omega.html", ROOT / "savf.html", ROOT / "darkith-inscriber.html"]
# The forge shell carries an embedded studio; both need the engine.
FORGE = ROOT / "darkith home forge.html"

# markers (HTML comments, so a leaked block is inert and easy to strip)
PR_START, PR_END = "<!-- PRERUNNER:START -->", "<!-- PRERUNNER:END -->"
PS_START, PS_END = "<!-- PRERUN-SHIM:START -->", "<!-- PRERUN-SHIM:END -->"
CARRIER_RE = re.compile(r'<script type="text/plain" id="studio-src">')

SHIM = r"""
(function () {
  "use strict";
  function ready(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }
  var DEMO = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    + '<body style="margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#0b0c0e;color:#e8edf3;padding:18px">'
    + '<h3 style="color:#ff8a3d;margin:0 0 6px">pre-runner self-check</h3>'
    + '<p id="s" style="color:#8b949e">booting\u2026</p>'
    + '<button id="b" style="font:inherit;padding:9px 14px;border-radius:10px;border:1px solid #2a2e35;background:#161a20;color:#e8edf3;cursor:pointer">tap me</button>'
    + '<script>var n=0,b=document.getElementById("b"),s=document.getElementById("s");'
    + 'b.onclick=function(){s.textContent="tapped "+(++n)+" time"+(n===1?"":"s")};s.textContent="ready \u2014 tap the button";'
    + '<' + '/script>';
  function editorText() {
    var ids = ["input", "pasteBox", "payload-editor"];
    for (var i = 0; i < ids.length; i++) { var e = document.getElementById(ids[i]); if (e && e.value && e.value.trim()) return e.value; }
    return "";
  }
  function target(extra) {
    var t = editorText();
    var looksHtml = /<\s*(!doctype|html|body|div|script|style|button|canvas|svg|table|form)/i.test(t);
    var files = looksHtml ? { "surface.html": t } : { "selfcheck.html": DEMO };
    var o = { files: files, entry: Object.keys(files)[0], shots: 4, interval: 500, stress: 20, seed: 1 };
    if (extra) for (var k in extra) if (Object.prototype.hasOwnProperty.call(extra, k)) o[k] = extra[k];
    return o;
  }
  function api() {
    if (!window.DarkithPreRunner) return null;
    if (!window.DarkithPrerun) {
      window.DarkithPrerun = {
        run: function (o) { return window.DarkithPreRunner.run(target(o)); },
        ui: function (o) { return window.DarkithPreRunner.ui(target(o)); },
        target: target, demo: DEMO
      };
    }
    return window.DarkithPrerun;
  }
  function clApi() {
    if (!window.ClearanceLoop) return null;
    if (!window.DarkithCL) {
      window.ClearanceLoop.install();
      window.DarkithCL = {
        /* Advance the ratchet one delivery, folding in the friction the last
           pre-run exposed (its errors + long tasks) before the law is applied. */
        advance: function (justify) {
          var last = window.__darkithLastRun;
          if (last) window.ClearanceLoop.absorb(last);
          var r = window.ClearanceLoop.advance(justify);
          if (window.__darkithToast) window.__darkithToast('ClearanceLoop: ' + window.ClearanceLoop.verdict() + ' (flux ' + window.ClearanceLoop.flux() + ')');
          return r;
        },
        ui: function () { return window.ClearanceLoop.ui(); },
        report: function () { return window.ClearanceLoop.report(); }
      };
    }
    return window.DarkithCL;
  }
  function fab() {
    if (document.getElementById("prerun-fab")) return;
    var b = document.createElement("button");
    b.id = "prerun-fab"; b.type = "button";
    b.title = "Pre-runner \u2014 race the race before the race";
    b.setAttribute("aria-label", "Pre-runner");
    b.textContent = "\u25b6";
    b.style.cssText = "position:fixed;right:12px;bottom:12px;z-index:2147483000;width:46px;height:46px;border-radius:50%;" +
      "border:1px solid #2a2e35;background:#14171c;color:#ff8a3d;font-size:18px;line-height:1;cursor:pointer;" +
      "box-shadow:0 6px 20px rgba(0,0,0,.5);opacity:.85;-webkit-tap-highlight-color:transparent";
    b.addEventListener("click", function () { var p = api(); if (p) p.ui(); });
    (document.body || document.documentElement).appendChild(b);
  }
  function register() {
    var p = api(), c = clApi(); fab();
    /* Remember the last pre-run report so ClearanceLoop can absorb its friction. */
    if (p && !window.__prerunWrapped) {
      window.__prerunWrapped = true;
      var orig = p.run;
      p.run = function (o) { return Promise.resolve(orig(o)).then(function (r) { window.__darkithLastRun = r; return r; }); };
    }
    if (window.Omega && window.Omega.BUILTINS) {
      if (!window.Omega.BUILTINS.prerun) window.Omega.BUILTINS.prerun = function () { if (p) p.ui(); return "(pre-running \u2014 see the overlay)"; };
      if (!window.Omega.BUILTINS.clearance) window.Omega.BUILTINS.clearance = function () { if (c) c.ui(); return null; };
    }
    if (typeof window.CMD_REGISTRY === "object" && window.CMD_REGISTRY) {
      if (!window.CMD_REGISTRY.prerun) window.CMD_REGISTRY.prerun = { icon: "\u25b6", label: "Pre-run", group: "Audit" };
      if (!window.CMD_REGISTRY.clearance) window.CMD_REGISTRY.clearance = { icon: "\u25c9", label: "ClearanceLoop", group: "Audit" };
    }
    if (typeof window.dispatchCommand === "function" && !window.__prerunPatched) {
      window.__prerunPatched = true;
      var origD = window.dispatchCommand;
      window.dispatchCommand = function (cmd) {
        if (cmd === "prerun") { if (p) p.ui(); return; }
        if (cmd === "clearance") { if (c) c.ui(); return; }
        return origD.apply(this, arguments);
      };
    }
  }
  ready(function () { setTimeout(register, 0); });
  window.DarkithPrerunReady = register;
})();
"""


def wrap_engines(engines) -> str:
    blocks = [PR_START + "\n<script>\n" + js.replace("</script", "<\\/script") + "\n</script>" for js in engines]
    return "\n".join(blocks) + "\n" + PR_END


def wrap_shim() -> str:
    return PS_START + "\n<script>\n" + SHIM.strip() + "\n</script>\n" + PS_END


def strip(text: str, start: str, end: str) -> str:
    return re.sub(re.escape(start) + r".*?" + re.escape(end) + r"\n?", "", text, flags=re.S)


def inject_before_close_body(text: str, block: str) -> str:
    idx = text.rfind("</body>")
    if idx < 0:
        raise SystemExit("no </body> to anchor against")
    return text[:idx] + block + "\n" + text[idx:]


def inject_after_first_script(text: str, block: str) -> str:
    """Insert right after the document's FIRST <script>…</script>.

    Anchoring here is deliberate. build/build-forge.py injects its own blocks at
    the last </body> and build/make_core.py extracts the SAVF core from the FIRST
    <script>; inserting after that script is therefore invisible to both — the
    core extraction is untouched and neither tool's re-injection (which happens
    at </body>) can reorder this block, so both `--check`s reproduce byte-for-byte.
    """
    end = text.find("</script>")
    if end < 0:
        return inject_before_close_body(text, block)
    end += len("</script>")
    return text[:end] + "\n" + block + text[end:]


def inject_doc(text: str, engines, shim: str) -> str:
    text = strip(text, PR_START, PR_END)
    text = strip(text, PS_START, PS_END)
    return inject_after_first_script(text, wrap_engines(engines) + "\n" + shim)


def get_carrier(shell: str) -> str:
    m = CARRIER_RE.search(shell)
    if not m:
        raise SystemExit("forge carries no studio-src")
    end = shell.find("</script>", m.end())
    return shell[m.end():end].replace("<\\/script", "</script")


def set_carrier(shell: str, studio: str) -> str:
    m = CARRIER_RE.search(shell)
    end = shell.find("</script>", m.end())
    return shell[:m.end()] + studio.replace("</script", "<\\/script") + shell[end:]


def syntax_gate(js: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
        path = f.name
    r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
    pathlib.Path(path).unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit("engine/shim does not parse:\n" + r.stderr.strip()[:800])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify sync; write nothing")
    args = ap.parse_args()

    engines = [e.read_text(encoding="utf-8") for e in ENGINES]
    for e in engines:
        syntax_gate(e)
    syntax_gate(SHIM)
    shim = wrap_shim()

    edits = {}
    for p in SHELLS:
        edits[p] = inject_doc(p.read_text(encoding="utf-8"), engines, shim)

    # The forge shell: inject its own shell, and the carrier it embeds.
    shell = FORGE.read_text(encoding="utf-8")
    shell_new = inject_doc(shell, engines, shim)
    carrier_new = inject_doc(get_carrier(shell_new), engines, shim)
    edits[FORGE] = set_carrier(shell_new, carrier_new)

    drift = []
    for p, text in edits.items():
        if args.check:
            if p.read_text(encoding="utf-8") != text:
                drift.append(p.name)
        else:
            p.write_text(text, encoding="utf-8")
            print(f"  injected {p.name:<26} {len(text):>8} B")

    if args.check:
        if drift:
            print("integrate-prerunner: OUT OF SYNC — " + ", ".join(drift))
            return 1
        print("integrate-prerunner: in sync")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
