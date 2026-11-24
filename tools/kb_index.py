#!/usr/bin/env python3
"""kb_index.py — the universal index of the readable knowledge-skill base, generated from bytes.

Why this exists: the repo's own laws already forbid duplication and require an addressable
index — NEVER #11 (One Tree), NEVER #15 (One Surface), NEVER #16 (One Document), §22
(deduplication + idempotent packaging, MUST #18), MUST #21 (Coordinate Index). But the
apparatus covered only the Kotlin tree (`tools/tree_index.py`) and four hardcoded doc names
(`tools/consolidate_docs.sh`). The human-readable corpus had no index and no gate saw the
real duplicates, so docs accumulated "all over the place" and the reader could not tell where
anything belonged.

This tool derives the structure from the repo's own invariant — the four conditions A∧B∧C∧D
the Operator's blueprint defines for "repository":

  A  authoritative, organized holding environment   -> the repo
  B  apparatus separated from raw content           -> governance is not mixed with the corpus
  C  preservation + retrieval + boundary            -> this index is the retrieval surface
  D  server-of-record, not a derived copy           -> one canonical copy; copies are generated

applied to the filesystem, that yields four registers:

  A-apparatus   root governance, machine+human read   AGENTS.md DARKITH.md RESUME.md TASKS.md DEFICITS.json
  B-knowledge   the human-readable corpus             docs/**
  C-skillbase   the interactive skill surfaces        root *.html (savf, omega, studio, forge, inscriber)
  D-asset       shipped runtime assets                app/src/main/assets/**
  E-evidence    machine-generated proof               proof/** except proof/revitalization/** (self-sealed serial receipts)\n\nThe generated REVITALIZATION block inside TASKS.md is excluded from its index hash; S16 seals that block separately. This prevents the board's own receipt telemetry from invalidating the knowledge index.

It emits docs/INDEX.md (the universal index a reader is pointed at) and docs/kb_manifest.json
(the machine manifest: path + register + bytes + sha256). Both are generated from the bytes,
deterministic, and carry no timestamp, so re-running is byte-identical (MUST #18).

It is also the gate (SPI-15: a law with no executable check is a note). `--check` fails if:
  - docs/INDEX.md or the manifest is stale (differs from a fresh generation);
  - a tracked readable file is not in the index (coverage);
  - two readable files share a hash and are not a declared mirror (an undeclared duplicate);
  - a declared mirror pair has drifted (NEVER #11);
  - a readable file is filed outside every register (misfiled).

Usage:
  python3 tools/kb_index.py            # check: fail if stale/duplicated/misfiled/uncovered
  python3 tools/kb_index.py --write    # regenerate docs/INDEX.md + docs/kb_manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "docs" / "INDEX.md"
MANIFEST = ROOT / "docs" / "kb_manifest.json"

# Files that ARE the index; excluded so the index never hashes itself (that would break
# idempotency: the content would change every time the index changed).
SELF = {"docs/INDEX.md", "docs/kb_manifest.json"}

# Readable registers. Governance lives at the root (apparatus, read first); the corpus
# lives under docs/ (content); the skill surfaces are the root web apps (build-coupled, so
# they cannot move without breaking ~15 build scripts — the boundary is stated, not violated).
GOVERNANCE = {"README.md", "AGENTS.md", "DARKITH.md", "RESUME.md", "TASKS.md", "DEFICITS.json"}
READABLE_EXTS = {".md", ".txt", ".html"}

# The one declared mirror: one page under two names by design (the app ships the asset; the
# repo-root copy is the browser copy). Declared here once; the gate keeps them byte-identical.
MIRRORS = [
    ("app/src/main/assets/darkith_ui.html", "darkith-inscriber.html"),
    # The homekeeper Node app ships the same reader page the root serves, so the CLI and
    # the app cannot disagree about what a record looks like.
    ("omega-reader.html", "darkith-omega-homekeeper/src/reader-shell.html"),
    # Captured resolver output, kept twice on purpose: the docs/ copy is the deliverable a
    # reader opens, the proof/ copy is the evidence record filed beside the run that made it.
    # Same bytes by construction. Declared as a mirror so a divergence still fails the gate
    # (NEVER #11) instead of being silenced by deleting one of them.
    ("docs/03-RESOLUTION-captured.txt", "proof/invariant-resolution/CAPTURED.txt"),
    ("docs/06_expected_root.txt",
     "proof/burden-uplift/E2E-REHEARSAL-2026-11-24/06_expected_root.txt"),
]

REGISTERS = [
    ("A-apparatus", "Governance — the machine+human laws (read first)"),
    ("B-knowledge", "Corpus — the human-readable knowledge base"),
    ("C-skillbase", "Skill surfaces — the interactive web apps"),
    ("D-asset", "Shipped runtime assets"),
    ("E-evidence", "Machine-generated proof"),
    ("F-config", "Build configuration — dependency manifests"),
    ("G-apparatus-portable", "Portable apparatus — the one-file toolkit that travels"),
    ("H-homekeeper-app", "Homekeeper Node app — the invariant blueprint, executable"),
]

# Build configuration: dependency manifests + the fracture-scout query manifest (both are
# hand-edited source-of-truth files that the tool reads; neither is generated).
CONFIG = {"tools/deps.txt", "tools/fractures.txt", "requirements-dev.txt"}


def tracked() -> list[str]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                         capture_output=True, text=True, check=True).stdout
    # The serial receipt chain is self-hashed and verified by revitalization.py.
    # Indexing those receipts would create a circular dependency: S16 seals the index,
    # while the index would otherwise hash S16 itself.
    return [p for p in out.split("\0")
            if p and not p.startswith("proof/revitalization/")]


def register_of(path: str) -> str | None:
    if path in GOVERNANCE:
        return "A-apparatus"
    if path.startswith("docs/"):
        return "B-knowledge"
    if "/" not in path and pathlib.PurePosixPath(path).suffix == ".html":
        return "C-skillbase"
    if path.startswith("app/src/main/assets/") or path.startswith("omega-app/src/main/assets/"):
        return "D-asset"
    if path.startswith("kit/"):
        # The portable apparatus: the single-file toolkit and its carry instructions. It is
        # neither corpus nor build config — it is the thing the Operator takes to the next
        # account, so it gets its own register rather than being filed as docs.
        return "G-apparatus-portable"
    if path.startswith("darkith-omega-homekeeper/"):
        return "H-homekeeper-app"
    if path.startswith("proof/"):
        return "E-evidence"
    if path in CONFIG:
        return "F-config"
    return None


def is_readable(path: str) -> bool:
    if path in SELF or path.startswith("proof/revitalization/"):
        return False
    if path in GOVERNANCE or path in CONFIG:
        return True
    if path.startswith(("build/", ".tools/", ".openhands/", "libs/", ".github/")):
        return False
    return pathlib.PurePosixPath(path).suffix in READABLE_EXTS


def indexed_bytes(path: str) -> bytes:
    """Return indexable source bytes, excluding the generated S16 telemetry block."""
    raw = (ROOT / path).read_bytes()
    if path != "TASKS.md":
        return raw
    text = raw.decode("utf-8", errors="replace")
    begin = "<!-- REVITALIZATION:BEGIN"
    end = "<!-- REVITALIZATION:END"
    if begin in text:
        pre, rest = text.split(begin, 1)
        if end not in rest:
            raise ValueError("TASKS.md has an unclosed REVITALIZATION block")
        _, post = rest.split(end, 1)
        text = pre + post
    return text.encode("utf-8")


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def describe(path: str) -> str:
    """One line from the file's own bytes — never guessed."""
    try:
        text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if path.endswith(".html"):
        m = re.search(r"<title>([^<]*)</title>", text, re.I)
        if m:
            return m.group(1).strip()[:70]
    if path.endswith(".json"):
        m = re.search(r'"(?:_law|_note|law|title)"\s*:\s*"([^"]+)"', text)
        if m:
            return m.group(1).strip()[:70]
    for line in text.splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        if s.startswith("#"):
            return s.lstrip("# ").strip()[:70]
        if s.startswith("//") or s.startswith("/*"):
            return s.lstrip("/* ").strip()[:70]
        return s[:70]
    return ""


