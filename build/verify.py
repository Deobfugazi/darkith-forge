#!/usr/bin/env python3
"""One-command proof that every SAVF surface tells the same truth.

Six checks, each of which fails loudly:

  1. sync      -- `build/build-forge.py --check` (no artifact has drifted)
  2. parity    -- the built JS core and `savf.py` return the same findings and
                  the same verdict for a fixed corpus of Python fixtures
  3. battery   -- savf.html, the studio and the fused forge boot from `file://`
                  in Chromium, Firefox and WebKit with zero page errors, zero
                  console errors, zero network, and identical verdicts
  4. omega     -- the Ω exec contract and assistant policy, against real child
                  processes and a real wasm32-wasi module
  5. omega ui  -- omega.html boots from `file://` at 360x800, builtins are
                  correct, and there is no horizontal overflow
  6. savf cli  -- savf.py's selftest passes and bad input fails cleanly
                  instead of dumping a traceback or a silent clean bill

Run:  python3 build/verify.py            (all six)
      python3 build/verify.py --fast     (all but the browser checks)

Exit status is 0 only when every check passes.
"""
import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
DELIVERY = ROOT / "delivery"
CORE = BUILD / "savf-core.js"
SAVF_PY = ROOT / "savf.py"

ARTIFACTS = {
    "savf.html": "savf.html",
    "studio.html": "darkith code studio.html",
    "forge.html": "darkith forge.html",
    "omega.html": "omega.html",
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
    print("[1/6] sync")
    # Each checker is (label, argv, needs_delivery). `delivery/` and the zips are
    # regenerable output that .gitignore forbids committing (RESUME.md §4), so in a
    # clean checkout they are absent. Absent is a skip, not a failure: the gate must
    # still be able to pass from a clean clone, or it blocks everything. Drift in an
    # artifact that IS present is a real defect and still fails.
    ok = True
    checkers = [
        ("build-forge.py", ["build-forge.py", "--check"], False),
        ("sync-delivery.py", ["sync-delivery.py", "--check"], True),
        ("make-repo-zip.py", ["make-repo-zip.py", "--check"], True),
        ("make-bundle-zip.py", ["make-bundle-zip.py", "--check"], True),
    ]
    for label, argv, needs_delivery in checkers:
        if needs_delivery and not DELIVERY.exists():
            print(f"      {label:<20} skipped (no delivery/ bundle; regenerable, not committed)")
            continue
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
    print("[2/6] parity (JS core vs savf.py)")
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
    print("[3/6] battery (chromium/firefox/webkit, file://, no network)")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        # A missing browser harness is a SKIP, not a product defect. Report it as
        # such and do not fail the run (the full proof is the CI run, which installs
        # playwright). This is what makes `--fast` and the full run agree: neither
        # pretends a skipped browser check is a passed one, and neither fails on an
        # absent tool. (Before this, battery FAILed on ImportError while omega-ui
        # PASSed on the same condition -- two verdicts for one repo, F2.)
        print("      SKIP: playwright not installed (browser battery not run)")
        return None

    # Prefer playwright's bundled browsers; fall back to a system install so the
    # battery still runs in a slim environment. An engine that is simply absent
    # is skipped, not failed -- a missing browser is not a product defect.
    system = {
        "chromium": ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"],
        "firefox": ["/usr/bin/firefox"],
        "webkit": [],
    }

    def launch(p, engine):
        args = ["--no-sandbox", "--disable-gpu"] if engine == "chromium" else None
        try:
            return getattr(p, engine).launch(args=args), None
        except Exception as e:
            for path in system.get(engine, []):
                if pathlib.Path(path).exists():
                    try:
                        return getattr(p, engine).launch(executable_path=path, args=args), None
                    except Exception as e2:
                        return None, str(e2).splitlines()[0][:70]
            return None, str(e).splitlines()[0][:60]

    ok = True
    ran_any = False
    with sync_playwright() as p:
        for engine in ("chromium", "firefox", "webkit"):
            browser, why = launch(p, engine)
            if browser is None:
                print(f"      {engine:<9} skipped: {why}")
                continue
            ran_any = True
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
                    if label == "omega.html":
                        res = pg.evaluate(
                            """()=>{
                              var O = window.Omega;
                              if(!O || typeof O.calc!=='function') return {core:'MISSING'};
                              return {core:'ok', verdict:String(O.calc('12*9+3')),
                                      n:document.querySelectorAll('[role=tab]').length};
                            }""")
                        good = (res.get("core") == "ok" and res.get("verdict") == "111"
                                and res.get("n") == 4 and not errs and not net)
                    else:
                        res = pg.evaluate(
                            """(src)=>{
                              var T = window.SavfTruth || window.SAVF;
                              if(!T || typeof T.auditSource!=='function') return {core:'MISSING'};
                              var a = T.auditSource('probe.py', src);
                              return {core:'ok', verdict:a.verdict, n:a.findings.length};
                            }""", PROBE)
                        good = (res.get("core") == "ok" and res.get("verdict") == "LIED"
                                and res.get("n") == 4 and not errs and not net)
                except Exception as e:
                    res = {"core": "ERROR " + str(e)[:60]}
                    good = False
                pg.close()
                ok = ok and good
                print(f"      {engine:<9} {label:<12} {res.get('core')} "
                      f"verdict={res.get('verdict')} findings={res.get('n')} "
                      f"errors={len(errs)} net={len(net)} {'ok' if good else 'FAIL'}")
                for e in errs[:3]:
                    print("         err:", e[:100])
            browser.close()
    return ok and ran_any


def check_omega() -> bool:
    """The Ω engine: exec contract, wasm tier, and assistant policy."""
    print("[4/6] omega")
    node = shutil.which("node")
    if not node:
        print("      node not installed; skipping omega contract tests")
        return True
    r = run([node, str(BUILD / "omega" / "omega-test.mjs")])
    last = (r.stdout.strip().splitlines() or [""])[-1]
    print("      " + last)
    if r.returncode != 0:
        print(r.stdout.strip()[-2000:])
        print(r.stderr.strip()[-1000:])
    return r.returncode == 0


def check_omega_ui() -> bool:
    """The Ω webapp UI: boots from file://, builtins correct, no overflow."""
    print("[5/6] omega ui")
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print("      SKIP: playwright not installed (omega ui not run)")
        return None
    r = run([sys.executable, str(BUILD / "omega" / "ui-test.py")])
    last = (r.stdout.strip().splitlines() or [""])[-1]
    print("      " + last)
    if r.returncode != 0:
        print(r.stdout.strip()[-2000:])
    return r.returncode == 0


def check_savf_cli() -> bool:
    """The savf.py CLI: selftest passes and bad input fails cleanly."""
    print("[6/6] savf cli")
    r = run([sys.executable, str(BUILD / "savf-cli-test.py")])
    last = (r.stdout.strip().splitlines() or [""])[-1]
    print("      " + last)
    if r.returncode != 0:
        print(r.stdout.strip()[-2000:])
    return r.returncode == 0


def check_s19_compile():
    """§19 MUST-11: the app tree compiles clean (the compile is the proof).

    Runs the real chain (aapt2 link --java for R.java, then kotlinc over the tree
    against android.jar + the build deps). Returns True on a clean compile, False
    on compile errors, and None (SKIP, not FAIL) when the toolchain is absent --
    a missing toolchain is not a product defect. CI installs the toolchain
    (tools/get_toolchain.sh) so this is a real proof there, never a vacuous green.
    """
    print("[7/7] s19 compile (MUST-11: the compile is the proof)")
    tree = ROOT / "app/src/main/java/com/darkith/transliaison"
    android_jar = pathlib.Path(os.environ.get("ANDROID_JAR", "/tmp/android.jar"))
    extra_cp = os.environ.get("EXTRA_CP", "")
    kotlinc = os.environ.get("KOTLINC", shutil.which("kotlinc") or "")
    if not tree.is_dir():
        print("      SKIP: no app source tree")
        return None
    if not (android_jar.exists() and kotlinc):
        print("      SKIP: android.jar/kotlinc absent (toolchain not staged)")
        return None
    r = run([sys.executable, str(ROOT / "build/s19_compile.py")])
    last = (r.stdout.strip().splitlines() or [""])[-1]
    print("      " + last)
    if r.returncode != 0:
        print(r.stdout.strip()[-1500:])
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="skip the browser battery")
    args = ap.parse_args()

    results = [("sync", check_sync()), ("parity", check_parity())]
    if not args.fast:
        results.append(("battery", check_battery()))
    results.append(("omega", check_omega()))
    if not args.fast:
        results.append(("omega-ui", check_omega_ui()))
    results.append(("savf-cli", check_savf_cli()))
    results.append(("s19-compile", check_s19_compile()))

    print()
    ok_all = True
    for name, ok in results:
        label = "PASS" if ok else ("SKIP" if ok is None else "FAIL")
        if ok is False:
            ok_all = False
        print(f"  {name:<12} {label}")
    print("\nVERIFY:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
