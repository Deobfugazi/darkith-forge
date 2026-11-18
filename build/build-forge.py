#!/usr/bin/env python3
"""DARKITH Forge build pipeline -- one source of truth, many hosts.

SAVF is one truth function.  This pipeline makes every host consume the same
core, so one input yields one verdict wherever it is computed:

    savf.html            standalone page          carries the core
    code studio          standalone code manager  carries the core
    darkith forge        fused shell              carries the core
    terminal (TermKit)   shell surface            `savf` builtin -> the core

Source of truth
---------------
`darkith home forge.html` is the canonical artifact: it carries the newest
studio and the newest TermKit.  The disk file `darkith code studio.html` and the
fused `darkith forge.html` are *outputs* regenerated from it, which is what ends
the drift between the three copies.

Idempotency
-----------
Every injected block is delimited by a marker pair and replaced on each build,
so running the pipeline twice never doubles a payload.

Run:  python3 build/build-forge.py
      python3 build/build-forge.py --check     (verify sync, write nothing)
"""
import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"

FORGE = ROOT / "darkith home forge.html"      # canonical shell (source of truth)
FORGE_OUT = ROOT / "darkith forge.html"       # fused artifact
STUDIO = ROOT / "darkith code studio.html"    # standalone mirror of the studio
SAVF_HTML = ROOT / "savf.html"

CORE = BUILD / "savf-core.js"
HOST = BUILD / "savf-host.js"
FACADE = BUILD / "truth-facade.js"

# markers: studio blocks live inside the carrier, shell blocks outside it, so
# they get distinct names and can never be confused by the stripper.
SC_START, SC_END = "<!-- SAVF-CORE:START -->", "<!-- SAVF-CORE:END -->"
SH_START, SH_END = "<!-- SAVF-HOST:START -->", "<!-- SAVF-HOST:END -->"
SS_START, SS_END = "<!-- SAVF-SHELL:START -->", "<!-- SAVF-SHELL:END -->"
ST_START, ST_END = "/* SAVF-TERM:START */", "/* SAVF-TERM:END */"
PF_START, PF_END = "<!-- SAVF-FACADE:START -->", "<!-- SAVF-FACADE:END -->"

CARRIER_RE = re.compile(r'<script type="text/plain" id="studio-src">')
BUILTINS_ANCHOR = "var builtins = Object.create(null);"

TERMINAL_BUILTIN = """%s
  /* `savf <file.py>` -- the terminal surface of the one truth function.  It
     calls the same core the page and the studio call, so the verdict printed
     here is the verdict they would give. */
  builtins["savf"] = function (args) {
    var T = globalThis.SavfTruth;
    if (!T || typeof T.auditSource !== "function") { out("savf: core not loaded"); return 1; }
    if (args[0] === "--gates") {
      for (var g = 0; g <= 10; g++) out("  phi" + g + "  " + (T.gateInfo["phi" + g] || ""));
      return 0;
    }
    var path = args[0] || "";
    if (!path) { out("usage: savf <file.py> | savf --gates"); return 1; }
    var node = sh.fs.resolve(sh.cwd, path);
    if (!node || node.type !== "file") { err("savf: " + path + ": no such file", 1); return 1; }
    var res = T.auditSource(path, sh.fs.read(node));
    out(res.verdict + "  " + res.counts.total + " finding(s) over " + res.files + " file(s)");
    for (var i = 0; i < res.findings.length; i++) {
      var f = res.findings[i];
      out("  phi" + f.phi + "  " + f.rule + "  line " + f.line + "  " + f.msg);
    }
    /* Mirror savf.py's EXIT map so `$?` here means the same as the CLI's:
       PASS 0, REVIEW 2, BLOCKED 3, LIED 4.  Collapsing every non-PASS to 1
       would hide which verdict was reached from `&&`, `||` and scripts. */
    var EXIT = { PASS: 0, REVIEW: 2, BLOCKED: 3, LIED: 4 };
    return (EXIT[res.verdict] != null) ? EXIT[res.verdict] : 1;
  };
%s""" % (ST_START, ST_END)


def wrap_script(js: str) -> str:
    body = js.replace("</script", "<\\/script")
    return "<script>\n" + body + "\n</script>"


def inject(text: str, start: str, end: str, payload: str) -> str:
    """Replace a marked block, or insert a fresh one before the closing body.

    The anchor is the LAST `</body>` in the document: the shell embeds whole HTML
    documents inside JavaScript string literals, so an earlier occurrence would
    land the block inside a string and break the page.
    """
    block = start + "\n" + payload + "\n" + end
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if pattern.search(text):
        return pattern.sub(lambda m: block, text, count=1)
    idx = text.rfind("</body>")
    if idx < 0:
        raise SystemExit("no </body> to anchor against")
    return text[:idx] + block + "\n" + text[idx:]


