#!/usr/bin/env python3
"""savf parity gate — the Python and browser SAVF engines must agree.

savf.py (stdlib CLI) and savf.html (offline single-file webapp) are two ports of
one formulary. If they ever disagree on a verdict or a chart sign, one of them is
lying about the same claim — the exact failure this project exists to prevent.
This gate runs both over the same inputs and fails on any divergence.

Runs savf.py directly and drives savf.html through playwright/chromium (falls
back to a system chromium). Skips loudly if no browser is available.

Usage: python3 tools/savf_parity_gate.py
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SAVF_PY = ROOT / "savf.py"
SAVF_HTML = ROOT / "savf.html"
VALID = {"x": ["L2R", "R2L"], "y": ["B2T", "T2B"], "z": ["NEAR2FAR", "FAR2NEAR"]}


def py_verdict(states: dict) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(states, f)
        path = f.name
    r = subprocess.run([sys.executable, str(SAVF_PY), "verdict", path],
                       capture_output=True, text=True)
    return r.stdout.strip()


def py_sign(chart: str, axis: str, move: str) -> str:
    r = subprocess.run([sys.executable, str(SAVF_PY), "sign", "--chart", chart,
                        "--axis", axis, "--move", move], capture_output=True, text=True)
    return r.stdout.strip()


def main() -> int:
    if not SAVF_PY.is_file() or not SAVF_HTML.is_file():
        print("savf_parity_gate: SKIP — savf.py or savf.html missing")
        return 0
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("savf_parity_gate: SKIP — playwright not installed")
        return 0

    base = {f"phi{i}": "pass" for i in range(11)}
    cases = {"all_pass": dict(base)}
    for g in ("phi0", "phi2", "phi3", "phi8", "phi9", "phi10"):
        c = dict(base); c[g] = "fail"; cases["hard_" + g] = c
    for g in ("phi4", "phi5", "phi6", "phi7"):
        c = dict(base); c[g] = "fail"; cases["soft_" + g] = c
    c = dict(base); del c["phi5"]; cases["marginal_phi5"] = c

    py_v = {k: py_verdict(v) for k, v in cases.items()}
    sign_keys = [f"{ch}/{ax}/{mv}" for ch in ("math", "raster", "sbaf0")
                 for ax, mvs in VALID.items() for mv in mvs]
    py_s = {k: py_sign(*k.split("/")) for k in sign_keys}

    exe = next((c for c in ("/usr/bin/chromium", "/usr/bin/chromium-browser",
                            "/usr/bin/google-chrome") if pathlib.Path(c).exists()), None)
    with sync_playwright() as pw:
        kwargs = {"args": ["--no-sandbox"]}
        if exe:
            kwargs["executable_path"] = exe
        try:
            b = pw.chromium.launch(**kwargs)
        except Exception as e:
            print(f"savf_parity_gate: SKIP — no browser ({str(e)[:60]})")
            return 0
        p = b.new_page()
        p.goto(SAVF_HTML.as_uri(), wait_until="load", timeout=60000)
        p.wait_for_timeout(800)
        js_v = p.evaluate("(c)=>{const o={};for(const k in c){o[k]=window.SAVF.core.verdict(c[k]);}return o;}", cases)
        js_s = p.evaluate("(ks)=>{const C=window.SAVF.core,o={};for(const k of ks){const a=k.split('/');o[k]=String(C.chartSign(a[0],a[1],a[2]));}return o;}", sign_keys)
        b.close()

    vdiff = {k: (py_v[k], js_v[k]) for k in py_v if py_v[k] != js_v[k]}
    sdiff = {k: (py_s[k], js_s[k]) for k in py_s if py_s[k] != js_s[k]}
    if vdiff or sdiff:
        print("savf_parity_gate: FAIL — savf.py and savf.html disagree")
        for k, (a, b) in list(vdiff.items())[:10]:
            print(f"   verdict {k}: py={a} js={b}")
        for k, (a, b) in list(sdiff.items())[:10]:
            print(f"   sign {k}: py={a} js={b}")
        return 1
    print(f"savf_parity_gate: PASS — {len(py_v)} verdicts + {len(py_s)} chart signs agree across "
          f"python and browser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
