#!/usr/bin/env python3
"""doc_path_gate.py — fail if a governance doc cites a repo path that does not exist.

The "disconnecting fragment" defect (SPI-23): AGENTS.md / DARKITH.md / RESUME.md name
files and directories, and when the tree moves the doc keeps naming the old paths. A
reader (or the next session) is then told to run something that is not there. Prose
cannot be gated, but a backticked repo path can: extract every one and require it to
resolve against the tracked tree.

A path resolves when it is tracked, or when a tracked file ends with it (so a
package-relative citation like `core/CssLite.kt` resolves against
`app/src/main/java/com/darkith/transliaison/core/CssLite.kt`), or when it is a known
generated/external artifact (the allowlist below). Anything else is a deficit.

Usage:
  python3 tools/doc_path_gate.py [root]
Exit: 0 = every cited path resolves; 1 = at least one does not.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

DEFAULT_DOCS = ["README.md", "AGENTS.md", "DARKITH.md", "RESUME.md"]

# Cited names that are legitimately NOT tracked: external jars fetched at build time,
# generated delivery output, and doc names DARKITH.md explicitly records as consolidated
# into itself (cited only as history).
ALLOWLIST = {
    "dist/", "dist/index.html",
    "VERSION.md", "RECONCILIATION.md", "DEFICIT_LEDGER.md", "singularity_progressive_continuum.md",
    "delivery/", "delivery/dl/", "requirements-dev.txt", "dl/",
    ".gradle/caches/", ".tools/", ".openhands/", "TASKS.json", "darkith_omega_source.zip",
    # savf runtime state (contract lock + HMAC manifest written into the CWD, gitignored)
    ".savf/",
    "dist/SHA256SUMS.txt", "dist/Darkith-2.1.0-omega.apk", "dist/_meta.json", "dist/index.html",
    # generated/orphan artifacts cited in delivery records (regenerable, never committed)
    "delivery/c7_patched_sources.zip", "delivery/darkith-one-shot.sh", "tree_omega/", "lib/",
    # build output named in prose (produced inside the APK by the chain, never a repo path)
    "classes.dex", "base.apk", "aligned.apk", "app-signed.apk",
    # generated mirror written beside a session board by tools/praxis_propagate.py
    "PRAXIS.md",
    # The Operator's research corpus. These documents sit BESIDE the repo on the home tree
    # (SPI-8: the home is the SD card, not the cloud). A law may cite them by name — that is
    # the point of citing a source — but they are not repo paths and must not be required to
    # be tracked here.
    "wtf.txt", "real upliftment.txt", "nt xi.txt", "trial and error.txt",
}

# Extensions that mark a token as a file path (not prose).
_EXTS = (".kt", ".py", ".sh", ".js", ".html", ".md", ".txt", ".xml", ".yml", ".yaml",
         ".json", ".jar", ".zip", ".apk", ".dex", ".so", ".tpl")
# Tokens that are pure placeholders in usage lines, never real paths.
_SKIP = re.compile(r"[<>{}*$]|^\.\.\.$|^-")
# External or generated artifacts whose absence is never a defect: jars/apks fetched or
# produced by the build, and any absolute/home/URL path (not in the repo).
_EXT_ARTIFACT = (".jar", ".apk")


def tracked_set(root: pathlib.Path) -> set[str]:
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files"],
                             capture_output=True, text=True, check=True).stdout
        return set(out.split())
    except Exception:
        return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
                and ".git" not in p.parts}


def _normalize(tok: str) -> str:
    """Strip a trailing :line[:col] and surrounding punctuation."""
    tok = tok.strip().strip("`").rstrip(".,;:)]}")
    return re.sub(r":\d+(:\d+)?$", "", tok)


def _candidate(tok: str) -> str | None:
    """A token that could be a repo-relative path, or None if it is not one."""
    tok = _normalize(tok)
    if not tok or tok in ALLOWLIST or _SKIP.search(tok):
        return None
    if tok.startswith(("/", "~")) or "://" in tok:
        return None                                    # absolute / home / URL
    if re.match(r"^[a-z0-9.-]+\.[a-z]{2,}/", tok):
        return None                                    # a domain + path
    if tok.endswith(_EXT_ARTIFACT):
        return None                                    # fetched/built artifact
    if len(tok) <= 4 and tok.startswith("."):
        return None                                    # a bare extension
    return tok


def looks_like_path(tok: str, tops: set[str], dirs: set[str]) -> bool:
    if not tok:
        return False
    first = tok.split("/")[0]
    if tok.endswith(_EXTS) or tok.endswith("/"):
        return True
    if first in tops or first in dirs:
        return True
    return False


def cited_tokens(text: str, tops: set[str], dirs: set[str],
                 tracked: set[str] | None = None) -> set[str]:
    """Repo-path-looking tokens inside backticks. Each backticked span is split on
    whitespace so a command like `bash tools/ci.sh` still yields `tools/ci.sh`. Matching
    is line-scoped, so a stray backtick cannot pair across lines."""
    toks: set[str] = set()
    for line in text.splitlines():
        for m in re.finditer(r"`([^`\n]+)`", line):
            span = m.group(1).strip()
            # A filename may contain spaces ("real upliftment.txt"). Try the whole span
            # first, so a multi-word filename is one path and not two prose words; then
            # fall back to whitespace splitting so `bash tools/ci.sh` still yields the path.
            # Only a span that ACTUALLY exists as a path, or is allowlisted by name, may be
            # read whole. Otherwise `bash tools/restore.sh` would be taken whole and reported
            # missing. ALLOWLIST is checked on the raw span because _candidate() maps an
            # allowlisted token to None by design.
            if " " in span and (span in ALLOWLIST
                                or (tracked is not None and span in tracked)):
                toks.add(span)
                continue
            for raw in span.split():
                cand = _candidate(raw)
                if cand and looks_like_path(cand, tops, dirs):
                    toks.add(cand)
    return toks


def resolves(cand: str, tracked: set[str]) -> bool:
    if cand in ALLOWLIST:
        return True
    c = cand.rstrip("/")
    if c in tracked or c + "/" in ALLOWLIST:
        return True
    for t in tracked:
        if t == c or t.endswith("/" + c) or ("/" + t).find("/" + c + "/") >= 0:
            return True
    return False


def main(argv: list[str]) -> int:
    root = pathlib.Path(argv[1]) if len(argv) > 1 else pathlib.Path.cwd()
    tracked = tracked_set(root)
    tops = {t.split("/")[0] for t in tracked}
    dirs = set()
    for t in tracked:
        parts = t.split("/")
        for i in range(1, len(parts)):
            dirs.add("/".join(parts[:i]))

    deficits = []
    total = 0
    for doc in DEFAULT_DOCS:
        p = root / doc
        if not p.exists():
            continue
        for tok in sorted(cited_tokens(p.read_text(encoding="utf-8", errors="replace"), tops, dirs, tracked)):
            total += 1
            if not resolves(tok, tracked):
                deficits.append((doc, tok))

    if deficits:
        print(f"doc_path_gate: FAIL — {len(deficits)} cited path(s) do not resolve "
              f"(of {total} path-like tokens):")
        for doc, tok in deficits:
            print(f"  {doc}: {tok}")
        return 1
    print(f"doc_path_gate: PASS — every cited repo path resolves ({total} tokens).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
