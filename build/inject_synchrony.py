#!/usr/bin/env python3
"""inject_synchrony.py — inject the generated synchrony runtime into every app surface.

Prime bylaw (MUST #23/#24): synchrony is time tracking, hardcoded and AUTO-GENERATED into
all apps. This tool is the generator's second half: it takes build/gen/omega_time.js and
places it inside every app HTML surface between stable markers, so the injection is
idempotent (re-running yields byte-identical output — MUST #18) and re-derivable.

It also stamps a live clock element into the surface's status bar so a saved document
always shows its time and date (the Operator's diachronic-sort requirement).

Run:  python3 build/inject_synchrony.py [--check]
      --check  verify every surface is current without writing (for the gate/CI)
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN_JS = ROOT / "build/gen/omega_time.js"
SURFACES = sorted((ROOT / "app/src/main/assets").glob("*.html"))

BEGIN = "<!-- BEGIN GENERATED synchrony (build/inject_synchrony.py) — DO NOT EDIT -->"
END = "<!-- END GENERATED synchrony -->"

# a clock readout: date + time, Operator-local, updated live. Uses the injected runtime.
CLOCK_HTML = (
    '<span id="omega-clock" title="Operator time (Asia/Manila, UTC+8)" '
    'style="position:fixed;right:6px;bottom:6px;z-index:2147483647;font:11px/1.2 ui-monospace,monospace;'
    'color:#E8C268;background:rgba(5,5,5,.82);border:1px solid rgba(232,194,104,.35);'
    'border-radius:6px;padding:3px 7px;pointer-events:none">--</span>'
)
CLOCK_JS = (
    "(function(){function tick(){var e=document.getElementById('omega-clock');"
    "if(e&&window.omegaTime)e.textContent=window.omegaTime.stamp();}"
    "tick();setInterval(tick,1000);})();"
)


def block() -> str:
    js = GEN_JS.read_text(encoding="utf-8")
    return f"{BEGIN}\n<script>\n{js}</script>\n<script>{CLOCK_JS}</script>\n{CLOCK_HTML}\n{END}"


def inject(html: str, payload: str) -> str:
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    if pattern.search(html):
        return pattern.sub(lambda _: payload, html, count=1)
    # first injection: right before </body> (or </html>, or appended)
    for anchor in ("</body>", "</html>"):
        i = html.rfind(anchor)
        if i != -1:
            return html[:i] + payload + "\n" + html[i:]
    return html + "\n" + payload + "\n"


def main() -> int:
    check = "--check" in sys.argv[1:]
    if not GEN_JS.is_file():
        print("inject_synchrony: FAIL — build/gen/omega_time.js missing (run build/gen_synchrony.py)")
        return 1
    if not SURFACES:
        print("inject_synchrony: FAIL — no app surfaces under app/src/main/assets/*.html")
        return 1

    payload = block()
    stale = []
    for s in SURFACES:
        original = s.read_text(encoding="utf-8")
        updated = inject(original, payload)
        if updated != original:
            stale.append(s.name)
            if not check:
                s.write_text(updated, encoding="utf-8")
    if check:
        if stale:
            print(f"inject_synchrony: FAIL — {len(stale)} surface(s) not current: {stale}")
            return 1
        print(f"inject_synchrony: PASS — {len(SURFACES)} surface(s) carry the current runtime")
        return 0
    print(f"inject_synchrony: {len(stale)} surface(s) updated; {len(SURFACES)} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
