#!/usr/bin/env python3
"""Bridge contract audit: which methods the HTML UI calls vs which the Kotlin
@JavascriptInterface bridge implements.

Why this exists (W-023 / SPI-6): a single-line `grep '@JavascriptInterface fun X'`
matches NOTHING when the annotation sits on its own line, so grep silently reports
every method as missing. This tool is multiline-aware, and it also catches the
reverse drift (a health panel listing methods that are not real bridge methods).

Usage:
  python3 tools/bridge_contract_audit.py <ui.html> <Bridge.kt> [--json]
"""
import re, sys, json

def extract(html, kt):
    bridge = set(re.findall(r"@JavascriptInterface\s+fun\s+([A-Za-z0-9_]+)", kt))
    ui = set(re.findall(r"bcall\(\s*'([A-Za-z0-9_]+)'", html))
    ui |= set(re.findall(r"has\(\s*'([A-Za-z0-9_]+)'", html))
    ui |= set(re.findall(r"window\.darkith\.([A-Za-z0-9_]+)\s*\(", html))
    # the health panel's declared expectation array (last ms=[...] wins)
    dash = set()
    ms = re.findall(r"ms\s*=\s*\[([^\]]*)\]", html)
    if ms:
        dash = set(x.strip().strip("'\"") for x in ms[-1].split(",") if x.strip())
    return bridge, ui, dash

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__); sys.exit(2)
    html = open(args[0], encoding="utf-8", errors="replace").read()
    kt = open(args[1], encoding="utf-8", errors="replace").read()
    bridge, ui, dash = extract(html, kt)

    missing = sorted(ui - bridge)          # UI calls it, bridge does not expose it -> runtime error
    unused = sorted(bridge - ui)           # bridge exposes it, UI never calls it -> dead surface
    dash_phantom = sorted(dash - bridge)   # health panel shows a dot for a method that is not real
    dash_omitted = sorted(bridge - dash - {"storageGranted", "version", "browserClose"})

    report = {
        "ui_html": args[0], "bridge_kt": args[1],
        "counts": {"ui": len(ui), "bridge": len(bridge), "dashboard": len(dash)},
        "MISSING_ui_needs_bridge_lacks": missing,
        "UNUSED_bridge_has_ui_never_calls": unused,
        "DASHBOARD_phantom_dot": dash_phantom,
        "DASHBOARD_omitted_real_methods": dash_omitted,
    }
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2)); return
    print("== bridge contract audit ==")
    print(f"   UI methods called : {len(ui)}")
    print(f"   bridge methods    : {len(bridge)}")
    print(f"   dashboard ms[]    : {len(dash)}")
    print()
    print(f"MISSING (UI needs, bridge lacks) -> {missing or 'NONE  ✓ contract complete'}")
    print(f"UNUSED  (bridge has, UI never calls) -> {unused or 'NONE'}")
    print(f"DASHBOARD phantom dot (ms[] not a real method) -> {dash_phantom or 'NONE'}")
    print(f"DASHBOARD omitted (real method not shown) -> {dash_omitted or 'NONE'}")
    # --gate: a CI exit status. MISSING is a runtime error waiting to happen;
    # a phantom dashboard dot is a UI that lies. Either fails the gate.
    if "--gate" in sys.argv:
        bad = missing + dash_phantom
        if bad:
            print(f"\nGATE FAIL — {len(missing)} missing, {len(dash_phantom)} phantom")
            sys.exit(1)
        print("\nGATE PASS — contract complete, no phantom dashboard dots")
        sys.exit(0)

if __name__ == "__main__":
    main()
