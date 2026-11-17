#!/usr/bin/env python3
"""Sync the delivery bundle with the built artifacts and refresh its hash page.

`delivery/` is the shipping bundle: the webapp, the APKs, the zips and an
`index.html` that prints a size and a sha256 for each one.  Two things drift
there -- the copied webapp files fall behind the repo, and the numbers printed
on the page fall behind the files -- so this script fixes both:

  1. copy the built webapp (`savf.html`, `darkith forge.html`) into delivery/
  2. recompute every size and sha256 that `index.html` prints
  3. report any link whose target is missing

Run:  python3 build/sync-delivery.py [--check]
"""
import argparse
import hashlib
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DELIVERY = ROOT / "delivery"
INDEX = DELIVERY / "index.html"
# The delivery hub UI is GENERATED, never hand-authored: its structure comes from
# this tracked template and its numbers from the files in delivery/. Wipe delivery/
# and re-running this script brings the UI back byte-identical (minus the hashes).
HUB_TPL = ROOT / "build/delivery-hub.template.html"

# repo file -> name inside delivery/
COPY = {
    ROOT / "savf.html": DELIVERY / "savf.html",
    ROOT / "darkith forge.html": DELIVERY / "darkith-forge.html",
    ROOT / "omega.html": DELIVERY / "omega.html",
}

# Documents that quote a size and a sha256 for the webapp.  Kept in step with
# the files above so no shipped page contradicts the bytes beside it.
DOC_FILES = {
    "savf.html": ROOT / "savf.html",
    "savf.py": ROOT / "savf.py",
    "darkith-forge.html": ROOT / "darkith forge.html",
    "omega.html": ROOT / "omega.html",
}
DOCS = ["README.txt", "PROGRESS-LEDGER.md"]

NAME_RE = re.compile(r"<b>([\w.+-]+\.\w+)</b>")
SIZE_RE = re.compile(r"[\d,]+ bytes")
HASH_RE = re.compile(r"sha256 [0-9a-f]{8,64}")


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def refresh_block(block: str) -> str:
    """Rewrite the size and sha256 that follow each `<b>file</b>` in a meta block."""
    names = NAME_RE.findall(block)
    for name in names:
        target = DELIVERY / name
        if not target.is_file():
            continue
        size = f"{target.stat().st_size:,} bytes"
        digest = "sha256 " + sha256(target)
        start = block.index(f"<b>{name}</b>")
        nxt = NAME_RE.search(block, start + 1)
        end = nxt.start() if nxt else len(block)
        seg = block[start:end]
        seg = SIZE_RE.sub(lambda m: size, seg, count=1)
        seg = HASH_RE.sub(lambda m: digest, seg, count=1)
        block = block[:start] + seg + block[end:]
    return block


def hub_from_template() -> str:
    """Render delivery/index.html from the tracked template, ready to be refreshed.

    The template carries the real hub markup (and the real numbers as of the last
    build). Refreshing it here keeps a freshly-generated hub in sync even when the
    numbers move; the size/hash pass below then re-stamps every block."""
    return refresh_index(HUB_TPL.read_text(encoding="utf-8"))


def refresh_index(text: str) -> str:
    """Apply refresh_block to every `<div class="meta">...</div>` section."""
    out, pos = [], 0
    open_tag = '<div class="meta">'
    while True:
        i = text.find(open_tag, pos)
        if i < 0:
            out.append(text[pos:])
            break
        j = text.find("</div>", i)
        if j < 0:
            out.append(text[pos:])
            break
        out.append(text[pos:i])
        out.append(refresh_block(text[i:j]))
        pos = j
    return "".join(out)


def check_links(text: str) -> list:
    hrefs = re.findall(r'href="([^"]+)"', text)
    missing = []
    for href in sorted(set(hrefs)):
        if href.startswith(("http:", "https:", "#", "mailto:")):
            continue
        if not (DELIVERY / href).exists():
            missing.append(href)
    return missing


# Markdown table row:   | `savf.html` | 359,396 | `f4aed824c7f21081006941c2` |
TABLE_ROW = re.compile(
    r"(?P<lead>\|\s*`)(?P<name>savf\.html|savf\.py|darkith-forge\.html)"
    r"(?P<sep>`\s*\|\s*)(?P<size>[\d,]+)(?P<mid>\s*\|\s*`)"
    r"(?P<hash>[0-9a-f]+)(?P<end>`\s*\|)"
)

# A "section" is opened by a heading line that names exactly one tracked file
# (e.g. "1) THE WEBAPP  —  darkith-forge.html" or "5) savf.html  —  ...").
# The next bare "SIZE bytes   sha256 HEX" line after it belongs to that file.
HEADING = re.compile(r"^[=\-\s]*\d*\)?\s*[^\n]*?(savf\.html|savf\.py|darkith-forge\.html)\b")

