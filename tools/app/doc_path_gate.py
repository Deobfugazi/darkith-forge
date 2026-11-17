#!/usr/bin/env python3
"""doc_path_gate.py — fail if a doc cites a path that does not exist.

AGENTS.md and RESUME.md drifted from the tree: they named `tree_omega/`,
`tools/fork_integrity_gate.sh`, `dist/index.html`, `hk-bridge-50` and other things
that no longer (or never did) exist. Nothing caught it, because no gate compared the
docs to the filesystem. This is that gate (the missing W-040-class detector).

It extracts every backticked token that looks like a repo path from the docs and
fails when the path is absent — with a small allowlist for paths that are
legitimately referenced but not committed (regenerable output, on-device staging,
CI-only inputs). It also checks that the bridge VERSION stated in AGENTS.md matches
the one in HomekeeperBridge.kt (the version-truth drift).

    python3 tools/app/doc_path_gate.py [--json]

Exit 0 = every cited path exists and versions agree. Non-zero = drift.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS = ["AGENTS.md", "RESUME.md", "DARKITH.md"]

# Tokens that look like a path but are deliberately not tracked here: regenerable
# output (delivery/, dist/), on-device staging (assets/engine/*), CI-only inputs, or
# platform paths. Named explicitly so an accidental new dangling path still fails.
ALLOW = {
    "delivery/", "dl/", "dist/", "build/omega/omega-ui.png", "build/omega/ui-test.png",
    "app/src/main/assets/engine/android.jar", "app/src/main/assets/engine/template.dex",
    "app/src/main/assets/engine/release_key", "app/src/main/assets/engine/release_cert",
    "assets/engine/android.jar", "assets/engine/template.dex",
    "/tmp/android.jar", "/tmp/apksig.jar", "/tmp/r8.jar",
    "$ANDROID_HOME/platforms/android-34/android.jar",
    "android-34/android.jar", "android.jar", "apksig-8.1.1.jar",
    "requirements-dev.txt",  # tracked; listed to be explicit
}

# Legitimately-cited-but-absent names, each with a reason. Anything NOT here that is
# both absent and unresolvable by basename is real drift.
ALLOW_REASONS = {
    # docs replaced by DARKITH.md -- prose names them as the superseded sources
    "RECONCILIATION.md", "VERSION.md", "DEFICIT_LEDGER.md",
    "singularity_progressive_continuum.md",
    # regenerable delivery artifacts (gitignored)
    "dist/index.html", "dist/SHA256SUMS.txt", "darkith-forged-proof.apk",
    "darkith-homekeeper-debug.apk", "darkith_omega_source.zip", "TASKS.json",
    # named in the §26 delivery record as REMOVED (dead duplicate); the citation is
    # the record of the deletion, not a live path
    "app/src/main/assets/savf.html",
    # CI-fetched toolchain jars (downloaded by tools/get_toolchain.sh, never committed)
    "android-all-14-robolectric-10818077.jar",
    # the NT-series design layer: module names in the architecture prose, not built
    # paths. They live in NT IX.txt / NT X.txt as a specification.
    "core/IRAuditor.kt", "core/CssLite.kt", "core/GpuScanner.kt", "core/IRBuilder.kt",
    "core/NativeForgeBuilder.kt", "core/OmegaActivity.kt", "core/OmegaRenderer.kt",
    "core/SubstrateIngestor.kt",
}
ALLOW |= ALLOW_REASONS

PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:sh|py|js|mjs|md|html|json|txt|kt|xml|jar|dex|apk|zip|png|tsv))`")
# Also catch repo-path references that are NOT backticked but begin with a known
# top-level directory (e.g. "tools/pack_delivery.py" in prose). These are
# unambiguous enough that a missing one is real drift, not a false positive.
BARE_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:tools|build|app|delivery|dist|core)/[A-Za-z0-9_./-]+"
    r"\.(?:sh|py|js|mjs|md|html|json|txt|kt|xml|jar|dex|apk|zip|png|tsv))")
BRIDGE_RE = re.compile(r"hk-bridge-\d+")


def main() -> int:
    problems = []
    checked = 0
    # Every file path in the tree: a doc may cite a bare filename, or a path relative
    # to a different root (e.g. `res/layout/activity_main.xml` for the real
    # `app/src/main/res/layout/activity_main.xml`). Both resolve by suffix.
    allpaths = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()]
    basenames = {p.rsplit("/", 1)[-1] for p in allpaths}
    url_re = re.compile(r"^[a-z0-9.-]+\.[a-z]{2,}/")   # dl.google.com/... -> a URL, not a repo path
    for doc in DOCS:
        p = ROOT / doc
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        toks = set(PATH_RE.findall(text)) | set(BARE_RE.findall(text))
        for tok in sorted(toks):
            if tok in ALLOW or url_re.match(tok):
                continue
            # absolute paths outside the repo are ephemeral/foreign, not drift
            if tok.startswith("/") and not (ROOT / tok.lstrip("/")).exists():
                continue
            checked += 1
            if (ROOT / tok).exists():
                continue
            if "/" not in tok and tok in basenames:
                continue
            if any(f == tok or f.endswith("/" + tok) for f in allpaths):
                continue
            problems.append(f"{doc}: cites missing path `{tok}`")

    # bridge VERSION truth: the number AGENTS.md states must equal the source.
    bridge = ROOT / "app/src/main/java/com/darkith/transliaison/HomekeeperBridge.kt"
    agents = ROOT / "AGENTS.md"
    if bridge.exists() and agents.exists():
        m = re.search(r'VERSION\s*=\s*"(hk-bridge-\d+)"', bridge.read_text(encoding="utf-8"))
        real = m.group(1) if m else None
        if real:
            stated = set(BRIDGE_RE.findall(agents.read_text(encoding="utf-8")))
            stale = sorted(s for s in stated if s != real)
            if stale:
                problems.append(f"AGENTS.md bridge VERSION drift: states {stale}, source is {real}")

    if "--json" in sys.argv:
        print(json.dumps({"checked": checked, "problems": problems}, indent=2))
        return 0 if not problems else 1

    print("== doc path gate ==")
    print(f"   {checked} path reference(s) checked across {', '.join(DOCS)}")
    if problems:
        for pr in problems:
            print("   DRIFT: " + pr)
        print(f"\nDOC-PATH GATE: FAIL — {len(problems)} drift(s)")
        return 1
    print("DOC-PATH GATE: PASS — every cited path exists; versions agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
