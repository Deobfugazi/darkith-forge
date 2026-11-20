#!/usr/bin/env python3
"""Browser gate for the standalone ClearanceLoop webapp.

The engine gate (`tools/clearanceloop_gate.py`) locks the LAW. This gate locks the
DELIVERY: it drives `clearanceloop.html` in a real headless Chromium over `file://`
and asserts the app a user actually opens still works — every tab, the whole
observe -> advance -> verdict flow, waiver grant and expiry, the in-browser
self-test, keyboard control, export, persistence across a real reload, and no
horizontal clipping on a 360px phone.

Accessibility and layout are measured, not eyeballed: WCAG contrast for every text
node, 40px minimum tap targets, and clipped text, in both themes at phone and
desktop widths.

Skips (exit 0) when Playwright or Chromium is absent, so CI on a bare box does not
fail for a missing browser; run it locally before shipping UI changes.

Run:  python3 tools/clearanceloop_ui_gate.py
      python3 tools/clearanceloop_ui_gate.py --shots DIR   (also save screenshots)
"""
import argparse
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "clearanceloop.html"

CHROMIUM_CANDIDATES = [
    "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable", "/snap/bin/chromium",
]

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

JS_AUDIT = """() => {
  function parse(c) {
    const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return null;
    const p = m[1].split(',').map(Number);
    return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1};
  }
  function lum(c) {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  }
  function bgOf(el) {
    let n = el;
    while (n && n !== document.documentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0.85) return c;
      n = n.parentElement;
    }
    return parse(getComputedStyle(document.body).backgroundColor) || {r: 8, g: 9, b: 12, a: 1};
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
    const own = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
    if (own) {
      const fg = parse(cs.color), bg = bgOf(el);
      if (fg && fg.a > 0.3) {
        const cr = ratio(fg, bg), size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight, 10) >= 600;
        const need = (size >= 18.66 || (size >= 14 && bold)) ? 3 : 4.5;
        const key = cs.color + '|' + cs.fontSize + '|' + el.tagName;
        if (cr < need && !seen.has(key)) {
          seen.add(key);
          out.contrast.push({t: (el.textContent || '').trim().slice(0, 24), cr: Math.round(cr * 100) / 100, need});
        }
      }
    }
    if (/^(BUTTON|A|INPUT|SELECT|TEXTAREA)$/.test(el.tagName) && el.type !== 'file') {
      if (r.height < 40 || r.width < 40) out.small.push({tag: el.tagName, id: el.id});
    }
    if (own && cs.overflow !== 'visible' && el.scrollWidth > el.clientWidth + 1) {
      out.clipped.push({t: (el.textContent || '').trim().slice(0, 24)});
    }
  });
  return out;
}"""

SEED = """() => {
    ClearanceLoop.reset();
    const seq = [[7,4,5,3,6],[4,2,3,1,4],[2,1,2,0,3],[1,0,1,0,2],[1,1,2,1,2]];
    for (const s of seq) {
        ClearanceLoop.observe({switching:s[0], waiting:s[1], searching:s[2], correcting:s[3], review:s[4]});
        ClearanceLoop.advance();
    }
    ClearanceLoop.observe({waiting: 6});
    ClearanceLoop.advance('gate: bounded waiver');
    if (window.ClearanceLoopApp) ClearanceLoopApp.renderAll();
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
            const b = document.querySelector('nav.tabs button[data-tab="' + t + '"]');
            return !!p && p.classList.contains('active') && !!b && b.getAttribute('aria-selected') === 'true';
        }""",
        name,
    )


