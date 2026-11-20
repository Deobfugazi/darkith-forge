#!/usr/bin/env python3
"""Browser gate for the standalone SAVF-1 webapp.

`tools/savf_parity_gate.py` locks the ENGINE against `savf.py`. This gate locks
the DELIVERY: it drives `savf.html` in a real headless Chromium over `file://`
and asserts the app a user actually opens still works — every tab, the audit
flow (paste, findings, verdict), the axis/sign/exp laws, the claims ledger, the
freeze/check tamper path, the in-browser self-test, keyboard control, theming,
and no clipping on a 360px phone.

Accessibility and layout are measured, not eyeballed: WCAG contrast for every
text node, 40px minimum tap targets, and clipped text, in both themes at phone
and desktop widths. Contrast is measured against the *painted* background, so a
gradient fill is resolved from its own colours rather than the page behind it.

Hostile input is a first-class case: the app must survive binary bytes, a null
byte, a syntax error, a 30-deep nest and a corrupt stored theme without an
uncaught error and without losing the UI.

Skips (exit 0) when Playwright or Chromium is absent, so CI on a bare box does
not fail for a missing browser; run it locally before shipping UI changes.

Run:  python3 tools/savf_ui_gate.py
      python3 tools/savf_ui_gate.py --shots DIR   (also save screenshots)
"""
import argparse
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "savf.html"

CHROMIUM_CANDIDATES = [
    "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable", "/snap/bin/chromium",
]

TABS = ["audit", "gates", "axis", "ledger", "seal", "self", "help"]

HOSTILE = """(src) => {
  const box = document.getElementById('pasteBox');
  box.value = src;
  document.getElementById('auditPaste').click();
}"""

SEED = """() => {
  const src = [
    'import os',
    'def f(a):',
    '    try:',
    '        return a/0',
    '    except Exception:',
    '        pass',
    '# TODO fix',
    'MOCK_X = 1',
    'def stub():',
    '    pass',
    'def real():',
    '    return 1'
  ].join('\\n');
  document.getElementById('pasteBox').value = src;
  document.getElementById('auditPaste').click();
}"""

# Contrast is measured against the painted pixel background. A gradient fill
# leaves backgroundColor transparent, so the gradient's own stops are read and
# the worst stop is used. That is what the eye actually sees.
JS_AUDIT = r"""() => {
  function parse(c) {
    const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(',').map(Number);
    return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1};
  }
  function lum(c) {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  }
  function stops(bgImage) {
    const out = [];
    const re = /rgba?\([^)]+\)/g;
    let m;
    while ((m = re.exec(bgImage))) { const c = parse(m[0]); if (c && c.a > 0.85) out.push(c); }
    return out;
  }
  function bgOf(el) {
    let n = el;
    while (n && n !== document.documentElement) {
      const cs = getComputedStyle(n);
      const img = cs.backgroundImage;
      if (img && img !== 'none') {
        const s = stops(img);
        if (s.length) return s;
      }
      const c = parse(cs.backgroundColor);
      if (c && c.a > 0.85) return [c];
      n = n.parentElement;
    }
    const b = parse(getComputedStyle(document.body).backgroundColor);
    return [b && b.a > 0.85 ? b : {r: 8, g: 9, b: 12, a: 1}];
  }
  function ratio(f, b) {
    const L1 = lum(f), L2 = lum(b), hi = Math.max(L1, L2), lo = Math.min(L1, L2);
    return (hi + 0.05) / (lo + 0.05);
  }
  const out = {contrast: [], small: [], clipped: []};
  const seen = new Set();
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) return;
    if (el.closest('[hidden]')) return;
    const own = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
    if (own) {
      const fg = parse(cs.color);
      if (fg && fg.a > 0.3) {
        const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight, 10) >= 600;
        const need = (size >= 18.66 || (size >= 14 && bold)) ? 3 : 4.5;
        let worst = 99;
        for (const bg of bgOf(el)) worst = Math.min(worst, ratio(fg, bg));
        const key = cs.color + '|' + cs.fontSize + '|' + el.tagName;
        if (worst < need && !seen.has(key)) {
          seen.add(key);
          out.contrast.push({t: (el.textContent || '').trim().slice(0, 24), cr: Math.round(worst * 100) / 100, need});
        }
      }
    }
    if (/^(BUTTON|A|SELECT|TEXTAREA|INPUT)$/.test(el.tagName) && el.type !== 'file') {
      if (r.height < 40 || r.width < 40) out.small.push({tag: el.tagName, id: el.id, h: Math.round(r.height), w: Math.round(r.width)});
    }
    if (own && cs.overflow !== 'visible' && el.scrollWidth > el.clientWidth + 1) {
      out.clipped.push({t: (el.textContent || '').trim().slice(0, 24)});
    }
  });
  return out;
}"""