def strip(text: str, start: str, end: str) -> str:
    return re.sub(re.escape(start) + r".*?" + re.escape(end) + r"\n?", "", text, flags=re.S)


def get_carrier(shell: str) -> str:
    m = CARRIER_RE.search(shell)
    if not m:
        raise SystemExit("shell carries no studio-src")
    end = shell.find("</script>", m.end())
    return shell[m.end():end].replace("<\\/script", "</script")


def set_carrier(shell: str, studio: str) -> str:
    m = CARRIER_RE.search(shell)
    end = shell.find("</script>", m.end())
    return shell[:m.end()] + studio.replace("</script", "<\\/script") + shell[end:]


def patch_studio(studio: str, core: str, host: str) -> str:
    studio = strip(studio, SC_START, SC_END)
    studio = strip(studio, SH_START, SH_END)
    studio = inject(studio, SC_START, SC_END, wrap_script(core))
    studio = inject(studio, SH_START, SH_END, wrap_script(host))
    return studio


def patch_shell(shell: str, core: str) -> str:
    shell = strip(shell, SS_START, SS_END)
    shell = strip(shell, ST_START, ST_END)
    shell = inject(shell, SS_START, SS_END, wrap_script(core))
    if BUILTINS_ANCHOR not in shell:
        raise SystemExit("TermKit anchor missing: cannot add the `savf` builtin")
    shell = shell.replace(BUILTINS_ANCHOR,
                          BUILTINS_ANCHOR + "\n" + TERMINAL_BUILTIN, 1)
    return shell


def patch_page(page: str, facade: str) -> str:
    """Give the standalone page the same unified facade as every other host.

    savf.html ships the raw modules (SavfScan/SavfCore/SavfAudit) but not the
    `SAVF.auditSource` entry point, so it would be the one surface whose API
    differs.  Injecting the facade makes the page, the studio, the forge and the
    terminal answer through one identical call.
    """
    page = strip(page, PF_START, PF_END)
    return inject(page, PF_START, PF_END, wrap_script(facade))


def build_core() -> None:
    subprocess.run([sys.executable, str(BUILD / "make_core.py")], check=True)


def syntax_gate(*paths: pathlib.Path) -> None:
    """Refuse to ship JavaScript that does not parse.

    The payloads are plain JS (the carrier escaping happens at wrap time), so
    `node --check` is an exact test.  A build that cannot parse is a build that
    would white-screen the app; it must fail here, not on the user's phone.
    """
    for p in paths:
        r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"syntax gate FAILED: {p.name}\n{r.stderr.strip()[:800]}")
        print(f"  syntax   {p.name:<20} ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify sync; write nothing")
    args = ap.parse_args()

    build_core()
    core = CORE.read_text(encoding="utf-8")
    host = HOST.read_text(encoding="utf-8")
    facade = FACADE.read_text(encoding="utf-8")
    syntax_gate(CORE, HOST)

    shell0 = FORGE.read_text(encoding="utf-8")
    studio0 = get_carrier(shell0)

    studio1 = patch_studio(studio0, core, host)
    shell1 = set_carrier(shell0, studio1)
    shell2 = patch_shell(shell1, core)
    page1 = patch_page(SAVF_HTML.read_text(encoding="utf-8"), facade)

    if args.check:
        ok = True
        # `darkith forge.html` is a GENERATED output (.gitignore). In a clean checkout it is
        # absent; an absent generated file is a skip, not drift. The canonical inputs
        # (darkith home forge.html, darkith code studio.html, savf.html) are always checked.
        for name, path, want in (
            ("darkith forge.html", FORGE_OUT, shell2),
            ("darkith code studio.html", STUDIO, studio1),
            ("savf.html", SAVF_HTML, page1),
        ):
            if not path.exists():
                print(f"skip: {name} absent (generated output)")
                continue
            if path.read_text(encoding="utf-8") != want:
                print(f"OUT OF SYNC: {name}", file=sys.stderr)
                ok = False
        print("check: " + ("in sync" if ok else "drift detected"))
        return 0 if ok else 1

    FORGE.write_text(shell2, encoding="utf-8")
    FORGE_OUT.write_text(shell2, encoding="utf-8")
    STUDIO.write_text(studio1, encoding="utf-8")
    SAVF_HTML.write_text(page1, encoding="utf-8")

    for label, text in (("studio", studio1), ("forge", shell2), ("page", page1), ("core", core)):
        print(f"  {label:<8} {len(text):>8} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
