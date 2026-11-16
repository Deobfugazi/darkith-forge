#!/usr/bin/env python3
"""Package the project into download zips and a download page.

Two archives are produced:

  darkith-forge-delivery.zip   the whole project (webapps, engine, build
                               scripts, harness, APKs, docs)
  darkith-webapp.zip           just the two zero-dependency offline apps,
                               for a phone on a thin data plan

Both land in delivery/dl/, and delivery/dl/index.html lists them with sizes
and sha256 so the link on the served page always matches the bytes on disk.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DELIVERY = ROOT / "delivery"
DL = DELIVERY / "dl"

# Scratch, caches and nested duplicates that should not ride along.
EXCLUDE_DIRS = {".git", "__pycache__", ".tools", ".shell-harness", "dl", "node_modules", ".openhands"}
EXCLUDE_SUFFIX = {".log", ".pyc", ".pyo"}
# Redundant archives already present as their own downloads.
EXCLUDE_FILES = {
    "darkith-forge-bundle.zip",
    "darkith-forge-repo.zip",
    "darkith_source_fixed.zip",
    "darkith_source_20261114_105324.zip",
    "savf1-bundle.zip",
}

SLIM = [
    "savf.html",
    "darkith forge.html",
    "savf.py",
    "delivery/README.txt",
]


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(base: pathlib.Path):
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(base)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if p.suffix in EXCLUDE_SUFFIX or p.name in EXCLUDE_FILES:
            continue
        yield p, rel


def write_zip(target: pathlib.Path, items) -> int:
    tmp = target.with_suffix(target.suffix + ".part")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path, rel in items:
            z.write(path, str(rel))
    tmp.replace(target)
    return target.stat().st_size


def main() -> int:
    DL.mkdir(parents=True, exist_ok=True)

    full = DL / "darkith-forge-delivery.zip"
    n = write_zip(full, walk(ROOT))
    print(f"  full   {full.name:<32} {full.stat().st_size:>12,} B")

    slim_items = []
    for name in SLIM:
        p = ROOT / name
        if p.is_file():
            slim_items.append((p, pathlib.Path(name).name))
    slim = DL / "darkith-webapp.zip"
    write_zip(slim, slim_items)
    print(f"  slim   {slim.name:<32} {slim.stat().st_size:>12,} B")

    rows = []
    for archive in (full, slim):
        rows.append((archive.name, archive.stat().st_size, sha256(archive)))

    page = DL / "index.html"
    page.write_text(render(rows), encoding="utf-8")
    print(f"  page   {page.relative_to(ROOT)}")
    return 0


def render(rows) -> str:
    cards = []
    for name, size, digest in rows:
        cards.append(
            f'<a class="card" href="{name}" download>'
            f'<span class="name">{name}</span>'
            f'<span class="size">{size:,} bytes</span>'
            f'<code class="hash">{digest}</code>'
            f"</a>"
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="dark light">
<title>DARKITH Forge — Download</title>
<style>
:root{{--bg:#08090c;--panel:#12151c;--line:#232836;--fg:#eef1f7;--fg2:#a8b1c4;--accent:#74a0ff}}
@media (prefers-color-scheme: light){{
:root{{--bg:#f4f6fa;--panel:#fff;--line:#d9dfea;--fg:#0f1319;--fg2:#4d566b;--accent:#2246ab}}
}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100dvh;background:var(--bg);color:var(--fg);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px 16px}}
h1{{font-size:18px;margin:0 0 4px;letter-spacing:-.2px}}
p.sub{{margin:0 0 22px;color:var(--fg2);font-size:13px;text-align:center}}
.wrap{{width:100%;max-width:640px;display:flex;flex-direction:column;gap:12px}}
.card{{display:flex;flex-direction:column;gap:6px;padding:16px;border-radius:14px;
background:var(--panel);border:1px solid var(--line);text-decoration:none;color:inherit;
transition:border-color .15s,transform .1s}}
.card:hover{{border-color:var(--accent)}}
.card:active{{transform:scale(.99)}}
.card .name{{font-weight:650;font-size:14.5px;color:var(--accent)}}
.card .size{{font-size:12.5px;color:var(--fg2)}}
.card .hash{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;
color:var(--fg2);word-break:break-all;opacity:.75}}
footer{{margin-top:22px;font-size:11.5px;color:var(--fg2);text-align:center}}
</style>
</head>
<body>
<h1>DARKITH Forge — Download</h1>
<p class="sub">Pick an archive. Every file is offline, zero-dependency, and OS-agnostic.</p>
<div class="wrap">
{chr(10).join(cards)}
</div>
<footer>sha256 printed above matches the bytes you will receive.</footer>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