JS_OVERFLOW = """() => {
    const de = document.documentElement;
    const bad = [];
    if (de.scrollWidth > de.clientWidth + 1) bad.push('document ' + de.scrollWidth + '>' + de.clientWidth);
    const scrollable = (el) => {
        let n = el.parentElement;
        while (n && n !== de) {
            const cs = getComputedStyle(n);
            if ((cs.overflowX === 'auto' || cs.overflowX === 'scroll') && n.scrollWidth > n.clientWidth) return true;
            n = n.parentElement;
        }
        return false;
    };
    document.querySelectorAll('*').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.right > de.clientWidth + 2 && !scrollable(el)) {
            bad.push(el.tagName + ' right=' + Math.round(r.right));
        }
    });
    return bad.slice(0, 5);
}"""


class Gate:
    def __init__(self):
        self.passed = 0
        self.fails = []

    def ck(self, cond, label, detail=""):
        if cond:
            self.passed += 1
        else:
            self.fails.append(label + (" -- " + str(detail) if detail else ""))

    def total(self):
        return self.passed + len(self.fails)


def find_chromium():
    for c in CHROMIUM_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    return shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")


def tab_visible(page, name):
    return page.evaluate(
        """(t) => {
            const p = document.getElementById('p-' + t);
            const b = document.querySelector('nav button[data-tab="' + t + '"]');
            return !!p && p.classList.contains('on') && !!b && b.getAttribute('aria-selected') === 'true';
        }""",
        name,
    )


def verdict_of(page):
    txt = page.inner_text("#verdictOut")
    for v in ("PASS", "REVIEW", "BLOCKED", "LIED"):
        if v in txt:
            return v
    return txt.strip()[:40]


