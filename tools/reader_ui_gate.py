#!/usr/bin/env python3
"""Browser gate for omega-reader.html.

Run: python3 tools/reader_ui_gate.py

tools/test_omega_reader.js proves the corpus, the renderer and search with a DOM
shim. A shim cannot prove that a click actually wires up: it never runs the
listeners. This gate drives the real page in a real browser from file://, which
is how the reader ships, and asserts the interaction surface works.

It exists because a `var open` inside the sidebar click handler hoisted over the
global open() and made every document click throw "open is not a function"
while the shim tests stayed green.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "omega-reader.html"

PASSED = 0
FAILED = 0
VIEWPORTS = [("phone", 360, 800), ("desktop", 1280, 900)]


def check(name, cond, extra=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  ok   {name}")
        return
    FAILED += 1
    print(f"  FAIL {name}" + (f"  -> {extra}" if extra else ""))


def run():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        # Exit 3, never 0: a skip is not a pass (SPI-31).
        print("reader_ui_gate: SKIP — playwright not installed")
        return 3

    if not PAGE.exists():
        print(f"reader_ui_gate: FAIL — {PAGE.name} is missing")
        return 1

    url = PAGE.as_uri()
    checked = 0

    with sync_playwright() as pw:
        for engine_name in ("chromium", "firefox", "webkit"):
            engine = getattr(pw, engine_name, None)
            if engine is None:
                continue
            try:
                browser = engine.launch()
            except Exception as exc:
                print(f"  skip {engine_name}: {str(exc)[:70]}")
                continue
            checked += 1

            for label, width, height in VIEWPORTS:
                ctx = browser.new_context(viewport={"width": width, "height": height},
                                          is_mobile=width < 500, has_touch=width < 500)
                page = ctx.new_page()
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)[:120]))
                page.on("console",
                        lambda m: errors.append("console: " + m.text[:120])
                        if m.type == "error" else None)

                page.goto(url, wait_until="load", timeout=120000)
                page.wait_for_function("() => !!window.DarkithLibrary", timeout=120000)
                page.wait_for_timeout(900)

                tag = f"{engine_name}/{label}"
                n = page.evaluate("() => window.DarkithLibrary.corpus().length")
                check(f"{tag} corpus loads", n > 0, f"{n} docs")

                # Every document must open and render, not merely exist.
                paths = page.evaluate("() => window.DarkithLibrary.corpus().map(d => d.p)")
                broken = []
                for path in paths:
                    page.evaluate("p => window.DarkithLibrary.open(p)", path)
                    page.wait_for_timeout(45)
                    chars = page.evaluate(
                        "() => document.querySelector('#docbody').innerText.length")
                    if chars < 40:
                        broken.append(path)
                check(f"{tag} every document renders", not broken,
                                ", ".join(broken[:3]))

                # A real click on a sidebar button must navigate. This is the
                # assertion the shim tests cannot make.
                if width < 500:
                    page.evaluate("() => document.querySelector('#menuBtn').click()")
                    page.wait_for_timeout(350)
                probe = paths[len(paths) // 2]
                page.evaluate(
                    "p => {const b = document.querySelector(`button.doc[data-path=\"${p}\"]`);"
                    " if (b) b.click();}", probe)
                page.wait_for_timeout(350)
                landed = page.evaluate("() => window.DarkithLibrary.state.path")
                check(f"{tag} a sidebar click navigates", landed == probe,
                                f"wanted {probe}, got {landed}")

                # Search must return hits and a hit must navigate.
                page.evaluate("() => document.querySelector('#searchOpen').click()")
                page.wait_for_timeout(300)
                page.fill("#q", "engine")
                page.wait_for_timeout(700)
                hits = page.evaluate("() => document.querySelectorAll('button.res').length")
                check(f"{tag} search returns hits", hits > 0, f"{hits} hits")
                if hits:
                    page.evaluate("() => document.querySelectorAll('button.res')[0].click()")
                    page.wait_for_timeout(600)
                    body = page.evaluate(
                        "() => document.querySelector('#docbody').innerText.length")
                    check(f"{tag} a search hit navigates", body > 100, str(body))
                page.keyboard.press("Escape")
                page.wait_for_timeout(250)

                # Outline must agree with the rendered headings.
                page.evaluate("() => window.DarkithLibrary.open('README.md')")
                page.wait_for_timeout(700)
                outline = page.evaluate(
                    "() => document.querySelectorAll('#outline a, #outline button').length")
                heads = page.evaluate(
                    "() => document.querySelectorAll('#docbody h1,#docbody h2,#docbody h3').length")
                check(f"{tag} outline matches headings", outline == heads,
                                f"outline {outline} vs {heads}")

                # Theme and font controls must change something.
                theme_before = page.evaluate(
                    "() => document.documentElement.dataset.theme || ''")
                page.evaluate("() => document.querySelector('#themeBtn').click()")
                page.wait_for_timeout(300)
                theme_after = page.evaluate(
                    "() => document.documentElement.dataset.theme || ''")
                check(f"{tag} theme toggles", theme_before != theme_after,
                                f"{theme_before} -> {theme_after}")

                font_before = page.evaluate(
                    "() => getComputedStyle(document.querySelector('#docbody')).fontSize")
                page.evaluate("() => document.querySelector('#fontBtn').click()")
                page.wait_for_timeout(300)
                font_after = page.evaluate(
                    "() => getComputedStyle(document.querySelector('#docbody')).fontSize")
                check(f"{tag} font size changes", font_before != font_after,
                                f"{font_before} -> {font_after}")

                # No horizontal overflow at phone width.
                if width < 500:
                    overflow = page.evaluate(
                        "() => document.documentElement.scrollWidth - "
                        "document.documentElement.clientWidth")
                    check(f"{tag} no horizontal overflow", overflow <= 0,
                                    f"{overflow}px")

                    # Every control in the sidebar drawer must clear the 44px
                    # touch floor. Inline prose links are exempt (WCAG 2.5.8).
                    page.evaluate("() => document.querySelector('#menuBtn').click()")
                    page.wait_for_timeout(400)
                    small = page.evaluate(
                        "() => [...document.querySelectorAll('#side button')]"
                        ".filter(e => { const r = e.getBoundingClientRect();"
                        "  return r.height > 0 && r.height < 44; })"
                        ".map(e => (e.textContent || '').trim().slice(0, 20)"
                        "  + ':' + Math.round(e.getBoundingClientRect().height))")
                    check(f"{tag} sidebar targets clear 44px", not small,
                                    "; ".join(small[:3]))

                check(f"{tag} no page errors", not errors,
                                "; ".join(errors[:2]))

                ctx.close()

            browser.close()

    total = PASSED + FAILED
    if checked == 0:
        print("\nREADER UI GATE: SKIP — no browser engine could launch")
        return 3
    print(f"\nREADER UI GATE: {'PASS' if FAILED == 0 else 'FAIL'} "
          f"({total} checks, {checked} engine(s))")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
