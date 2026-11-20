#!/usr/bin/env python3
"""Pixel-accurate WCAG contrast audit for savf.html.

For each text-bearing element the background is read from that element's own
padding ring (inset points), which is background by construction even when the
fill is a gradient. The text colour is the computed `color`. This avoids the two
false results a naive audit produces on gradients and on tight text-node boxes.

Run: python3 qa_savf_contrast.py
"""
import io
import pathlib
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
SAVF = ROOT / "savf.html"
TABS = ["audit", "gates", "axis", "ledger", "seal", "self", "help"]
SCALE = 2


def lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def main() -> int:
    fails = []
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        for theme in ("dark", "light"):
            pg = br.new_page(viewport={"width": 360, "height": 800}, device_scale_factor=SCALE)
            pg.goto(SAVF.as_uri())
            pg.wait_for_load_state("networkidle")
            pg.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
            pg.wait_for_timeout(150)

            for tab in TABS:
                pg.click(f'[data-tab="{tab}"]')
                # Let the panel finish its fade-in; capturing mid-transition reads a
                # partially painted layer and invents contrast failures.
                pg.wait_for_timeout(450)
                pg.evaluate("() => window.scrollTo(0, 0)")
                pg.wait_for_timeout(120)
                shot = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")

                items = pg.evaluate("""() => {
                    const out = [];
                    for (const el of document.querySelectorAll(
                            'p,span,dt,dd,label,button,li,h1,h2,h3,code,b,td,th,a,div')) {
                        const txt = Array.from(el.childNodes)
                            .filter(n => n.nodeType === 3)
                            .map(n => n.textContent.trim()).join("").trim();
                        if (!txt) continue;
                        const cs = getComputedStyle(el);
                        if (cs.visibility === "hidden" || cs.display === "none") continue;
                        if (parseFloat(cs.opacity) < 0.6) continue;
                        const r = el.getBoundingClientRect();
                        if (r.width < 12 || r.height < 12) continue;
                        if (r.bottom < 0 || r.top > innerHeight) continue;
                        out.push({t: txt.slice(0, 28), x: r.x, y: r.y, w: r.width, h: r.height,
                                  color: cs.color, fs: parseFloat(cs.fontSize),
                                  fw: parseInt(cs.fontWeight),
                                  radius: parseFloat(cs.borderTopLeftRadius) || 0});
                    }
                    return out;
                }""")

                for it in items:
                    fg = tuple(int(v) for v in it["color"]
                               .replace("rgba(", "").replace("rgb(", "")
                               .replace(")", "").split(",")[:3])
                    x0, y0 = it["x"] * SCALE, it["y"] * SCALE
                    x1, y1 = (it["x"] + it["w"]) * SCALE, (it["y"] + it["h"]) * SCALE
                    # Keep sample points inside the rounded corner, or the ring reads
                    # the page behind a pill/logo and reports a false failure.
                    inset = max(2, int(min(it["w"], it["h"]) * 0.18),
                                int(it.get("radius", 0)) + 1)
                    inset = min(inset, int(min(it["w"], it["h"]) / 2) - 1)
                    pts = [(x0 + inset, y0 + inset), (x1 - inset, y0 + inset),
                           (x0 + inset, y1 - inset), (x1 - inset, y1 - inset),
                           (x0 + inset, (y0 + y1) / 2), (x1 - inset, (y0 + y1) / 2)]
                    counts = {}
                    for px, py in pts:
                        ix, iy = int(px), int(py)
                        if 0 <= ix < shot.width and 0 <= iy < shot.height:
                            c = shot.getpixel((ix, iy))
                            counts[c] = counts.get(c, 0) + 1
                    if not counts:
                        continue
                    bg = max(counts.items(), key=lambda kv: kv[1])[0]
                    # A sample point may land on a glyph; if the reading equals the
                    # text colour it is unusable, so skip rather than report a lie.
                    if ratio(fg, bg) < 1.05:
                        continue
                    large = it["fs"] >= 24 or (it["fs"] >= 18.66 and it["fw"] >= 700)
                    need = 3.0 if large else 4.5
                    got = ratio(fg, bg)
                    if got < need:
                        fails.append((theme, tab, it["t"], round(got, 2), need, fg, bg))
            pg.close()
        br.close()

    print(f"\nPIXEL CONTRAST AUDIT: {len(fails)} failure(s)")
    seen = set()
    for theme, tab, txt, got, need, fg, bg in fails:
        if (theme, txt) in seen:
            continue
        seen.add((theme, txt))
        print(f"  [{theme}/{tab}] {txt!r}  {got}:1 (need {need}) fg={fg} bg={bg}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
