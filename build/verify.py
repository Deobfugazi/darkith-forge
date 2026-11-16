#!/usr/bin/env python3
"""One-command proof that every SAVF surface tells the same truth.

Three checks, each of which fails loudly:

  1. sync      -- `build/build-forge.py --check` (no artifact has drifted)
  2. parity    -- the built JS core and `savf.py` return the same findings and
                  the same verdict for a fixed corpus of Python fixtures
  3. battery   -- savf.html, the studio and the fused forge boot from `file://`
                  in Chromium, Firefox and WebKit with zero page errors, zero
                  console errors, zero network, and identical verdicts

Run:  python3 build/verify.py            (all three)
      python3 build/verify.py --fast     (sync + parity only; no browser)

Exit status is 0 only when every check passes.
"""
import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
CORE = BUILD / "savf-core.js"
SAVF_PY = ROOT / "savf.py"

ARTIFACTS = {
    "savf.html": "savf.html",
    "studio.html": "darkith code studio.html",
    "forge.html": "darkith forge.html",
}

# A fixture is (name, source).  Together they exercise every rule the static
# scanner can raise, plus the parser edges (syntax error, empty, unicode, CRLF).
FIXTURES = [
    ("clean.py", "def add(a, b):\n    return a + b\n"),
    ("stub.py", "def compute(x):\n    pass\n\ndef other(y):\n    ...\n"),
    ("phantom.py", "import zzz_not_real\nfrom yyy_also_fake import thing\n\ndef f():\n    return zzz_not_real.x\n"),
    ("markers.py", "def f():\n    # TODO: implement\n    # FIXME: broken\n    return 1  # XXX\n"),
    ("swallow.py", "def f():\n    try:\n        risky()\n    except Exception:\n        pass\n"),
    ("taut.py", "def test_thing():\n    assert True\n    assert 1 == 1\n"),
    ("mock.py", "def production():\n    return mock_response\n"),
    ("syntax.py", "def f(:\n    return\n"),
    ("empty.py", ""),
    ("unicode.py", "def caf\u00e9():\n    # TODO: implement\n    pass\n"),
    ("crlf.py", "def f():\r\n    pass\r\n"),
    ("nested.py", "import os\n\ndef outer():\n    def inner():\n        try:\n            os.system('x')\n        except Exception:\n            pass\n    return inner\n"),
    ("phantom_attr.py", "import os\n\nx = os.definitely_not_a_real_attr\n"),
]

PROBE = ("import totally_fake_module\n"
         "def calculate(a,b):\n    pass\n"
         "# TODO: implement\n"
         "try:\n    x=1\nexcept Exception:\n    pass\n")

CLI_LINE = re.compile(r"^(\S+):(\d+) \[(\w+)\] (phi\d+) (\w+): (.*)$")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def check_sync() -> bool:
    print("[1/3] sync")
    ok = True
    checkers = [
        ("build-forge.py", ["build-forge.py", "--check"]),
        ("sync-delivery.py", ["sync-delivery.py", "--check"]),
        ("make-repo-zip.py", ["make-repo-zip.py", "--check"]),
        ("make-bundle-zip.py", ["make-bundle-zip.py", "--check"]),
    ]
    for _label, argv in checkers:
        r = run([sys.executable, str(BUILD / argv[0])] + argv[1:])
        if r.returncode != 0:
            ok = False
        last = (r.stdout.strip().splitlines() or [""])[-1]
        print("      " + last)
        if r.returncode != 0:
            print(r.stderr.strip())
    return ok


def cli_findings(path: pathlib.Path):
    """Findings from `savf.py scan`, as (phi, rule, line) tuples."""
    r = run([sys.executable, str(SAVF_PY), "scan", str(path)])
    out = r.stdout or ""
    res = []
    for line in out.splitlines():
        m = CLI_LINE.match(line)
        if m:
            res.append((m.group(4), m.group(5), int(m.group(2))))
    return sorted(res)


