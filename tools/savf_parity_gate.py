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
import hashlib
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

# f-string replacement fields are real code (PEP 701, Python 3.12+): a NAME or
# COMMENT inside `{...}` is a token CPython sees.  The browser lexer emits one
# STRING token per literal, so these cases pin the scan findings that must still
# agree across the two engines.
FSTRING_CASES = {
    "field_name": 'x = f"{MOCK_VALUE}"\n',
    "attribute": 'x = f"{obj.MOCK_X}"\n',
    "format_spec": 'x = f"{v:>{MOCK_W}}"\n',
    "nested_spec": 'x = f"{v:{WIDTH}d}"\n',
    "debug_spec": 'x = f"{MOCK_V=}"\n',
    "multiline": 'x = f"""\n{SAMPLE_X}\n"""\n',
    "nested_fstring": "x = f\"{f'{FAKE_A}'}\"\n",
    "comment_in_field": 'x = f"""{1 # TODO here\n}"""\n',
    "kwarg": 'x = f"{g(MOCK_1=2)}"\n',
    "dict_in_field": 'x = f"{ {MOCK_K: 1} }"\n',
    "lambda_in_field": 'x = f"{(lambda: MOCK_D)()}"\n',
    "raw_prefix": 'x = rf"{MOCK_R}"\n',
    "upper_prefix": 'x = F"{MOCK_S}"\n',
    "literal_text_only": 'x = f"TODO MOCK_A"\n',
    "escaped_braces": 'x = f"{{MOCK_C}}"\n',
    "string_in_field": 'x = f"{d[\'MOCK_A\']}"\n',
    "bytes_not_fstring": 'x = b"MOCK_T"\n',
    "concat": 'x = "a" f"{MOCK_B}"\n',
}


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