def collect() -> list[dict]:
    rows = []
    for path in tracked():
        if not is_readable(path):
            continue
        p = ROOT / path
        if not p.is_file():
            continue
        content = indexed_bytes(path)
        rows.append({
            "path": path,
            "register": register_of(path) or "UNFILED",
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "desc": describe(path),
        })
    rows.sort(key=lambda r: (r["register"], r["path"]))
    return rows


def duplicates(rows: list[dict]) -> list[tuple[str, list[str]]]:
    declared = {tuple(sorted(pair)) for pair in MIRRORS}
    by_hash: dict[str, list[str]] = {}
    for r in rows:
        by_hash.setdefault(r["sha256"], []).append(r["path"])
    dups = []
    for h, paths in by_hash.items():
        if len(paths) < 2:
            continue
        if tuple(sorted(paths)) in declared:
            continue
        dups.append((h, sorted(paths)))
    return sorted(dups)


def mirror_drift() -> list[tuple[str, str]]:
    drift = []
    for a, b in MIRRORS:
        pa, pb = ROOT / a, ROOT / b
        if pa.is_file() and pb.is_file() and sha256(pa) != sha256(pb):
            drift.append((a, b))
    return drift


def render(rows: list[dict]) -> str:
    total = len(rows)
    lines = [
        "# INDEX — the universal index of the knowledge-skill base",
        "",
        "Generated by `tools/kb_index.py` from the tracked bytes. Do not hand-edit; re-run the",
        "tool. Deterministic (no timestamp, no self-hash): re-running yields byte-identical",
        "output (MUST #18). Every readable file is filed in exactly one register; a file that",
        "resolves to no register is a defect the gate fails on.",
        "",
        "The registers are the repo's own invariant (A∧B∧C∧D — see",
        "`docs/DARKITH-OMEGA-repo.txt`) applied to the filesystem: apparatus separated from",
        "content (B), one retrieval surface (C), one canonical copy (D).",
        "",
        f"**{total} readable files across {len(REGISTERS)} registers.**",
        "",
    ]
    for reg, blurb in REGISTERS:
        group = [r for r in rows if r["register"] == reg]
        if not group:
            continue
        lines += [f"## {reg} — {blurb}", "", "| file | bytes | sha256 | what it is |",
                  "|---|---|---|---|"]
        for r in group:
            d = r["desc"].replace("|", "\\|")
            lines.append(f"| `{r['path']}` | {r['bytes']:,} | `{r['sha256'][:12]}` | {d} |")
        lines.append("")
    unfiled = [r for r in rows if r["register"] == "UNFILED"]
    if unfiled:
        lines += ["## UNFILED — a defect", "",
                  "| file | bytes | sha256 |", "|---|---|---|"]
        for r in unfiled:
            lines.append(f"| `{r['path']}` | {r['bytes']:,} | `{r['sha256'][:12]}` |")
        lines.append("")
    lines += [
        "## Declared mirrors (one surface, two names — kept byte-identical)",
        "",
    ]
    for a, b in MIRRORS:
        lines.append(f"- `{a}` == `{b}`")
    lines += [
        "",
        "## The laws this index enforces",
        "",
        "- NEVER #11 (One Tree) — no two divergent live copies; a mirror must not drift.",
        "- NEVER #15 (One Surface) — one delivery surface, not a scatter of links.",
        "- NEVER #16 (One Document) — one canonical record; copies are generated.",
        "- §22 / MUST #18 — deduplication + idempotent packaging (re-run = byte-identical).",
        "- MUST #21 (Coordinate Index) — a tree you cannot enumerate is a tree you cannot account for.",
        "",
    ]
    return "\n".join(lines)


