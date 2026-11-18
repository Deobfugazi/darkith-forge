#!/usr/bin/env python3
"""download_gate.py — enforces MUST #16 (FORCED DOWNLOAD, DARKITH.md §22/§30).

The law: every artifact link carries `download` and is served as an attachment, so a tap
downloads the file, not opens a viewer. A hub that opens a viewer instead of saving is a
delivery the Operator cannot install.

This gate checks the whole chain, not one link in it:
  1. a hub generator exists (tools/pack_delivery.py);
  2. it emits `download` on the artifact anchors;
  3. a server exists that sets `Content-Disposition: attachment`;
  4. if a built hub exists (dist/index.html), every artifact it lists carries `download`.

Fails if any link is missing. A `download` attribute with no attachment header is not a
forced download on every client; an attachment header with no hub is not one surface.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HUB_GEN = ROOT / "tools/pack_delivery.py"
HUB = ROOT / "dist/index.html"
SERVER = ROOT / "tools/serve_hub.py"


def main() -> int:
    fails = []

    if not HUB_GEN.is_file():
        fails.append("no hub generator (tools/pack_delivery.py)")
    elif 'download>' not in HUB_GEN.read_text(encoding="utf-8"):
        fails.append("hub generator emits no `download` on artifact anchors")

    if not SERVER.is_file():
        fails.append("no server setting Content-Disposition: attachment (tools/serve_hub.py)")
    else:
        s = SERVER.read_text(encoding="utf-8")
        if "Content-Disposition" not in s or "attachment" not in s:
            fails.append("serve_hub.py does not set Content-Disposition: attachment")

    if HUB.is_file():
        html = HUB.read_text(encoding="utf-8", errors="replace")
        hrefs = re.findall(r'href="([^"]+)"', html)
        missing = [h for h in hrefs
                   if not h.startswith(("http", "#", "/"))
                   and 'download' not in html.split(f'href="{h}"', 1)[1][:120]]
        if missing:
            fails.append(f"hub artifact link(s) without `download`: {missing}")

    if fails:
        print(f"download_gate: FAIL — {len(fails)} problem(s):")
        for f in fails:
            print("  " + f)
        return 1
    print("download_gate: PASS — hub links carry `download`; server forces attachment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
