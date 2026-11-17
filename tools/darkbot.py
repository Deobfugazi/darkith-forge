#!/usr/bin/env python3
"""darkbot.py — handcoded, provider-neutral dependency watcher.

Replaces a hosted dependency service (Dependabot et al.) with a script that belongs to
this repository. It has no vendor in it: it reads a plain manifest, asks the PUBLIC
package registry (PyPI, npm) what the latest version is, and reports or applies the
difference. It runs on any machine with Python 3 — including a phone in Termux, offline
except for the registry call itself.

Why not the hosted service: that service is welded to one code host. This is not. The
detection lives here; only the "open a pull request" step is a thin per-host adapter
(see .github/workflows/darkbot.yml), so changing code host does not touch this file.

Commands
  check                 report drift; exit 1 if any pin is behind the registry
  report                human-readable table of every dependency
  update                rewrite the manifest pins to the latest versions
  export [--out FILE]   write a pip requirements file from the manifest (pypi entries),
                        so there is ONE source of truth for versions, not two
  digest <eco> <name> <version>
                        print the registry's recorded sha256 for each artifact of a
                        release, so a download can be verified byte-for-byte
  verify <file> <sha256>
                        check a local file's sha256 against an expected digest

Manifest format (tools/deps.txt), one line per dependency:
  <ecosystem>  <name>  <pinned-version>      # ecosystems: pypi | npm

Security: this program only READS JSON metadata and (for `digest`) hashes bytes. It never
executes anything it downloads. Registries are contacted over HTTPS; the base URLs can be
overridden for a private mirror with --pypi-base / --npm-base.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools" / "deps.txt"

PYPI_BASE = "https://pypi.org"
NPM_BASE = "https://registry.npmjs.org"
TIMEOUT = 20
UA = "darkbot/1.0 (+repo:darkith-forge)"


# ── manifest ──────────────────────────────────────────────────────────────────
def load_manifest(path: pathlib.Path):
    """Return [(lineno, ecosystem, name, version)]; raises on malformed lines."""
    deps = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 3:
            raise SystemExit(f"{path}:{i}: expected '<ecosystem> <name> <version>', got: {raw!r}")
        eco, name, ver = parts
        if eco not in ("pypi", "npm"):
            raise SystemExit(f"{path}:{i}: unknown ecosystem {eco!r} (want pypi|npm)")
        deps.append((i, eco, name, ver))
    return deps


def write_manifest(path: pathlib.Path, updates: dict[str, str]) -> None:
    """Rewrite pins in place, preserving comments and layout. Key = '<eco> <name>'."""
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        body = raw.split("#", 1)[0]
        key = " ".join(body.split()[:2])
        if key in updates:
            tail = raw.split("#", 1)
            comment = ("  # " + tail[1].strip()) if len(tail) > 1 else ""
            out.append(f"{key} {updates[key]}{comment}")
        else:
            out.append(raw)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


# ── version comparison (numeric release + optional pre-release suffix) ─────────
_RE_VER = re.compile(r"^(\d+(?:\.\d+)*)(.*)$")


def parse_version(s: str):
    m = _RE_VER.match(s.strip())
    if not m:
        return ((), s)  # unparseable -> sorts as lowest, compared by raw string
    release = tuple(int(x) for x in m.group(1).split("."))
    return (release, m.group(2))


def compare_versions(a: str, b: str) -> int:
    """-1 if a<b, 0 if equal, 1 if a>b. A release outranks its own pre-release."""
    ra, pa = parse_version(a)
    rb, pb = parse_version(b)
    n = max(len(ra), len(rb))
    ra = ra + (0,) * (n - len(ra))
    rb = rb + (0,) * (n - len(rb))
    if ra != rb:
        return -1 if ra < rb else 1
    if pa == pb:
        return 0
    if pa == "":
        return 1   # a is the plain release, b is a pre-release
    if pb == "":
        return -1
    return -1 if pa < pb else 1


# ── registry clients ──────────────────────────────────────────────────────────
def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def latest_pypi(name: str, base: str = PYPI_BASE):
    """Return (latest_version, {filename: sha256}) or raise urllib.error.URLError."""
    d = _get_json(f"{base}/pypi/{name}/json")
    ver = d["info"]["version"]
    digests = {}
    for f in d.get("releases", {}).get(ver, []):
        if f.get("digests", {}).get("sha256"):
            digests[f["filename"]] = f["digests"]["sha256"]
    return ver, digests


def latest_npm(name: str, base: str = NPM_BASE):
    """Return (latest_version, {tarball: integrity}) or raise urllib.error.URLError."""
    d = _get_json(f"{base}/{name}")
    ver = d["dist-tags"]["latest"]
    dist = d.get("versions", {}).get(ver, {}).get("dist", {})
    integ = {}
    if dist.get("tarball"):
        integ[dist["tarball"]] = dist.get("integrity", dist.get("shasum", ""))
    return ver, integ


def latest(eco: str, name: str, pypi_base: str, npm_base: str):
    if eco == "pypi":
        return latest_pypi(name, pypi_base)
    return latest_npm(name, npm_base)


# ── commands ──────────────────────────────────────────────────────────────────
def cmd_report(args) -> int:
    deps = load_manifest(args.manifest)
    rows = []
    drift = 0
    for lineno, eco, name, pinned in deps:
        try:
            newest, _ = latest(eco, name, args.pypi_base, args.npm_base)
        except (urllib.error.URLError, KeyError, TimeoutError) as e:
            rows.append((eco, name, pinned, "?", f"unreachable: {e}"))
            drift += 1
            continue
        c = compare_versions(pinned, newest)
        state = {0: "current", -1: "BEHIND", 1: "ahead"}[c]
        if c < 0:
            drift += 1
        rows.append((eco, name, pinned, newest, state))

    width = max((len(f"{e} {n}") for e, n, *_ in rows), default=10)
    for eco, name, pinned, newest, state in rows:
        print(f"  {eco + ' ' + name:<{width}}  {pinned:<12} -> {newest:<12} {state}")
    print(f"\n{len(rows)} dependencies, {drift} needing attention")
    return 0 if drift == 0 else 1


def cmd_update(args) -> int:
    deps = load_manifest(args.manifest)
    updates = {}
    for lineno, eco, name, pinned in deps:
        try:
            newest, _ = latest(eco, name, args.pypi_base, args.npm_base)
        except (urllib.error.URLError, KeyError, TimeoutError) as e:
            print(f"  skip {eco} {name}: registry unreachable ({e})", file=sys.stderr)
            continue
        if compare_versions(pinned, newest) < 0:
            updates[f"{eco} {name}"] = newest
            print(f"  bump {eco} {name}: {pinned} -> {newest}")
    if not updates:
        print("  nothing to update")
        return 0
    write_manifest(args.manifest, updates)
    print(f"  wrote {args.manifest}")
    return 0


def cmd_export(args) -> int:
    """Write a pip requirements file from the pypi entries in the manifest.

    The manifest is the single source of truth; this file is generated from it, never
    hand-edited, so the two can never disagree.
    """
    deps = load_manifest(args.manifest)
    lines = [
        "# GENERATED by tools/darkbot.py export -- do not edit by hand.",
        "# Source of truth: tools/deps.txt",
        "",
    ]
    for _lineno, eco, name, ver in deps:
        if eco == "pypi":
            lines.append(f"{name}=={ver}")
    out = pathlib.Path(args.out)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote {out} ({sum(1 for _, e, *_ in deps if e == 'pypi')} pypi entries)")
    return 0


def cmd_selftest(args) -> int:
    """Offline proof that darkbot's own logic is correct. No network, no vendor."""
    fails = []

    def expect(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            fails.append(msg)

    cases = [
        ("1.0.0", "1.0.0", 0), ("1.0.0", "1.0.1", -1), ("1.0.1", "1.0.0", 1),
        ("1.0", "1.0.0", 0), ("2.0.0", "1.9.9", 1), ("1.10.0", "1.9.0", 1),
        ("1.0.0", "1.0.0rc1", 1), ("1.0.0rc1", "1.0.0", -1),
        ("1.0.0a1", "1.0.0b1", -1), ("0.0.1", "0.1.0", -1),
    ]
    for a, b, want in cases:
        got = compare_versions(a, b)
        expect(got == want, f"compare_versions({a!r}, {b!r}) == {want}")

    # manifest parsing: good, comment, blank, malformed
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        good = pathlib.Path(td) / "deps.txt"
        good.write_text("# c\n\npypi  foo  1.2.3  # trailing\nnpm  bar  4.5.6\n", encoding="utf-8")
        deps = load_manifest(good)
        expect(len(deps) == 2, "parses 2 deps, ignoring comments/blanks")
        expect(deps[0][1:] == ("pypi", "foo", "1.2.3"), "reads pypi foo 1.2.3")
        expect(deps[1][1:] == ("npm", "bar", "4.5.6"), "reads npm bar 4.5.6")

        bad = pathlib.Path(td) / "bad.txt"
        bad.write_text("pypi foo\n", encoding="utf-8")
        try:
            load_manifest(bad)
            expect(False, "rejects a malformed line")
        except SystemExit:
            expect(True, "rejects a malformed line")

        # export round-trip: export writes exactly the pypi pins
        out = pathlib.Path(td) / "req.txt"
        cmd_export(argparse.Namespace(manifest=good, out=str(out)))
        expect(out.read_text(encoding="utf-8").splitlines()[-1] == "foo==1.2.3",
               "export writes pypi pins only")

        # update rewrites the pin in place, preserving the comment
        write_manifest(good, {"pypi foo": "9.9.9"})
        txt = good.read_text(encoding="utf-8")
        expect("pypi foo 9.9.9" in txt and "trailing" in txt,
               "update rewrites pin and keeps comment")

    print(f"\nDARKBOT: {'PASS' if not fails else 'FAIL'} "
          f"({len(cases) + 6 - len(fails)} passed, {len(fails)} failed)")
    return 0 if not fails else 1


def cmd_digest(args) -> int:
    if args.ecosystem == "pypi":
        ver, digests = latest_pypi(args.name, args.pypi_base)
        if args.version:
            # re-query the exact release's files
            d = _get_json(f"{args.pypi_base}/pypi/{args.name}/json")
            files = d.get("releases", {}).get(args.version, [])
            digests = {f["filename"]: f["digests"]["sha256"] for f in files
                       if f.get("digests", {}).get("sha256")}
            ver = args.version
    else:
        ver, digests = latest_npm(args.name, args.npm_base)
        ver = args.version or ver
    print(f"{args.ecosystem} {args.name} {ver}")
    for fname, digest in sorted(digests.items()):
        print(f"  sha256 {digest}  {fname}")
    return 0


def cmd_verify(args) -> int:
    h = hashlib.sha256()
    with open(args.file, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    got = h.hexdigest()
    ok = got.lower() == args.sha256.lower()
    print(f"{'OK  ' if ok else 'FAIL'} {args.file}\n  expected {args.sha256}\n  actual   {got}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="handcoded, provider-neutral dependency watcher")
    ap.add_argument("--manifest", type=pathlib.Path, default=MANIFEST)
    ap.add_argument("--pypi-base", default=PYPI_BASE)
    ap.add_argument("--npm-base", default=NPM_BASE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    sub.add_parser("check").set_defaults(fn=cmd_report)
    sub.add_parser("update").set_defaults(fn=cmd_update)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    e = sub.add_parser("export")
    e.add_argument("--out", default=str(ROOT / "requirements-dev.txt"))
    e.set_defaults(fn=cmd_export)
    d = sub.add_parser("digest")
    d.add_argument("ecosystem", choices=["pypi", "npm"])
    d.add_argument("name")
    d.add_argument("version", nargs="?")
    d.set_defaults(fn=cmd_digest)
    v = sub.add_parser("verify")
    v.add_argument("file")
    v.add_argument("sha256")
    v.set_defaults(fn=cmd_verify)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
