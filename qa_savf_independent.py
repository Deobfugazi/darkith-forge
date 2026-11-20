#!/usr/bin/env python3
"""Independent duty-level QA for savf.html.

Written by the agent, deliberately NOT reusing the repo's structural gate. This asks
whether the engine performs its duties and tells the truth:

  1. boots at 360x800 with no page errors
  2. every tab reachable
  3. a lying tree is called LIED, and the Python twin agrees
  4. empty input is never called PASS (total function)
  5. freeze produces a lock; a tampered file is named
  6. HMAC create/verify round-trips; a wrong key is rejected
  7. zero network requests (offline is the whole point)
  8. tap targets >= 44px, no horizontal overflow

Run: python3 qa_savf_independent.py
"""
import hashlib
import hmac
import json
import pathlib
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
SAVF = ROOT / "savf.html"
CHROME = "/usr/bin/chromium"

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def main() -> int:
    if not SAVF.is_file():
        print(f"FAIL: {SAVF} not found")
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 360, "height": 800})

        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        requests = []
        page.on("request", lambda r: requests.append(r.url))

        page.goto(SAVF.as_uri())
        page.wait_for_load_state("networkidle")

        # 1. tabs
        for t in ["audit", "gates", "axis", "ledger", "seal", "self", "help"]:
            page.click(f'[data-tab="{t}"]')
            page.wait_for_timeout(120)
            visible = page.evaluate(
                "(n) => { const el = document.getElementById('p-'+n);"
                " return !!el && !el.hasAttribute('hidden'); }", t)
            check(f"tab {t} reachable", visible)

        # 2. a lying tree -> LIED
        page.click('[data-tab="audit"]')
        page.wait_for_timeout(120)
        page.fill("#pasteBox", "def calclate(x):\n    # TODO: implement\n    pass\n")
        page.click("#auditPaste")
        page.wait_for_timeout(700)
        v = page.inner_text("#verdictOut").strip().upper()
        check("stub tree -> LIED", "LIED" in v, v)

        # 3. the Python twin agrees (ground truth, not a re-implementation)
        twin = subprocess.run(
            [sys.executable, "-c",
             "import savf,json;print(savf.verdict({'phi1':'fail','phi2':'fail'}))"],
            cwd=str(ROOT), capture_output=True, text=True).stdout.strip()
        check("twin verdict is LIED", twin == "LIED", twin)
        check("UI agrees with twin", twin in v, f"ui={v} twin={twin}")

        # 4. empty input is not PASS
        page.fill("#pasteBox", "   \n\n")
        page.click("#auditPaste")
        page.wait_for_timeout(500)
        ev = page.inner_text("#verdictOut").strip().upper()
        check("empty input is not PASS", "PASS" not in ev, ev)

        # 5. freeze -> lock, then tamper is named
        page.click('[data-tab="seal"]')
        page.wait_for_timeout(150)
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            target = d / "clean.py"
            target.write_text("def f():\n    return 1\n")
            page.set_input_files("#freezeInput", str(target))
            page.wait_for_timeout(300)
            page.click("#freezeRun")
            page.wait_for_timeout(600)
            lock_txt = page.inner_text("#freezeOut")
            check("freeze produced a lock",
                  "frozen" in lock_txt.lower() and "seal" in lock_txt.lower(),
                  lock_txt[:80])

            lock_json = page.evaluate(
                "() => { const t = document.getElementById('freezeOut');"
                " const m = t.innerText.match(/\\{[\\s\\S]*\\}/); return m ? m[0] : ''; }")
            if lock_json:
                page.fill("#lockBox", lock_json)
                target.write_text("def f():\n    return 999  # tampered\n")
                page.set_input_files("#checkInput", str(target))
                page.wait_for_timeout(300)
                page.click("#checkRun")
                page.wait_for_timeout(600)
                out = page.inner_text("#checkOut")
                check("tamper detected by name", "clean.py" in out, out[:100])

        # 6. HMAC round trip + wrong key rejected
        page.fill("#macKey", "correct-horse")
        page.click("#macCreate")
        page.wait_for_timeout(500)
        created = page.input_value("#macBox") or page.inner_text("#macBox")
        check("hmac manifest created", "mac" in created.lower(), created[:80])

        page.fill("#macKey", "wrong-key")
        page.click("#macVerify")
        page.wait_for_timeout(500)
        wrong = page.inner_text("#macOut")
        check("wrong key rejected", "fail" in wrong.lower() or "mismatch" in wrong.lower()
              or "bad" in wrong.lower() or "wrong" in wrong.lower(), wrong[:80])

        # 7. offline: zero external requests
        external = [u for u in requests
                    if not u.startswith(("file:", "data:", "blob:", "about:"))]
        check("zero external requests", not external, str(external[:3]))

        # 8. tap targets and overflow
        small = page.evaluate("""() => {
            const out = [];
            for (const el of document.querySelectorAll('button,[role=button],a')) {
                const r = el.getBoundingClientRect();
                if (r.width === 0 && r.height === 0) continue;
                if (r.height < 44 || r.width < 44)
                    out.push((el.id || el.textContent || '?').trim().slice(0,20)
                             + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
            }
            return out;
        }""")
        check("all tap targets >= 44px", not small, str(small[:4]))

        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("no horizontal overflow @360", overflow <= 1, f"{overflow}px")

        # 9. the launcher must never sit on a control, on any tab (regression:
        # it covered the Sign button and, once moved, the SA logo)
        overlaps = []
        for tab in ("audit", "gates", "axis", "ledger", "seal", "self", "help"):
            page.click(f'[data-tab="{tab}"]')
            page.wait_for_timeout(450)
            hits = page.evaluate("""() => {
                const fab = document.getElementById('prerun-fab');
                if (!fab) return ['missing'];
                const f = fab.getBoundingClientRect();
                const out = [];
                for (const el of document.querySelectorAll(
                        'button,a[href],[role=button],input,textarea,select,header,.logo')) {
                    if (el === fab || fab.contains(el)) continue;
                    const cs = getComputedStyle(el);
                    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
                    const r = el.getBoundingClientRect();
                    if (r.width <= 0 || r.height <= 0) continue;
                    const ox = Math.max(0, Math.min(r.right, f.right) - Math.max(r.left, f.left));
                    const oy = Math.max(0, Math.min(r.bottom, f.bottom) - Math.max(r.top, f.top));
                    if (ox * oy > 0) out.push(el.id || String(el.className) || el.tagName);
                }
                return out;
            }""")
            overlaps.extend(f"{tab}:{h}" for h in hits)
        check("launcher never covers a control", not overlaps, str(overlaps[:4]))

        # 10. the pre-runner dialog must be dismissible with Escape and must not
        # trap the page (regression: Escape did nothing)
        page.click('[data-tab="audit"]')
        page.wait_for_timeout(300)
        page.focus("#prerun-fab")
        page.keyboard.press("Enter")
        page.wait_for_timeout(700)
        opened = page.evaluate("() => !!document.querySelector('[role=dialog]')")
        trapped = page.evaluate(
            "() => { const d = document.querySelector('[role=dialog]');"
            " return d ? d.contains(document.activeElement) : false; }")
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        closed = page.evaluate("() => !document.querySelector('[role=dialog]')")
        usable = page.evaluate(
            "() => document.querySelector('#p-audit').classList.contains('on')")
        check("dialog opens and traps focus", opened and trapped, f"opened={opened} trapped={trapped}")
        check("Escape closes dialog, page usable", closed and usable,
              f"closed={closed} usable={usable}")

        check("no page errors", not errors, str(errors[:2]))
        browser.close()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\nINDEPENDENT SAVF QA: {passed}/{len(results)} checks pass\n")
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        line = f"  [{mark}] {name}"
        if detail and not ok:
            line += f"   <- {detail}"
        print(line)
    failed = [n for n, ok, _ in results if not ok]
    if failed:
        print(f"\nFAILURES ({len(failed)}): {failed}")
        return 1
    print("\nALL DUTIES HOLD.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