def build_manifest(rows: list[dict]) -> str:
    m = {
        "_law": "kb_index: the readable knowledge-skill base, indexed from bytes; "
                "registers A-apparatus/B-knowledge/C-skillbase/D-asset/E-evidence",
        "registers": {r: b for r, b in REGISTERS},
        "mirrors": [{"a": a, "b": b} for a, b in MIRRORS],
        "count": len(rows),
        "files": [{"path": r["path"], "register": r["register"],
                   "bytes": r["bytes"], "sha256": r["sha256"]} for r in rows],
    }
    return json.dumps(m, indent=2, sort_keys=True) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="regenerate INDEX.md + kb_manifest.json")
    a = ap.parse_args()

    rows = collect()
    index_text = render(rows)
    manifest_text = build_manifest(rows)

    if a.write:
        INDEX.parent.mkdir(parents=True, exist_ok=True)
        INDEX.write_text(index_text, encoding="utf-8")
        MANIFEST.write_text(manifest_text, encoding="utf-8")
        print(f"kb_index: wrote docs/INDEX.md + docs/kb_manifest.json ({len(rows)} readable files)")
        return 0

    fails = []
    if not INDEX.is_file():
        fails.append("docs/INDEX.md is missing (run: --write)")
    elif INDEX.read_text(encoding="utf-8") != index_text:
        fails.append("docs/INDEX.md is stale (run: --write)")
    if not MANIFEST.is_file():
        fails.append("docs/kb_manifest.json is missing (run: --write)")
    elif MANIFEST.read_text(encoding="utf-8") != manifest_text:
        fails.append("docs/kb_manifest.json is stale (run: --write)")

    for r in rows:
        if r["register"] == "UNFILED":
            fails.append(f"misfiled (no register): {r['path']}")

    for h, paths in duplicates(rows):
        fails.append(f"undeclared duplicate ({h[:12]}): {', '.join(paths)}")

    for a_, b_ in mirror_drift():
        fails.append(f"mirror drift (NEVER #11): {a_} != {b_}")

    if fails:
        print(f"kb_index: FAIL — {len(fails)} problem(s):")
        for f in fails:
            print(f"  {f}")
        return 1
    print(f"kb_index: PASS — {len(rows)} readable files, all filed, no undeclared duplicates, "
          f"index current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
