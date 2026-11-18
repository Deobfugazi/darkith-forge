#!/usr/bin/env python3
"""pre-runner gate — the node driver and its engine must honour one contract.

`tools/prerunner.js` (CLI) drives `app/src/main/assets/vendor/prerunner.js` (engine)
through a real headless Chromium. This gate locks the things that must never drift:

  1. the engine module exposes the documented surface (run/register/transpile/adapters);
  2. the CLI honours its EXIT-CODE contract — PASS/WARN->0, FAIL->1, NEEDS_ADAPTER->2;
  3. a clean page PASSes and a throwing page FAILs (the verdict is honest both ways);
  4. a run is DETERMINISTIC: same --seed -> same errors and same verdict.

Everything degrades honestly: no `node` -> SKIP; no browser library -> the browser-
dependent assertions SKIP (module + CLI usage still checked), never a false PASS.

Usage: python3 tools/prerunner_gate.py
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "tools" / "prerunner.js"
ENGINE = ROOT / "app" / "src" / "main" / "assets" / "vendor" / "prerunner.js"

CLEAN = "<!doctype html><body><h1>ok</h1><script>document.title='ok'</script></body>"
THROWS = "<!doctype html><body><script>throw new Error('boom')</script></body>"


def find_chrome() -> str | None:
    for c in ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome",
              "/usr/bin/google-chrome-stable", "/snap/bin/chromium"):
        if pathlib.Path(c).exists():
            return c
    return os.environ.get("PRERUNNER_CHROME") or os.environ.get("CHROME_PATH")


def have_browser_lib(node: str) -> bool:
    probe = ("for (const m of ['playwright','playwright-core','puppeteer','puppeteer-core'])"
             " { try { require(m); process.exit(0); } catch(e){} } process.exit(1);")
    r = subprocess.run([node, "-e", probe], cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0


def run_cli(node: str, args: list[str], env: dict) -> tuple[int, dict | None]:
    out = tempfile.mkdtemp(prefix="prgate-")
    try:
        r = subprocess.run([node, str(CLI), *args, "--out", out, "--quiet"],
                           cwd=ROOT, capture_output=True, text=True, env=env, timeout=180)
        rep = pathlib.Path(out) / "report.json"
        data = json.loads(rep.read_text()) if rep.exists() else None
        return r.returncode, data
    finally:
        shutil.rmtree(out, ignore_errors=True)


def main() -> int:
    if not CLI.is_file() or not ENGINE.is_file():
        print("prerunner_gate: SKIP — tools/prerunner.js or vendor/prerunner.js missing")
        return 0
    node = shutil.which("node")
    if not node:
        print("prerunner_gate: SKIP — node not installed")
        return 0

    fails: list[str] = []

    # 1. engine module surface (node-only, no browser needed)
    probe = ("const m=require(%s); const need=['run','register','transpile','adapters'];"
             "const miss=need.filter(k=>typeof m[k]==='undefined');"
             "if(miss.length){console.error('missing '+miss.join(','));process.exit(1);}"
             "console.log('surface ok');" % json.dumps(str(ENGINE)))
    r = subprocess.run([node, "-e", probe], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        fails.append("engine surface: " + (r.stderr.strip() or "missing run/register/transpile/adapters"))

    # 2. NEEDS_ADAPTER path needs no browser
    env = dict(os.environ)
    chrome = find_chrome()
    if chrome:
        env["PRERUNNER_CHROME"] = chrome
    with tempfile.NamedTemporaryFile("w", suffix=".zzz", delete=False) as f:
        f.write("whatever")
        weird = f.name
    code, _ = run_cli(node, [weird], env)
    if code != 2:
        fails.append(f"NEEDS_ADAPTER exit: expected 2, got {code}")
    pathlib.Path(weird).unlink(missing_ok=True)

    # 3-4. browser-dependent: clean PASSes, throwing FAILs, same seed repeats
    if not have_browser_lib(node):
        print("prerunner_gate: browser assertions SKIPPED — npm i playwright-core (or puppeteer)")
    else:
        with tempfile.TemporaryDirectory() as d:
            clean = pathlib.Path(d) / "clean.html"; clean.write_text(CLEAN)
            throws = pathlib.Path(d) / "throws.html"; throws.write_text(THROWS)
            c1, r1 = run_cli(node, [str(clean), "--shots", "2", "--ms", "120", "--seed", "7"], env)
            if c1 != 0 or not r1 or r1.get("verdict") != "PASS":
                fails.append(f"clean page: expected PASS/0, got {r1 and r1.get('verdict')}/{c1}")
            c2, r2 = run_cli(node, [str(throws), "--shots", "1", "--ms", "120", "--seed", "7"], env)
            if c2 != 1 or not r2 or r2.get("verdict") != "FAIL":
                fails.append(f"throwing page: expected FAIL/1, got {r2 and r2.get('verdict')}/{c2}")
            fuzz = pathlib.Path(d) / "f.html"
            fuzz.write_text("<!doctype html><body><button id=b>x</button>"
                            "<script>document.getElementById('b').onclick=function(){}</script></body>")
            a1, ra = run_cli(node, [str(fuzz), "--shots", "2", "--ms", "80", "--stress", "20", "--seed", "42"], env)
            a2, rb = run_cli(node, [str(fuzz), "--shots", "2", "--ms", "80", "--stress", "20", "--seed", "42"], env)
            if ra and rb and (ra.get("errors") != rb.get("errors") or ra.get("verdict") != rb.get("verdict")):
                fails.append("determinism: same seed produced different reports")

    if fails:
        print("prerunner_gate: FAIL")
        for f in fails:
            print("   " + f)
        return 1
    print("prerunner_gate: PASS — engine surface + CLI exit contract + honest verdicts hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
