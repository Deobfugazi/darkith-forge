#!/usr/bin/env python3
"""reader_build.py — generate omega-reader.html from the indexed bytes.

The reader is one self-contained HTML file. It carries the whole readable
corpus, so it opens from a phone, a desktop, or a USB stick with no server, no
network, and no build step at read time.

Why generated: the previous omega-reader.html hardcoded eleven short sections
of prose in four "registers" and never opened the library it claimed to be a
shell for. Its footer pointed at docs/DARKITH-OMEGA-repo.txt, which it never
read. The corpus it should serve is the one tools/kb_index.py already indexes,
so this tool reads docs/kb_manifest.json — the same bytes, the same hashes — and
inlines them.

Output is deterministic: no timestamp, sorted paths, fixed gzip level. Running
it twice produces a byte-identical file (MUST #18), so `--check` can fail a
build whose reader has drifted from the corpus.

Usage:
  python3 tools/reader_build.py            # write omega-reader.html
  python3 tools/reader_build.py --check    # fail if it is stale
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "kb_manifest.json"
TEMPLATE = ROOT / "build" / "reader" / "reader_template.html"
INFLATE = ROOT / "build" / "reader" / "inflate.js"
OUT = ROOT / "omega-reader.html"

INFLATE_SLOT = "/*__INFLATE__*/"
PAYLOAD_SLOT = "__PAYLOAD_B64__"


def read_text(path: pathlib.Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", "replace")


def build() -> str:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    docs = []
    for entry in sorted(manifest["files"], key=lambda f: f["path"]):
        path = ROOT / entry["path"]
        # The reader cannot contain its own bytes: writing them changes the file,
        # which changes the hash, which changes the bytes. Skip the shell itself
        # so the build has a fixed point (the same reason kb_index excludes the
        # index from its own manifest).
        if path == OUT:
            continue
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != entry["sha256"]:
            raise SystemExit(
                f"reader_build: {entry['path']} does not match the index "
                f"(index {entry['sha256'][:12]}, file {digest[:12]}). "
                "Re-run tools/kb_index.py --write first."
            )
        docs.append({
            "p": entry["path"],
            "r": entry["register"],
            "n": len(raw),
            "h": entry["sha256"][:16],
            "t": read_text(path),
        })

    blob = json.dumps(docs, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload = base64.b64encode(gzip.compress(blob, 9, mtime=0)).decode("ascii")

    template = TEMPLATE.read_text(encoding="utf-8")
    inflate = INFLATE.read_text(encoding="utf-8")
    if INFLATE_SLOT not in template or PAYLOAD_SLOT not in template:
        raise SystemExit("reader_build: template is missing an injection slot")

    html = template.replace(INFLATE_SLOT, inflate)
    html = html.replace(PAYLOAD_SLOT, payload)
    return html


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if omega-reader.html is not the current build")
    args = ap.parse_args()

    html = build()
    if args.check:
        if not OUT.exists():
            print(f"reader_build: FAIL — {OUT.name} is missing", file=sys.stderr)
            return 1
        current = OUT.read_text(encoding="utf-8")
        if current != html:
            print(
                f"reader_build: FAIL — {OUT.name} is stale "
                f"({len(current):,} B on disk, {len(html):,} B from the corpus). "
                "Run python3 tools/reader_build.py",
                file=sys.stderr,
            )
            return 1
        print(f"reader_build: PASS — {OUT.name} matches the indexed corpus")
        return 0

    OUT.write_text(html, encoding="utf-8")
    print(f"reader_build: wrote {OUT.name} ({len(html):,} B, "
          f"{len(json.loads((ROOT / 'docs' / 'kb_manifest.json').read_text())['files'])} documents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
