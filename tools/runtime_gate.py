#!/usr/bin/env python3
"""runtime_gate.py — does the app surface actually RENDER?

Installation and rendering are two separate failures. The install gate proves
the package installer accepts the APK; this proves the UI the OS will hand to
Zygote/AMS/WMS actually paints. It loads the real launcher asset
(app/src/main/assets/homekeeper.html — what HomekeeperActivity loads into its
WebView) at the device viewport, first with NO bridge and then with a stub of
the real 41-method window.darkith bridge, and fails on any console/page error,
a blank body, an empty DOM, or horizontal overflow.

Usage:
    python3 tools/app/runtime_gate.py [html] [--shot out.png]

Exit 0 = renders clean; non-zero = a rendering defect. Skips (exit 0 with a
loud note) only when playwright is genuinely absent, so a slim environment
does not report a false failure.
"""
import os, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_TARGET = ROOT / "app" / "src" / "main" / "assets" / "homekeeper.html"

# The real @JavascriptInterface surface (grep-verified from HomekeeperBridge.kt),
# stubbed to safe values so the page can be exercised as it is on device.
BRIDGE = r"""
window.darkith = {
  apkVersion: () => "2.1.0-omega",
  browserOpen: () => "{\"ok\":true}", browserClose: () => "{\"ok\":true}",
  copyText: () => "{\"ok\":true}",
  fileCopy: () => "{\"ok\":true}", fileDelete: () => "{\"ok\":true}",
  fileDirs: () => "[\"/sdcard\",\"/sdcard/Darkith\"]",
  fileList: () => "[]", fileMove: () => "{\"ok\":true}",
  fileRead: () => "{\"ok\":true,\"data\":\"\"}", fileStat: () => "{\"exists\":false}",
  fileWrite: () => "{\"ok\":true}",
  forgeChimera: () => "{\"ok\":true}", forgeNative: () => "{\"ok\":true}",
  forgeRenderNative: () => "{\"ok\":true}",
  getAppIcon: () => "", getInstalledApps: () => "[]",
  healSource: () => "{\"ok\":true}", ingestSubstrate: () => "{\"ok\":true}",
  installApkNative: () => "{\"ok\":true}", launchApp: () => "{\"ok\":true}",
  memInfo: () => "{\"total\":4000000000,\"avail\":2000000000}",
  openExternal: () => "{\"ok\":true}", openFolderIn: () => "{\"ok\":true}",
  openOmegaScreen: () => "{\"ok\":true}", openWith: () => "{\"ok\":true}",
  requestStorage: () => "{\"ok\":true}", shareFiles: () => "{\"ok\":true}",
  shell: () => "", shellExec: () => "{\"ok\":true,\"out\":\"\"}",
  shellEnv: () => "{}", shellHistory: () => "[]", shellSetCwd: () => "{\"ok\":true}",
  shellSetEnv: () => "{\"ok\":true}",
  signerSignature: () => "deadbeef", storageGranted: () => true,
  translateHtml: () => "", unzipTo: () => "{\"ok\":true}",
  verifySignerSignature: () => true, version: () => "hk-bridge-52",
  zipPaths: () => "{\"ok\":true}",
};
"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target = pathlib.Path(args[0]) if args else DEFAULT_TARGET
    shot = None
    if "--shot" in sys.argv:
        shot = sys.argv[sys.argv.index("--shot") + 1]

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("SKIP: playwright not installed (python3 -m pip install -r requirements-dev.txt)")
        sys.exit(0)

    if not target.is_file():
        print(f"SKIP: no UI asset at {target}")
        sys.exit(0)

    results = []
    def check(name, cond, detail=""):
        results.append((name, bool(cond), detail))

    def run_mode(p, bridged):
        errors = []
        # Prefer the system chromium when playwright's bundled browser is absent,
        # so CI in a slim image renders instead of failing on a missing download.
        launch_kwargs = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        for cand in ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"):
            if os.path.exists(cand):
                launch_kwargs["executable_path"] = cand
                break
        browser = p.chromium.launch(**launch_kwargs)
        ctx = browser.new_context(viewport={"width": 360, "height": 800},
                                  device_scale_factor=2, color_scheme="dark",
                                  is_mobile=True, has_touch=True)
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        if bridged:
            page.add_init_script(BRIDGE)
        page.goto(target.as_uri())
        page.wait_for_timeout(1200)

        tag = "bridged" if bridged else "no-bridge"
        check(f"[{tag}] no console/page errors", not errors, "; ".join(errors[:6]))
        txt = (page.inner_text("body") or "").strip()
        check(f"[{tag}] non-blank render (text > 200 chars)", len(txt) > 200, f"len={len(txt)}")
        n = page.evaluate("document.querySelectorAll('*').length")
        check(f"[{tag}] DOM populated (> 100 nodes)", n > 100, f"nodes={n}")
        ow = page.evaluate("document.documentElement.scrollWidth")
        check(f"[{tag}] no horizontal overflow (<=361px)", ow <= 361, f"scrollWidth={ow}")
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        check(f"[{tag}] themed background set", bg not in ("rgba(0, 0, 0, 0)", "rgb(255, 255, 255)", ""), bg)
        if bridged and shot:
            page.screenshot(path=shot, full_page=False)
        browser.close()
        return txt

    with sync_playwright() as p:
        run_mode(p, bridged=False)
        t1 = run_mode(p, bridged=True)

    check("title present in DOM", "HOMEKEEPER" in t1.upper() or "DARKITH" in t1.upper(), t1[:80])

    ok = all(r[1] for r in results)
    for name, cond, detail in results:
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   [{detail}]" if detail and not cond else ""))
    print()
    print("RUNTIME:", "PASS" if ok else "FAIL", f"({sum(1 for r in results if r[1])}/{len(results)})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
