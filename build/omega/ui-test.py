#!/usr/bin/env python3
"""Headless UI test for omega.html at the target 360x800 viewport.

Loads the real file from disk (file://, offline), exercises the builtins
through actual keystrokes, checks the assistant tab, and fails on any console
error or horizontal overflow. This is the same "pre-run before delivery" gate
the other shells use.
"""
import sys, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
TARGET = ROOT / "omega.html"
SHOT = ROOT / "build" / "omega" / "omega-ui.png"

errors, results = [], []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))

with sync_playwright() as p:
    # Prefer playwright's own bundled chromium (present after
    # `playwright install chromium`, as CI does); fall back to a system
    # chromium for slim environments. The old hardcoded /usr/bin/chromium
    # does not exist on a GitHub runner, which made this test unrunnable in CI.
    try:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
    except Exception:
        browser = p.chromium.launch(executable_path="/usr/bin/chromium",
                                    args=["--no-sandbox", "--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width": 360, "height": 800},
                              device_scale_factor=2, color_scheme="dark")
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    page.goto(TARGET.as_uri())
    page.wait_for_timeout(400)

    # 1. booted without throwing
    check("boot: no console/page errors", not errors, "; ".join(errors))

    # 2. banner rendered
    out = page.inner_text("#term-out")
    check("boot: banner present", "DARKITH" in out and "offline terminal" in out, out[:120])

    def run(cmd):
        page.fill("#term-input", cmd)
        page.press("#term-input", "Enter")
        page.wait_for_timeout(220)
        return page.inner_text("#term-out")

    # 3. safe arithmetic (no eval)
    t = run("calc 12*9+3")
    check("calc: 12*9+3 == 111", "111" in t.split("calc 12*9+3")[-1], t[-80:])

    # 4. arithmetic respects precedence and parens
    t = run("calc (2+3)^2")
    check("calc: (2+3)^2 == 25", "25" in t.split("calc (2+3)^2")[-1], t[-60:])

    # 5. calc rejects code
    t = run("calc process.exit(1)")
    check("calc: refuses non-numeric input", "only numbers" in t or "unexpected" in t, t[-80:])

    # 6. real sha256 against the known digest of "hello"
    t = run("sha256 hello")
    want = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    check("sha256: matches the known digest", want in t, t[-80:])

    # 7. base64 round-trip
    t = run("b64 hello")
    check("b64: encodes hello -> aGVsbG8=", "aGVsbG8=" in t, t[-60:])

    # 8. help lists builtins
    t = run("help")
    check("help: lists builtins", "in-page builtins" in t and "calc" in t)

    # 9. caps is honest when no bridge exists
    t = run("caps")
    check("caps: reports in-page only without a bridge",
          "in-page builtins only" in t and "not installed" in t, t[-200:])

    # 10. unknown command fails loudly, never silently
    t = run("frobnicate --now")
    check("unknown: reports command not found", "command not found" in t)

    # 11. layout: no horizontal overflow at 360px
    ov = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check("layout: no horizontal overflow at 360px", ov <= 1, f"overflow={ov}px")

    # 12. interactive elements are touch-sized (>=32px tall)
    small = page.evaluate("""() => {
      const bad = [];
      document.querySelectorAll('button, .key, input, select, textarea').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.height > 0 && r.height < 30) bad.push(el.id || el.className || el.tagName);
      });
      return bad;
    }""")
    check("layout: touch targets >=30px", not small, str(small))

    # 13. dark theme is applied
    bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
    check("theme: dark background when the OS prefers dark", bg in ("rgb(5, 5, 5)", "rgba(5, 5, 5, 1)"), bg)

    # 14. assistant tab: offline ruleset computes, and is labelled as such
    page.click('.tab[data-pane="assistant"]')
    page.wait_for_timeout(150)
    page.fill("#prompt", "7*6")
    page.click("#send")
    page.wait_for_timeout(500)
    chat = page.inner_text("#chat")
    check("assistant: offline ruleset computes 7*6 = 42", "42" in chat, chat[-120:])
    check("assistant: labels itself as offline ruleset (no fake LLM)",
          "offline ruleset" in chat, chat[-200:])

    # 15. system tab renders capability + tier tables
    page.click('.tab[data-pane="system"]')
    page.wait_for_timeout(150)
    sys_txt = page.inner_text("#sys").upper()
    check("system: shows capability report", "CAPABILITIES" in sys_txt and "NATIVELIBRARYDIR" in sys_txt)
    check("system: shows model tiers with real sizes",
          "QWEN2.5 0.5B" in sys_txt and "491" in sys_txt, sys_txt[:200])

    # 15b. light scheme also renders (OS-agnostic theming)
    ctx2 = browser.new_context(viewport={"width": 360, "height": 800}, color_scheme="light")
    pg2 = ctx2.new_page()
    pg2.goto(TARGET.as_uri()); pg2.wait_for_timeout(300)
    bg2 = pg2.evaluate("getComputedStyle(document.body).backgroundColor")
    check("theme: light background when the OS prefers light",
          bg2 in ("rgb(246, 247, 249)", "rgba(246, 247, 249, 1)"), bg2)
    ctx2.close()

    # 16. accessibility: tabs use roles
    roles = page.evaluate("""() => ({
      tabs: document.querySelectorAll('[role=tab]').length,
      panels: document.querySelectorAll('[role=tabpanel]').length
    })""")
    check("a11y: tablist roles present", roles["tabs"] == 4 and roles["panels"] == 4, str(roles))

    # 17. browser tab: URL normalisation, frame wiring, honest note, persistence.
    #     We assert normalisation directly and never load a remote site, so the
    #     test stays offline (a real site refusing to be framed is expected and
    #     must not count as a defect).
    page.click('.tab[data-pane="browser"]')
    page.wait_for_timeout(150)
    norm = page.evaluate("""() => ({
      host: Omega.Browser.normalize('example.com'),
      local: Omega.Browser.normalize('localhost:8080/x'),
      query: Omega.Browser.normalize('darkith test query'),
      scheme: Omega.Browser.normalize('https://a.example/b')
    })""")
    check("browser: bare host is upgraded to https", norm["host"] == "https://example.com", norm["host"])
    check("browser: localhost gets http", norm["local"] == "http://localhost:8080/x", norm["local"])
    check("browser: non-URL input becomes a search", norm["query"].startswith("https://duckduckgo.com/?q="), norm["query"])
    check("browser: an explicit scheme is preserved", norm["scheme"] == "https://a.example/b", norm["scheme"])

    # frame wiring with an offline data: URL (no network, no CSP block)
    page.evaluate("Omega.Browser.go('data:text/html,<h1>ok</h1>')")
    page.wait_for_timeout(250)
    src = page.evaluate("document.getElementById('browser-frame').src")
    check("browser: loads the target into the frame", src.startswith("data:text/html"), src)
    check("browser: shows an honest framing note", len(page.inner_text("#browser-note")) > 10)

    # 18. settings persistence: the tab choice survives a reload
    page.click('.tab[data-pane="assistant"]')
    page.wait_for_timeout(150)
    page.reload()
    page.wait_for_timeout(500)
    sel = page.get_attribute('.tab[data-pane="assistant"]', "aria-selected")
    check("settings: last tab is restored after reload", sel == "true", str(sel))

    # back to terminal and screenshot
    page.click('.tab[data-pane="terminal"]')
    page.wait_for_timeout(150)
    page.screenshot(path=str(SHOT), full_page=False)
    browser.close()

print(f"screenshot: {SHOT}")
fails = [r for r in results if not r[1]]
for name, ok, detail in results:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f"  -- {detail}" if (detail and not ok) else ""))
if errors:
    print("\nconsole errors:")
    for e in errors:
        print("  " + e)
print(f"\nOMEGA-UI: {'PASS' if not fails and not errors else 'FAIL'} ({len(results)-len(fails)}/{len(results)})")
sys.exit(0 if (not fails and not errors) else 1)