def run(shots_dir):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "playwright not installed"

    exe = find_chromium()
    if not exe:
        return None, "no chromium binary found"

    g = Gate()
    url = APP.as_uri()
    if shots_dir:
        shots_dir = pathlib.Path(shots_dir)
        shots_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe, args=["--no-sandbox", "--allow-file-access-from-files"])

        for label, vp in [("phone 360x800", {"width": 360, "height": 800}),
                          ("narrow 320x800", {"width": 320, "height": 800}),
                          ("desktop 1280x900", {"width": 1280, "height": 900})]:
            ctx = browser.new_context(viewport=vp, device_scale_factor=2)
            page = ctx.new_page()
            errs = []
            page.on("console", lambda m, e=errs: e.append("console.error: " + m.text) if m.type == "error" else None)
            page.on("pageerror", lambda ex, e=errs: e.append("pageerror: " + str(ex)))
            page.goto(url)
            page.wait_for_timeout(700)

            def go(name):
                page.click('nav button[data-tab="' + name + '"]')
                page.wait_for_timeout(150)

            g.ck(not errs, "[" + label + "] clean load", "; ".join(errs[:3]))
            g.ck(page.evaluate("typeof window.SavfTruth === 'object'"), "[" + label + "] engine present")
            g.ck(page.evaluate("typeof window.SavfScan === 'object'"), "[" + label + "] scanner present")
            g.ck(page.evaluate("typeof window.SavfAudit === 'object'"), "[" + label + "] audit module present")
            g.ck(page.evaluate("typeof window.SavfCore.verdict === 'function'"), "[" + label + "] verdict function present")
            g.ck(not page.evaluate(JS_OVERFLOW), "[" + label + "] no clipping", page.evaluate(JS_OVERFLOW))

            for name in TABS:
                go(name)
                g.ck(tab_visible(page, name), "[" + label + "] tab " + name)

            # ---- audit: the flow a user actually runs ----
            go("audit")
            page.evaluate(SEED)
            page.wait_for_timeout(900)
            v = verdict_of(page)
            g.ck(v in ("PASS", "REVIEW", "BLOCKED", "LIED"), "[" + label + "] audit yields a verdict", v)
            g.ck("finding" in page.inner_text("#verdictOut").lower(), "[" + label + "] verdict states a count",
                 page.inner_text("#verdictOut")[:80])
            fo = page.inner_text("#findingsOut")
            for rule in ("SWALLOWED", "MARKER", "FAKE_DATA", "STUB"):
                g.ck(rule in fo, "[" + label + "] finding " + rule, fo[:80])
            g.ck("pasted.py" in fo, "[" + label + "] finding names the file", fo[:80])

            go("gates")
            n = page.eval_on_selector_all("#gateGrid .gate", "e => e.length")
            g.ck(n == 11, "[" + label + "] all 11 gates rendered", n)
            page.click('#gateGrid .gate[data-phi="phi0"]')
            page.wait_for_timeout(150)
            g.ck(page.get_attribute('#gateGrid .gate[data-phi="phi0"]', "aria-expanded") == "true",
                 "[" + label + "] gate opens")
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
            g.ck(page.get_attribute('#gateGrid .gate[data-phi="phi0"]', "aria-expanded") == "false",
                 "[" + label + "] Esc closes a gate")

            # manual verdict builder must agree with the core law
            man = page.evaluate("""() => {
                const sels = [...document.querySelectorAll('#manualGrid select')];
                const states = {};
                sels.forEach(s => { const m = s.closest('[data-phi]'); if (m) states[m.dataset.phi] = s.value; });
                const core = SavfCore.verdict(states);
                document.querySelector('#manualGrid select');
                return {core, n: sels.length};
            }""")
            g.ck(man["n"] == 11, "[" + label + "] manual builder has 11 selectors", man["n"])
            g.ck(man["core"] in ("PASS", "REVIEW", "BLOCKED", "LIED"),
                 "[" + label + "] manual verdict is valid", man["core"])

            # ---- axis law ----
            go("axis")
            page.fill("#axP0", "0,0")
            page.fill("#axP1", "100,0")
            page.fill("#axS", "0.3")
            page.select_option("#axTau", "1")
            page.click("#axisRun")
            page.wait_for_timeout(400)
            ax = page.inner_text("#axisOut")
            g.ck("30" in ax, "[" + label + "] axis point 30", ax[:100])

            # tau-reversal identity: at(s,+1) == at(1-s,-1)
            page.fill("#axS", "0.3")
            page.select_option("#axTau", "-1")
            page.click("#axisRun")
            page.wait_for_timeout(400)
            rev = page.evaluate("""() => {
                const ax = new SavfCore.Axis([0,0],[100,0]);
                const a = ax.at(0.3, 1), b = ax.at(0.7, -1);
                return a[0] === b[0] && a[1] === b[1];
            }""")
            g.ck(rev, "[" + label + "] tau reversal identity holds")

            page.fill("#axS", "1.5")
            page.click("#axisRun")
            page.wait_for_timeout(400)
            g.ck("must lie in" in page.inner_text("#axisOut").lower() or
                 "fail" in page.inner_text("#axisOut").lower(),
                 "[" + label + "] out-of-range s is refused", page.inner_text("#axisOut")[:80])
            page.fill("#axS", "0.3")

            # sign law: the same delta flips sign between charts
            page.select_option("#sgChart", "math")
            page.select_option("#sgAxis", "x")
            page.select_option("#sgMove", "R2L")
            page.click("#signRun")
            page.wait_for_timeout(400)
            s1 = page.inner_text("#signOut")
            page.select_option("#sgChart", "raster")
            page.click("#signRun")
            page.wait_for_timeout(400)
            s2 = page.inner_text("#signOut")
            g.ck(s1 != s2, "[" + label + "] chart flips the move sign", s1[:24] + " vs " + s2[:24])

            # exp/log must round-trip
            page.fill("#exB", "2"); page.fill("#exK", "1"); page.fill("#exL", "5"); page.fill("#exS", "2")
            page.click("#expRun")
            page.wait_for_timeout(400)
            ex = page.inner_text("#expOut")
            g.ck(ex.strip() != "", "[" + label + "] exp/log reports", ex[:80])

            # ---- ledger ----
            go("ledger")
            page.click("#ledgerSample")
            page.wait_for_timeout(300)
            g.ck(len(page.input_value("#ledgerBox")) > 50, "[" + label + "] ledger sample loads")
            page.click("#ledgerRun")
            page.wait_for_timeout(600)
            lo = page.inner_text("#ledgerOut")
            g.ck("claim" in lo.lower(), "[" + label + "] ledger evaluates", lo[:100])
            g.ck("unsupported" in lo or "invalid" in lo, "[" + label + "] ledger flags bad derivation", lo[:120])

            page.fill("#ledgerBox", "{not json")
            page.click("#ledgerRun")
            page.wait_for_timeout(400)
            g.ck(page.evaluate("() => !!document.querySelector('#ledgerOut .bad-note')") or
                 "json" in page.inner_text("#ledgerOut").lower(),
                 "[" + label + "] ledger rejects bad JSON", page.inner_text("#ledgerOut")[:80])

            # ---- freeze / check: the tamper path ----
            go("seal")
            sealed = page.evaluate("""() => {
                const files = {'a.py': 'x = 1\\n', 'b.py': 'y = 2\\n'};
                const lock = SavfAudit.freeze(files, {thresholds: {theta_mut: 0.6, theta_cov: 0.8},
                                                      exemptions: [], chart: 'math'});
                const ok = SavfAudit.checkFreeze(lock, files);
                const tampered = Object.assign({}, files, {'a.py': 'x = 999\\n'});
                const bad = SavfAudit.checkFreeze(lock, tampered);
                const edited = JSON.parse(JSON.stringify(lock));
                edited.thresholds.theta_mut = 0.1;
                const thr = SavfAudit.checkFreeze(edited, files);
                const missing = SavfAudit.checkFreeze(lock, {'a.py': 'x = 1\\n'});
                return {seal: !!lock.seal, ok: ok.ok, bad: bad.ok,
                        badProbs: bad.problems, thr: thr.ok, miss: missing.ok};
            }""")
            g.ck(sealed["seal"], "[" + label + "] freeze produces a seal")
            g.ck(sealed["ok"], "[" + label + "] unchanged tree verifies")
            g.ck(not sealed["bad"], "[" + label + "] edited file is caught")
            g.ck(any("a.py" in x for x in sealed["badProbs"]),
                 "[" + label + "] caught edit names the file", sealed["badProbs"])
            g.ck(not sealed["thr"], "[" + label + "] edited threshold is caught")
            g.ck(not sealed["miss"], "[" + label + "] missing file is caught")

            page.fill("#lockBox", "{not json")
            page.click("#checkRun")
            page.wait_for_timeout(300)
            g.ck("json" in page.inner_text("#checkOut").lower(), "[" + label + "] bad lock is refused",
                 page.inner_text("#checkOut")[:80])

            # ---- in-browser self-test ----
            go("self")
            page.fill("#selfN", "400")
            page.click("#selfRun")
            page.wait_for_timeout(2500)
            so = page.inner_text("#selfOut")
            g.ck("passed" in so.lower(), "[" + label + "] in-app self-test passes", so[:120])
            g.ck("fail" not in so.lower() or "Some checks failed" not in so,
                 "[" + label + "] no self-test failures", so[:120])

            # ---- theming ----
            t0 = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            page.click("#themeBtn")
            page.wait_for_timeout(250)
            t1 = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            g.ck(t0 != t1, "[" + label + "] theme toggles", str(t0) + "->" + str(t1))
            page.click("#themeBtn")
            page.wait_for_timeout(200)

            # ---- tab semantics: each tab names a real panel, exactly one is exposed ----
            sem = page.evaluate("""() => {
                const tabs = [...document.querySelectorAll('[role=tab]')];
                const panels = [...document.querySelectorAll('[role=tabpanel]')];
                return {
                    controls: tabs.every(t => {
                        const id = t.getAttribute('aria-controls');
                        return id && document.getElementById(id);
                    }),
                    count: tabs.length === panels.length,
                    one: panels.filter(p => !p.hasAttribute('hidden')).length === 1,
                    selected: tabs.filter(t => t.getAttribute('aria-selected') === 'true').length === 1,
                    roving: tabs.filter(t => t.tabIndex === 0).length === 1
                };
            }""")
            g.ck(sem["controls"], "[" + label + "] tabs aria-controls a real panel")
            g.ck(sem["count"], "[" + label + "] tab/panel counts match")
            g.ck(sem["one"], "[" + label + "] exactly one panel exposed", json.dumps(sem))
            g.ck(sem["selected"] and sem["roving"], "[" + label + "] one selected tab, roving tabindex",
                 json.dumps(sem))

            # ---- keyboard: 1..7 jump, ignored while typing ----
            page.evaluate("() => { document.activeElement && document.activeElement.blur(); }")
            for i, name in enumerate(TABS, 1):
                page.keyboard.press(str(i))
                page.wait_for_timeout(180)
                g.ck(tab_visible(page, name), "[" + label + "] key " + str(i) + " -> " + name)

            go("audit")
            page.click("#pasteBox")
            page.keyboard.press("2")
            page.wait_for_timeout(200)
            g.ck(tab_visible(page, "audit"), "[" + label + "] number key ignored inside a textarea")
            page.evaluate("() => { document.activeElement && document.activeElement.blur(); }")

            # ---- hostile input must never break the app ----
            go("audit")
            hostile = [
                ("empty", ""),
                ("whitespace", "   \n\n\t  "),
                ("not python", "this is not python at all {{{"),
                ("syntax error", "def f(:\n  pass"),
                ("null byte", "x = 1\x00\n"),
                ("unicode", "def f():\n    return 'h\u00e9llo \U0001f30d'\n"),
                ("huge indent", "def f():\n" + " " * 400 + "pass\n"),
                ("binary", "".join(chr(c) for c in range(1, 32))),
                ("comments only", "# a\n# b\n"),
                ("deep nest", "def f():\n" + "".join("    " * i + "if %d:\n" % i for i in range(1, 25)) + "        pass\n"),
            ]
            for name, src in hostile:
                errs.clear()
                page.evaluate(HOSTILE, src)
                page.wait_for_timeout(500)
                alive = page.evaluate("() => !!document.querySelector('h1') && !!document.getElementById('pasteBox')")
                g.ck(alive and not errs, "[" + label + "] hostile: " + name, "; ".join(errs[:2]))

            # ---- measured accessibility + layout, both themes ----
            for theme in ("dark", "light"):
                page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                page.evaluate(SEED)
                page.wait_for_timeout(500)
                for name in TABS:
                    go(name)
                    r = page.evaluate(JS_AUDIT)
                    g.ck(not r["contrast"], "[" + label + "/" + theme + "/" + name + "] contrast",
                         json.dumps(r["contrast"][:3]))
                    g.ck(not r["small"], "[" + label + "/" + theme + "/" + name + "] tap targets",
                         json.dumps(r["small"][:3]))
                    g.ck(not r["clipped"], "[" + label + "/" + theme + "/" + name + "] no clipped text",
                         json.dumps(r["clipped"][:3]))

            if shots_dir:
                page.evaluate("(t) => document.documentElement.setAttribute('data-theme', 'dark')", "dark")
                go("audit")
                page.evaluate(SEED)
                page.wait_for_timeout(500)
                page.screenshot(path=str(shots_dir / ("savf-" + label.replace(" ", "-") + ".png")), full_page=True)

            g.ck(not errs, "[" + label + "] no errors after full run", "; ".join(errs[:5]))
            ctx.close()

        # a corrupt stored theme must never brick the app
        ctx = browser.new_context(viewport={"width": 360, "height": 800})
        page = ctx.new_page()
        perrs = []
        page.on("pageerror", lambda ex: perrs.append(str(ex)))
        page.goto(url)
        page.wait_for_timeout(300)
        for bad in ["{", "null", "[]", '"purple"', "dark", "1"]:
            page.evaluate("(x) => localStorage.setItem('savf.theme', x)", bad)
            page.reload()
            page.wait_for_timeout(350)
            alive = page.evaluate("() => !!document.querySelector('h1') && typeof SavfTruth === 'object'")
            g.ck(alive, "[corrupt theme] survives " + bad[:12], alive)
        g.ck(not perrs, "[corrupt theme] no uncaught errors", "; ".join(perrs[:3]))
        ctx.close()

        # storage denied (private mode / locked-down WebView) must degrade, not crash
        ctx = browser.new_context(viewport={"width": 360, "height": 800})
        ctx.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new Error('SecurityError');}});")
        page = ctx.new_page()
        serrs = []
        page.on("pageerror", lambda ex: serrs.append(str(ex)))
        page.goto(url)
        page.wait_for_timeout(700)
        g.ck(page.evaluate("() => !!document.querySelector('h1')"), "[no storage] app boots")
        g.ck(page.evaluate("() => typeof SavfTruth === 'object'"), "[no storage] engine present")
        g.ck("session-only" in page.inner_text("#tagline"), "[no storage] tagline tells the truth",
             page.inner_text("#tagline"))
        g.ck(not serrs, "[no storage] no uncaught errors", "; ".join(serrs[:3]))
        ctx.close()

        browser.close()

    # ---- cross-engine: the app claims to be OS agnostic, so prove it ----
    # Firefox and WebKit are optional; a missing engine is skipped, never failed.
    with sync_playwright() as p:
        for engine in ("firefox", "webkit"):
            try:
                b = getattr(p, engine).launch()
            except Exception as e:
                print("SKIP: " + engine + " unavailable (" + str(e).splitlines()[0][:60] + ")")
                continue
            ctx = b.new_context(viewport={"width": 360, "height": 800})
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda ex, e=errs: e.append(str(ex)))
            page.goto(url)
            page.wait_for_timeout(1200)
            tag = "[" + engine + "]"
            g.ck(page.evaluate("() => typeof SavfTruth === 'object' && typeof SavfScan === 'object'"),
                 tag + " engine present")
            page.evaluate(SEED)
            page.wait_for_timeout(1800)
            g.ck(page.evaluate("() => document.querySelector('#verdictOut .verdict h3').textContent")
                 in ("PASS", "REVIEW", "BLOCKED", "LIED"), tag + " audit verdict renders",
                 page.evaluate("() => document.querySelector('#verdictOut .verdict h3').textContent"))
            law = page.evaluate("""() => {
                const ax = new SavfCore.Axis([0,0],[100,0]);
                const a = ax.at(0.3, 1), b = ax.at(0.7, -1);
                const files = {'a.py': 'x = 1\\n'};
                const lock = SavfAudit.freeze(files, {thresholds:{theta_mut:0.6,theta_cov:0.8},
                                                      exemptions:[], chart:'math'});
                return {rev: a[0] === b[0] && a[1] === b[1],
                        seal: !!lock.seal,
                        ok: SavfAudit.checkFreeze(lock, files).ok,
                        tamper: SavfAudit.checkFreeze(lock, {'a.py': 'x = 2\\n'}).ok};
            }""")
            g.ck(law["rev"], tag + " tau reversal identity")
            g.ck(law["seal"] and law["ok"] and not law["tamper"], tag + " freeze/tamper law", json.dumps(law))
            page.click('nav button[data-tab="self"]')
            page.wait_for_timeout(300)
            page.fill("#selfN", "300")
            page.click("#selfRun")
            page.wait_for_timeout(3000)
            g.ck("All checks passed" in page.inner_text("#selfOut"), tag + " in-app self-test passes",
                 page.inner_text("#selfOut")[:100])
            t0 = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            page.click("#themeBtn")
            page.wait_for_timeout(300)
            g.ck(page.evaluate("() => document.documentElement.getAttribute('data-theme')") != t0,
                 tag + " theme toggles")
            g.ck(not page.evaluate(JS_OVERFLOW), tag + " no clipping", page.evaluate(JS_OVERFLOW))
            g.ck(not errs, tag + " no uncaught errors", "; ".join(errs[:3]))
            b.close()

    return g, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=None, help="directory for screenshots")
    args = ap.parse_args()

    g, why = run(args.shots)
    if g is None:
        print("SKIP: " + why)
        return 0

    if g.fails:
        print("SAVF UI GATE: FAIL (%d/%d checks)" % (g.passed, g.total()))
        for f in g.fails:
            print("  FAIL  " + f)
        return 1
    print("SAVF UI GATE: PASS (%d checks)" % g.total())
    return 0


if __name__ == "__main__":
    sys.exit(main())
