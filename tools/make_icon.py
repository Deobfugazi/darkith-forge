#!/usr/bin/env python3
"""Generate the Darkith launcher icon from scratch — no downloads, no image libs.

Pure stdlib (math + zlib + struct): a tiny PNG encoder and a 4x-supersampled
rasteriser for the mark. Deterministic: no wall-clock, no randomness, so a re-run is
byte-identical (same law as pack_delivery.py).

The mark is the omega (U+03A9) — the app's own doctrine: ONE surface, the end of the
continuum — struck in gold #E8C268 on near-black #050505. Those two are the app's real
omega_accent / omega_bg (res/values/colors.xml), so the icon is of the app, not a
picture dropped next to it. Geometry is hardcoded below, not imported.

Emits (minSdk 24 needs legacy PNGs; API 26+ prefers the adaptive icon):
  res/mipmap-{mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/ic_launcher.png        (rounded square)
  res/mipmap-{...}/ic_launcher_round.png                            (circle)
  res/mipmap-anydpi-v26/ic_launcher.xml                             (adaptive)
  res/mipmap-anydpi-v26/ic_launcher_round.xml
  res/drawable/ic_launcher_foreground.xml                           (vector omega)
  res/values/ic_launcher_background.xml                             (color resource)
"""
import math
import pathlib
import struct
import sys
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "app/src/main/res"

# ── the two colours of the doctrine (res/values/colors.xml) ─────────────────────
BG = (5, 5, 5)          # omega_bg      #FF050505
GOLD = (232, 194, 104)  # omega_accent  #FFE8C268

# ── mark geometry, in a 108-unit space (adaptive icons are 108dp with a 66dp safe zone)
U = 108.0
CX, CY = 54.0, 53.0
RO = 23.0               # outer radius of the ring
TH = 9.0                # stroke thickness
RI = RO - TH
GAP = math.radians(38)  # half-angle of the opening at the bottom (the omega's mouth)
FOOT_HW = TH / 2.0

_r = math.radians(50.0)
_l = math.radians(130.0)
R_EDGE = (CX + RO * math.cos(_r), CY + RO * math.sin(_r))
L_EDGE = (CX + RO * math.cos(_l), CY + RO * math.sin(_l))
R_FOOT = (R_EDGE[0] + 12.5, 73.5)
L_FOOT = (L_EDGE[0] - 12.5, 73.5)

BORDER_INSET = 3.5      # keyline distance from the outer shape
BORDER_W = 2.0
BORDER_A = 0.32         # subtle: it defines the silhouette without shouting

DENSITIES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
SS = 4                  # supersample factor per axis


def _capsule(px, py, a, b, hw):
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    seg = vx * vx + vy * vy
    t = 0.0 if seg == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / seg))
    dx, dy = wx - t * vx, wy - t * vy
    return math.hypot(dx, dy) <= hw


def _in_ring(px, py):
    dx, dy = px - CX, py - CY
    d = math.hypot(dx, dy)
    if d < RI or d > RO:
        return False
    ang = math.atan2(dy, dx)
    diff = abs(ang - math.pi / 2.0)
    diff = min(diff, 2 * math.pi - diff)
    return diff > GAP


def _shape_sdf(px, py, round_icon):
    """Signed distance to the outer silhouette (<=0 inside)."""
    if round_icon:
        return math.hypot(px - CX, py - CY) - U / 2.0
    half, rad = U / 2.0, 24.0
    qx = abs(px - CX) - (half - rad)
    qy = abs(py - CY) - (half - rad)
    return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - rad


def render(n, round_icon):
    """Return RGBA bytes for an n*n icon."""
    scale = U / n
    out = bytearray()
    for py in range(n):
        for px in range(n):
            bg_cov = mark_cov = border_cov = 0
            for sy in range(SS):
                for sx in range(SS):
                    ux = (px + (sx + 0.5) / SS) * scale
                    uy = (py + (sy + 0.5) / SS) * scale
                    sd = _shape_sdf(ux, uy, round_icon)
                    if sd > 0:
                        continue
                    bg_cov += 1
                    if abs(sd + BORDER_INSET) <= BORDER_W / 2.0:
                        border_cov += 1
                    if _in_ring(ux, uy) or _capsule(ux, uy, R_EDGE, R_FOOT, FOOT_HW) \
                            or _capsule(ux, uy, L_EDGE, L_FOOT, FOOT_HW):
                        mark_cov += 1
            total = SS * SS
            if bg_cov == 0:
                out += bytes((0, 0, 0, 0))
                continue
            r, g, b = BG
            if border_cov:
                f = BORDER_A * (border_cov / total) / max(bg_cov / total, 1e-9)
                f = min(f, 1.0)
                r = round(r + (GOLD[0] - r) * f)
                g = round(g + (GOLD[1] - g) * f)
                b = round(b + (GOLD[2] - b) * f)
            if mark_cov:
                f = mark_cov / total
                r = round(r + (GOLD[0] - r) * f)
                g = round(g + (GOLD[1] - g) * f)
                b = round(b + (GOLD[2] - b) * f)
            a = round(255 * bg_cov / total)
            out += bytes((r, g, b, a))
    return bytes(out)


def _png(n, rgba):
    raw = bytearray()
    for y in range(n):
        raw.append(0)
        raw += rgba[y * n * 4:(y + 1) * n * 4]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def _foreground_vector():
    rx, ry = R_EDGE
    lx, ly = L_EDGE
    rf, lf = R_FOOT, L_FOOT
    d = (f"M {rx:.2f},{ry:.2f} A {RO:.2f},{RO:.2f} 0 1 0 {lx:.2f},{ly:.2f} "
         f"M {rx:.2f},{ry:.2f} L {rf[0]:.2f},{rf[1]:.2f} "
         f"M {lx:.2f},{ly:.2f} L {lf[0]:.2f},{lf[1]:.2f}")
    return f'''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <!-- the omega: ONE surface, the end of the continuum. Gold on the near-black plate. -->
    <path
        android:pathData="{d}"
        android:strokeColor="#FFE8C268"
        android:strokeWidth="{TH:.2f}"
        android:strokeLineCap="round"
        android:strokeLineJoin="round" />
</vector>
'''


def _adaptive():
    return '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
'''


def main():
    written = []
    for name, size in DENSITIES.items():
        d = RES / f"mipmap-{name}"
        d.mkdir(parents=True, exist_ok=True)
        for fname, rnd in (("ic_launcher.png", False), ("ic_launcher_round.png", True)):
            p = d / fname
            p.write_bytes(_png(size, render(size, rnd)))
            written.append(p)

    anydpi = RES / "mipmap-anydpi-v26"
    anydpi.mkdir(parents=True, exist_ok=True)
    for fname in ("ic_launcher.xml", "ic_launcher_round.xml"):
        p = anydpi / fname
        p.write_text(_adaptive(), encoding="utf-8")
        written.append(p)

    dr = RES / "drawable"
    dr.mkdir(parents=True, exist_ok=True)
    p = dr / "ic_launcher_foreground.xml"
    p.write_text(_foreground_vector(), encoding="utf-8")
    written.append(p)

    p = RES / "values/ic_launcher_background.xml"
    p.write_text('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
                 '    <color name="ic_launcher_background">#FF050505</color>\n</resources>\n',
                 encoding="utf-8")
    written.append(p)

    for p in written:
        print(f"  wrote {p.relative_to(ROOT)}  {p.stat().st_size:,} B")
    print(f"  {len(written)} file(s); mark = omega {GOLD} on {BG}")


if __name__ == "__main__":
    main()
    sys.exit(0)