# Plain text, name inline:  reference savf.py  40,583 bytes  sha256 f4aed824...(64)
PLAIN_NAMED = re.compile(
    r"(?P<lead>(?:reference\s+)?)(?P<name>savf\.html|savf\.py|darkith-forge\.html)"
    r"(?P<gap>\s+)(?P<size>[\d,]+)(?P<mid>\s+bytes\s+sha256\s+)(?P<hash>[0-9a-f]{64})"
)


def _stamp(name: str, keep: int | None = None):
    target = DOC_FILES.get(name)
    if target is None or not target.is_file():
        return None
    size = f"{target.stat().st_size:,}"
    digest = sha256(target)
    if keep is not None:
        digest = digest[:keep]
    return size, digest


# A bare "SIZE bytes   sha256 HEX" line, whole-line anchored.
BARE = re.compile(r"(?P<size>[\d,]+)(?P<mid>\s+bytes\s+sha256\s+)(?P<hash>[0-9a-f]{64})")


def refresh_docs(text: str) -> str:
    """Rewrite the size/sha256 that the docs print for the webapp files.

    Three shapes are handled, each anchored so an unrelated hash on a nearby
    line can never be rewritten: a markdown table row, a name-inline line, and
    a bare line that inherits the file named in its section heading.
    """
    def table(m: re.Match) -> str:
        st = _stamp(m.group("name"), keep=len(m.group("hash")))
        if not st:
            return m.group(0)
        return (m.group("lead") + m.group("name") + m.group("sep") + st[0]
                + m.group("mid") + st[1] + m.group("end"))

    def named(m: re.Match) -> str:
        st = _stamp(m.group("name"))
        if not st:
            return m.group(0)
        return (m.group("lead") + m.group("name") + m.group("gap") + st[0]
                + m.group("mid") + st[1])

    out, current = [], None
    for line in text.splitlines(keepends=True):
        body = line.strip()
        h = HEADING.match(body)
        if h:
            current = h.group(1)
        m = BARE.fullmatch(body)
        if m and current:
            st = _stamp(current)
            if st:
                line = st[0] + m.group("mid") + st[1] + "\n"
            # a heading owns exactly one size line; stop before the next one
            current = None
        out.append(line)

    text = "".join(out)
    text = TABLE_ROW.sub(table, text)
    text = PLAIN_NAMED.sub(named, text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report drift; write nothing")
    args = ap.parse_args()

    if args.check:
        ok = True
        if not INDEX.exists():
            print("index.html: missing (regenerate with: python3 build/sync-delivery.py)",
                  file=sys.stderr)
            ok = False
        else:
            index = INDEX.read_text(encoding="utf-8")
            if refresh_index(index) != index:
                print("index.html: printed sizes/hashes are stale", file=sys.stderr)
                ok = False
        stale = [dst.name for src, dst in COPY.items()
                 if not dst.exists() or dst.read_bytes() != src.read_bytes()]
        if stale:
            print("stale copies: " + ", ".join(stale), file=sys.stderr)
            ok = False
        for doc in DOCS:
            p = DELIVERY / doc
            if p.exists() and refresh_docs(p.read_text(encoding="utf-8")) != p.read_text(encoding="utf-8"):
                print(f"{doc}: printed sizes/hashes are stale", file=sys.stderr)
                ok = False
        missing = check_links(index if INDEX.exists() else "")
        if missing:
            print("missing links: " + ", ".join(missing), file=sys.stderr)
            ok = False
        print("delivery: " + ("in sync" if ok else "drift detected"))
        return 0 if ok else 1

    # Copy first, then hash: the printed numbers must describe the files that
    # are actually in delivery/ once this run finishes.
    for src, dst in COPY.items():
        shutil.copyfile(src, dst)
        print(f"  copied   {src.name} -> delivery/{dst.name}  ({dst.stat().st_size:,} B)")

    # Regenerate the hub from the template when it is absent or still the
    # un-stamped template (the placeholder hash), then always re-stamp numbers.
    if not INDEX.exists() or INDEX.read_bytes() == HUB_TPL.read_bytes():
        INDEX.write_text(hub_from_template(), encoding="utf-8")
        print("  index    generated from build/delivery-hub.template.html")

    index = INDEX.read_text(encoding="utf-8")
    refreshed = refresh_index(index)
    INDEX.write_text(refreshed, encoding="utf-8")
    changed = sum(1 for a, b in zip(index.splitlines(), refreshed.splitlines()) if a != b)
    print(f"  index    refreshed ({changed} line(s) updated)")

    for doc in DOCS:
        p = DELIVERY / doc
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        new = refresh_docs(text)
        if new != text:
            p.write_text(new, encoding="utf-8")
            n = sum(1 for a, b in zip(text.splitlines(), new.splitlines()) if a != b)
            print(f"  {doc:<8} refreshed ({n} line(s) updated)")

    missing = check_links(refreshed)
    if missing:
        print("  MISSING LINKS: " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