def cls(rep, name):
    return next(c for c in rep["classes"] if c["cls"] == name)


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
                          ("desktop 1280x900", {"width": 1280, "height": 900})]:
            ctx = browser.new_context(viewport=vp, device_scale_factor=2)
            page = ctx.new_page()
            errs = []
            page.on("console", lambda m, e=errs: e.append("console.error: " + m.text) if m.type == "error" else None)
            page.on("pageerror", lambda ex, e=errs: e.append("pageerror: " + str(ex)))
            page.goto(url)
            page.wait_for_timeout(600)

            def go(name):
                page.click('nav.tabs button[data-tab="' + name + '"]')
                page.wait_for_timeout(150)

            g.ck(not errs, "[" + label + "] clean load", "; ".join(errs[:3]))
            g.ck(page.evaluate("typeof window.ClearanceLoop === 'object'"), "[" + label + "] engine present")
            g.ck(page.evaluate("typeof window.ClearanceLoopApp === 'object'"), "[" + label + "] app shell booted")
            g.ck(not page.evaluate(JS_OVERFLOW), "[" + label + "] no clipping", page.evaluate(JS_OVERFLOW))

            for name in ["observe", "ratchet", "waivers", "report", "self", "help"]:
                go(name)
                g.ck(tab_visible(page, name), "[" + label + "] tab " + name)

            go("observe")
            page.fill("#in-switching", "7")
            page.fill("#in-waiting", "4")
            page.click("#observeSeed")
            page.wait_for_timeout(250)
            g.ck(page.is_visible("#p-ratchet"), "[" + label + "] observe jumps to ratchet")
            g.ck(page.evaluate("() => ClearanceLoop.report().verdict") in ("PASS", "WARN", "FAIL"),
                 "[" + label + "] verdict valid")
            page.click("#advanceBtn")
            page.wait_for_timeout(250)
            g.ck(page.evaluate("() => ClearanceLoop.report().delivery") >= 1, "[" + label + "] delivery advances")

            go("observe")
            page.fill("#in-switching", "1")
            page.fill("#in-waiting", "0")
            page.click("#observeSeed")
            page.wait_for_timeout(250)
            go("ratchet")
            page.click("#advanceBtn")
            page.wait_for_timeout(300)
            sw = cls(page.evaluate("() => ClearanceLoop.report()"), "switching")
            g.ck(sw["hwm"] <= 1, "[" + label + "] HWM ratchets down", json.dumps(sw))

            go("observe")
            page.fill("#in-switching", "9")
            page.click("#observeSeed")
            page.wait_for_timeout(200)
            go("ratchet")
            page.click("#advanceBtn")
            page.wait_for_timeout(300)
            g.ck(page.evaluate("() => ClearanceLoop.report().verdict") == "FAIL",
                 "[" + label + "] regression FAILs")

            page.evaluate("() => ClearanceLoop.reset()")
            go("observe")
            page.fill("#in-switching", "0")
            page.fill("#in-waiting", "3")
            page.click("#observeSeed")
            page.wait_for_timeout(200)
            go("ratchet")
            page.click("#advanceBtn")
            page.wait_for_timeout(250)
            page.fill("#advanceJustify", "gate waiver")
            page.evaluate("() => { ClearanceLoop.observe({waiting: 6}); }")
            page.click("#advanceBtn")
            page.wait_for_timeout(300)
            w = cls(page.evaluate("() => ClearanceLoop.report()"), "waiting")
            g.ck(w["waived"] is True, "[" + label + "] waiver recorded", json.dumps(w))
            g.ck(w["hwm"] == 3, "[" + label + "] waiver never raises HWM", json.dumps(w))
            g.ck(page.evaluate("() => ClearanceLoop.report().verdict") != "FAIL", "[" + label + "] waiver suppresses FAIL")

            go("waivers")
            g.ck("gate waiver" in page.inner_text("#waiverList"), "[" + label + "] waiver listed")
            g.ck(page.is_visible('[data-revoke="waiting"]'), "[" + label + "] revoke control present")
            page.click('[data-revoke="waiting"]')
            page.wait_for_timeout(350)
            rv = cls(page.evaluate("() => ClearanceLoop.report()"), "waiting")
            g.ck(rv["waived"] is False, "[" + label + "] revoke ends waiver", json.dumps(rv))
            g.ck(rv["hwm"] == 3, "[" + label + "] revoke keeps the mark")
            g.ck(page.evaluate("() => ClearanceLoop.report().verdict") == "FAIL",
                 "[" + label + "] revoked waiver FAILs again")
            g.ck("No live waivers" in page.inner_text("#waiverList"),
                 "[" + label + "] waived list empties after revoke")
            # re-grant so the expiry path below still exercises a real waiver
            page.evaluate("""() => {
                ClearanceLoop.observe({waiting: 6});
                ClearanceLoop.advance('gate waiver');
                ClearanceLoopApp.renderAll();
            }""")
            page.wait_for_timeout(250)

            page.evaluate("""() => {
                for (let i = 0; i < ClearanceLoop.WAIVER; i++) {
                    ClearanceLoop.observe({waiting: 6});
                    ClearanceLoop.advance();
                }
            }""")
            page.wait_for_timeout(250)
            rep = page.evaluate("() => ClearanceLoop.report()")
            w2 = cls(rep, "waiting")
            g.ck(w2["waived"] is False, "[" + label + "] waiver expires", json.dumps(w2))
            g.ck(rep["verdict"] == "FAIL", "[" + label + "] expiry FAILs again")
            g.ck(w2["hwm"] == 3, "[" + label + "] HWM never rose")

            go("report")
            try:
                rj = json.loads(page.inner_text("#reportOut"))
                okj = rj.get("verdict") in ("PASS", "WARN", "FAIL") and "classes" in rj
            except Exception as e:
                okj, rj = False, str(e)
            g.ck(okj, "[" + label + "] report tab is valid JSON", str(rj)[:120])

            go("self")
            page.click("#runSelf")
            page.wait_for_timeout(800)
            sp = page.inner_text("#selfPass")
            sf = page.inner_text("#selfFail")
            g.ck(sf == "0" and int(sp) >= 8, "[" + label + "] in-app self-test passes", "pass=" + sp + " fail=" + sf)

            t0 = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            page.click("#themeBtn")
            page.wait_for_timeout(200)
            t1 = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            g.ck(t0 != t1, "[" + label + "] theme toggles", str(t0) + "->" + str(t1))
            page.click("#themeBtn")
            page.wait_for_timeout(200)

            d0 = page.evaluate("() => ClearanceLoop.report().delivery")
            page.evaluate("() => document.activeElement.blur()")
            page.keyboard.press("a")
            page.wait_for_timeout(300)
            g.ck(page.evaluate("() => ClearanceLoop.report().delivery") == d0 + 1,
                 "[" + label + "] keyboard advance")
            page.keyboard.press("6")
            page.wait_for_timeout(200)
            g.ck(page.evaluate("() => document.getElementById('p-help').classList.contains('active')"),
                 "[" + label + "] keyboard tab jump")

            page.evaluate("() => window.dispatchEvent(new Event('blur'))")
            page.wait_for_timeout(150)
            g.ck(page.evaluate("() => ClearanceLoopApp.live.switching") > 0, "[" + label + "] live signals")

            dl = page.evaluate("""() => {
                let got = null;
                const proto = HTMLAnchorElement.prototype;
                const orig = proto.click;
                proto.click = function () { got = this.download; };
                document.getElementById('exportBtn').click();
                proto.click = orig;
                return got;
            }""")
            g.ck(bool(dl) and dl.endswith(".json"), "[" + label + "] export downloads .json", str(dl))
            g.ck(page.evaluate("() => !!localStorage.getItem('darkith.clearanceloop.v1')"),
                 "[" + label + "] state persisted")

            # measured accessibility + layout, both themes
            for theme in ("dark", "light"):
                page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                page.evaluate(SEED)
                for name in ["observe", "ratchet", "waivers", "report", "self", "help"]:
                    go(name)
                    r = page.evaluate(JS_AUDIT)
                    g.ck(not r["contrast"], "[" + label + "/" + theme + "/" + name + "] contrast",
                         json.dumps(r["contrast"][:3]))
                    g.ck(not r["small"], "[" + label + "/" + theme + "/" + name + "] tap targets",
                         json.dumps(r["small"][:3]))
                    g.ck(not r["clipped"], "[" + label + "/" + theme + "/" + name + "] no clipped text",
                         json.dumps(r["clipped"][:3]))

            if shots_dir:
                page.evaluate("(t) => document.documentElement.setAttribute('data-theme', 'dark')")
                page.evaluate(SEED)
                go("ratchet")
                page.screenshot(path=str(shots_dir / ("gate-" + label.replace(" ", "-") + ".png")), full_page=True)

            g.ck(not errs, "[" + label + "] no errors after full run", "; ".join(errs[:5]))
            ctx.close()

        # persistence across a real browser reload
        ctx = browser.new_context(viewport={"width": 900, "height": 800})
        page = ctx.new_page()
        page.goto(url)
        page.wait_for_timeout(500)
        page.evaluate("""() => {
            ClearanceLoop.reset();
            ClearanceLoop.observe({review: 9}); ClearanceLoop.advance();
            ClearanceLoop.observe({review: 2}); ClearanceLoop.advance();
        }""")
        before = page.evaluate("() => ClearanceLoop.report().classes.find(c => c.cls === 'review').hwm")
        page.reload()
        page.wait_for_timeout(600)
        after = page.evaluate("() => ClearanceLoop.report().classes.find(c => c.cls === 'review').hwm")
        g.ck(before == after == 2, "[reload] HWM survives reload", str(before) + "->" + str(after))
        g.ck(page.evaluate("() => ClearanceLoop.report().verdict") == "PASS", "[reload] verdict consistent")
        ctx.close()

        # a hostile stored state must never brick the app
        ctx = browser.new_context(viewport={"width": 360, "height": 800})
        page = ctx.new_page()
        perrs = []
        page.on("pageerror", lambda ex: perrs.append(str(ex)))
        page.goto(url)
        page.wait_for_timeout(300)
        for bad in ['{{{not json', 'null', '[]', '{"hwm":"x"}', '{"hwm":{"switching":"NaN"}}',
                    '{"classes":null}', '{"delivery":1e999}']:
            page.evaluate("(x) => localStorage.setItem('darkith.clearanceloop.v1', x)", bad)
            page.reload()
            page.wait_for_timeout(320)
            v = page.evaluate("() => ClearanceLoop.report().verdict")
            app = page.evaluate("() => typeof window.ClearanceLoopApp === 'object'")
            g.ck(v in ("PASS", "WARN", "FAIL") and app, "[corrupt state] survives " + bad[:24], v)
        g.ck(not perrs, "[corrupt state] no uncaught errors", "; ".join(perrs[:3]))
        ctx.close()

        # storage denied (WebView private mode) must degrade, not crash
        ctx = browser.new_context(viewport={"width": 360, "height": 800})
        ctx.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new Error('SecurityError');}});")
        page = ctx.new_page()
        serrs = []
        page.on("pageerror", lambda ex: serrs.append(str(ex)))
        page.goto(url)
        page.wait_for_timeout(700)
        g.ck(page.evaluate("typeof window.ClearanceLoopApp === 'object'"), "[no storage] app still boots")
        g.ck(page.evaluate("""() => {
            ClearanceLoop.observe({review: 5}); ClearanceLoop.advance();
            return ClearanceLoop.report().verdict;
        }""") in ("PASS", "WARN", "FAIL"), "[no storage] engine still works")
        g.ck(not serrs, "[no storage] no uncaught errors", "; ".join(serrs[:3]))
        ctx.close()

        browser.close()

    return g, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", help="directory to write screenshots into")
    args = ap.parse_args()

    if not APP.exists():
        print("clearanceloop_ui_gate: FAIL -- missing " + str(APP))
        return 1

    g, why = run(args.shots)
    if g is None:
        # Runtime absence (no browser/jsdom): exit 3 so CI reports SKIP, never PASS.
        print("clearanceloop_ui_gate: SKIP -- " + why)
        return 3

    if g.fails:
        print("clearanceloop_ui_gate: FAIL -- " + str(len(g.fails)) + "/" + str(g.total()) + " checks failed")
        for f in g.fails:
            print("  x " + f)
        return 1

    print("clearanceloop_ui_gate: PASS -- " + str(g.total()) + " browser checks "
          "(function, law, a11y, layout, persistence, hostile state, no storage)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