def py_glog(case: list):
    """Outcome of the exp/log inverse: a value, or the fact that it refuses."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("savf_ref_g", SAVF_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        return ["ok", mod.g_log(*case)]
    except Exception:
        return ["err", "refused"]


# g is undefined once expm1(x) rounds to -1 (x below ~ -36.7). Both engines must
# refuse there instead of returning inf/Infinity, and agree elsewhere.
GLOG_CASES = [
    [1.0, 2, -3, 20], [1.0, 2, -4, 20], [0.5, 2, -3, 20], [1.0, 10, -2, 50],
    [1.0, 1.0000001, -40, 10], [0.0, 2, -3, 20], [1.0, 2, 3, 20],
]

# Freeze/seal cases. The first two cover the float-formatting edge: theta_mut=1
# is an int in JavaScript and 1.0 in Python, and a lock that renders differently
# in the two tools fails to verify across them.
SEAL_CASES = [
    {"files": {"a.py": "a" * 64, "b.py": "b" * 64},
     "thresholds": {"theta_mut": 1, "theta_cov": 0.8}, "exemptions": [], "chart": "math"},
    {"files": {"m.py": "c" * 64},
     "thresholds": {"theta_mut": 0.6, "theta_cov": 1}, "exemptions": ["phi5"], "chart": "raster"},
    {"files": {"pkg/x.py": "d" * 64, "pkg/y.py": "e" * 64, "z.py": "f" * 64},
     "thresholds": {"theta_mut": 0.75, "theta_cov": 0.9}, "exemptions": ["a.py", "b.py"],
     "chart": "unspecified"},
]

# A lock is verified from its text, because that is what savf.py re-reads.  An
# integer threshold ("1") and a float one ("1.0") are the same JS Number but
# different Python values, so the page must seal whichever literal the file
# carries.  Each case is (lock body as Python types, the exact text to verify).
def _lock_text(body: dict, mut_literal: str | None = None) -> str:
    text = json.dumps({**body, "seal": hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()},
        indent=2, sort_keys=True)
    if mut_literal is not None:
        text = text.replace(f'"theta_mut": {body["thresholds"]["theta_mut"]!r}',
                            f'"theta_mut": {mut_literal}')
    return text


LOCK_CASES = []
for _thr, _lit in (({"theta_mut": 1, "theta_cov": 0.8}, None),
                   ({"theta_mut": 1.0, "theta_cov": 0.8}, None),
                   ({"theta_mut": 1.0, "theta_cov": 0.8}, "1e0")):
    _body = {"version": 1, "files": {"a.py": "a" * 64}, "thresholds": _thr,
             "exemptions": [], "chart": "math"}
    _text = _lock_text(_body, _lit)
    # The page parses the textarea with JSON.parse, so the object it verifies
    # carries the seal; the text travels alongside and is authoritative.
    LOCK_CASES.append((json.loads(_text), _text))


def py_findings(src: str) -> list:
    """Scan findings for one source string, as the CLI reports them."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(src)
        path = f.name
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("savf_ref", SAVF_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return sorted([f["rule"], f["line"], f["phi"], f["msg"]]
                      for f in mod.scan_file(path, set()))
    finally:
        pathlib.Path(path).unlink(missing_ok=True)


def main() -> int:
    # savf.html is TRACKED (its absence is a defect); savf.py is generated. Playwright is
    # a runtime. Only the last two are skips — exit 3, never a silent exit 0.
    if not SAVF_HTML.is_file():
        print(f"savf_parity_gate: FAIL — {SAVF_HTML} is tracked but missing (broken tree)")
        return 1
    if not SAVF_PY.is_file():
        print("savf_parity_gate: SKIP — savf.py not generated")
        return 3
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("savf_parity_gate: SKIP — playwright not installed")
        return 3

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
            return 3
        p = b.new_page()
        p.goto(SAVF_HTML.as_uri(), wait_until="load", timeout=60000)
        p.wait_for_timeout(800)
        js_v = p.evaluate("(c)=>{const o={};for(const k in c){o[k]=window.SAVF.core.verdict(c[k]);}return o;}", cases)
        js_s = p.evaluate("(ks)=>{const C=window.SAVF.core,o={};for(const k of ks){const a=k.split('/');o[k]=String(C.chartSign(a[0],a[1],a[2]));}return o;}", sign_keys)
        js_f = p.evaluate(
            """(cases)=>{
              const std=Object.create(null);(window.SAVF_STDLIB||[]).forEach(n=>{std[n]=1;});
              const o={};
              for(const k in cases){
                o[k]=window.SAVF.scan.scanSource('t.py', cases[k],
                  {stdlib:std, stdattrs:window.SAVF_STDATTRIB||{}, local:Object.create(null),
                   installed:Object.create(null)})
                  .map(x=>[x.rule,x.line,x.phi,x.msg]).sort();
              }
              return o;
            }""", FSTRING_CASES)
        js_g = p.evaluate(
            """(cs)=>cs.map(c=>{try{return ['ok',window.SAVF.core.gLog.apply(null,c)];}
                               catch(e){return ['err','refused'];}})""", GLOG_CASES)
        js_lock = p.evaluate(
            """(cs)=>cs.map(([body,text])=>{
                 try { return window.SAVF.audit.checkFreeze(body, body.files, text); }
                 catch(e) { return {ok:false, problems:[String(e)]}; }
               })""", [[b, t] for b, t in LOCK_CASES])
        js_seal = p.evaluate(
            """(cs)=>cs.map(c=>{
                 const l = window.SAVF.audit.freeze(c.files, {thresholds:c.thresholds,
                   exemptions:c.exemptions, chart:c.chart});
                 return [l.seal, window.SAVF.audit.lockToJson(l)];
               })""", SEAL_CASES)
        b.close()

    py_f = {k: py_findings(v) for k, v in FSTRING_CASES.items()}
    fdiff = {k: (py_f[k], js_f[k]) for k in py_f
             if [[str(y) for y in x] for x in py_f[k]] != [[str(y) for y in x] for x in js_f[k]]}
    if fdiff:
        print("savf_parity_gate: FAIL — f-string field scanning disagrees")
        for k, (a, b) in list(fdiff.items())[:10]:
            print(f"   {k}: py={a} js={b}")
        return 1

    py_g = [py_glog(c) for c in GLOG_CASES]
    gdiff = []
    for c, a, b in zip(GLOG_CASES, py_g, js_g):
        if a[0] != b[0] or (a[0] == "ok" and abs(a[1] - b[1]) > 1e-12):
            gdiff.append((c, a, b))
    if gdiff:
        print("savf_parity_gate: FAIL — exp/log inverse disagrees")
        for c, a, b in gdiff[:10]:
            print(f"   g_log{c}: py={a} js={b}")
        return 1

    # A lock frozen in the browser must verify in the CLI and the reverse, so the
    # seal bytes and the emitted JSON both have to match Python exactly.  Python
    # writes 1.0 where JavaScript writes 1, which is why this is checked on the
    # rendered text and not only on the hash.
    lockdiff = []
    for c, (js_seal_hex, js_lock_text) in zip(SEAL_CASES, js_seal):
        # The CLI declares --theta-mut/--theta-cov as type=float, so a threshold
        # is always a Python float no matter what was typed on the command line.
        # The page's number input yields a JS number, which has no int/float
        # distinction, so both sides must be compared after that coercion.
        thr = {"theta_mut": 0.6, "theta_cov": 0.8}
        thr.update({k: float(v) for k, v in c["thresholds"].items()})
        body = {"version": 1, "files": c["files"], "thresholds": thr,
                "exemptions": sorted(c["exemptions"]), "chart": c["chart"]}
        py_seal_hex = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        py_text = json.dumps({**body, "seal": py_seal_hex}, indent=2, sort_keys=True)
        if js_seal_hex != py_seal_hex:
            lockdiff.append((c["chart"], c["thresholds"], "seal", py_seal_hex, js_seal_hex))
        elif js_lock_text != py_text:
            lockdiff.append((c["chart"], c["thresholds"], "lock text", py_text, js_lock_text))
    if lockdiff:
        print("savf_parity_gate: FAIL — freeze lock disagrees (a lock frozen on one side "
              "would not verify on the other)")
        for chart, thr, what, a, b in lockdiff[:6]:
            print(f"   chart={chart} thresholds={thr} {what}:")
            print(f"     py={a!r}")
            print(f"     js={b!r}")
        return 1

    # A lock sealed by Python must verify in the page, and the page must agree
    # with Python about the ones it rejects.
    badlocks = [(b, t, r) for (b, t), r in zip(LOCK_CASES, js_lock) if not r["ok"]]
    if badlocks:
        print("savf_parity_gate: FAIL — a Python-sealed lock does not verify in the page")
        for body, text, r in badlocks[:4]:
            print(f"   thresholds={body['thresholds']}: {r['problems']}")
        return 1

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
          f"python and browser; {len(FSTRING_CASES)} f-string field cases, "
          f"{len(GLOG_CASES)} exp/log inverse cases, {len(SEAL_CASES)} freeze locks and "
          f"{len(LOCK_CASES)} cross-tool lock verifications agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