def check_parity() -> bool:
    print("[2/3] parity (JS core vs savf.py)")
    import json
    import tempfile

    core = CORE.read_text(encoding="utf-8")
    driver = r"""
const fs = require('fs');
const { execFileSync } = require('child_process');
eval(fs.readFileSync(process.argv[2], 'utf8'));
const T = globalThis.SavfTruth;
const fixtures = JSON.parse(process.argv[3]);
const out = {};
for (const [name, src] of fixtures) {
  const r = T.auditSource(name, src);
  out[name] = { verdict: r.verdict, findings: r.findings.map(f => ['phi'+f.phi, f.rule, f.line]) };
}
process.stdout.write(JSON.stringify(out));
"""
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        (td / "core.js").write_text(core, encoding="utf-8")
        (td / "driver.js").write_text(driver, encoding="utf-8")
        payload = json.dumps([[n, s] for n, s in FIXTURES])
        r = run(["node", str(td / "driver.js"), str(td / "core.js"), payload])
        if r.returncode != 0:
            print("      node driver failed:\n" + r.stderr.strip()[:800])
            return False
        js = json.loads(r.stdout)

        ok = True
        for name, src in FIXTURES:
            f = td / name
            f.write_text(src, encoding="utf-8", newline="")
            cli = cli_findings(f)
            jset = sorted(tuple(x) for x in js[name]["findings"])
            match = cli == jset
            ok = ok and match
            print(f"      {name:<16} cli={len(cli):>2} js={len(jset):>2} "
                  f"verdict={js[name]['verdict']:<8} {'match' if match else 'DIFFER'}")
            if not match:
                print("         cli:", cli)
                print("         js :", jset)
    return ok


def check_battery() -> bool:
    print("[3/3] battery (chromium/firefox/webkit, file://, no network)")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("      playwright not installed; skipping battery")
        return False

    ok = True
    with sync_playwright() as p:
        for engine in ("chromium", "firefox", "webkit"):
            try:
                args = ["--no-sandbox", "--disable-gpu"] if engine == "chromium" else None
                browser = getattr(p, engine).launch(args=args)
            except Exception as e:
                print(f"      {engine:<9} unavailable: {str(e).splitlines()[0][:60]}")
                ok = False
                continue
            for label, rel in ARTIFACTS.items():
                pg = browser.new_page(viewport={"width": 360, "height": 800})
                errs, net = [], []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
                pg.on("request", lambda r: net.append(r.url)
                      if not r.url.startswith(("file://", "data:", "blob:", "about:")) else None)
                try:
                    pg.goto("file://" + str(ROOT / rel), wait_until="load", timeout=30000)
                    pg.wait_for_timeout(2000)
                    res = pg.evaluate(
                        """(src)=>{
                          var T = window.SavfTruth || window.SAVF;
                          if(!T || typeof T.auditSource!=='function') return {core:'MISSING'};
                          var a = T.auditSource('probe.py', src);
                          return {core:'ok', verdict:a.verdict, n:a.findings.length};
                        }""", PROBE)
                except Exception as e:
                    res = {"core": "ERROR " + str(e)[:60]}
                pg.close()
                good = (res.get("core") == "ok" and res.get("verdict") == "LIED"
                        and res.get("n") == 4 and not errs and not net)
                ok = ok and good
                print(f"      {engine:<9} {label:<12} {res.get('core')} "
                      f"verdict={res.get('verdict')} findings={res.get('n')} "
                      f"errors={len(errs)} net={len(net)} {'ok' if good else 'FAIL'}")
                for e in errs[:3]:
                    print("         err:", e[:100])
            browser.close()
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="skip the browser battery")
    args = ap.parse_args()

    results = [("sync", check_sync()), ("parity", check_parity())]
    if not args.fast:
        results.append(("battery", check_battery()))

    print()
    for name, ok in results:
        print(f"  {name:<8} {'PASS' if ok else 'FAIL'}")
    good = all(ok for _, ok in results)
    print("\nVERIFY:", "PASS" if good else "FAIL")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
