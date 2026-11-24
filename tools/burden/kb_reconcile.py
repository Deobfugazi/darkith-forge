#!/usr/bin/env python3
"""kb_reconcile.py — reconcile docs/kb_manifest.json against the bytes on disk.

The audit's charge: "Nor have I completed a line-by-line reconciliation of every one
of the 78 manifest entries in this delivery. I will not call that completed research."
This gate makes that check permanent and repeatable instead of a promise.

Exit 0 = all entries match (or are declared as known drift in the allowlist).
Exit 1 = at least one undeclared missing or drifted entry.
Exit 3 = manifest absent (a skip, and a skip is never a pass, SPI-31).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

MANIFEST = pathlib.Path("docs/kb_manifest.json")
# Paths whose drift is a declared, tracked defect. Empty means zero tolerance.
ALLOWLIST = pathlib.Path("proof/kb-reconcile-allowlist.json")


def load_allowlist() -> set[str]:
    if ALLOWLIST.exists():
        return set(json.loads(ALLOWLIST.read_text()).get("allow", []))
    return set()


def main() -> int:
    if not MANIFEST.exists():
        print("KB_RECONCILE: SKIP manifest_absent (a skip is never a pass, SPI-31)")
        return 3

    doc = json.loads(MANIFEST.read_text())
    files = doc.get("files", [])
    allow = load_allowlist()

    matched, missing, drifted = [], [], []
    for e in files:
        p = pathlib.Path(e["path"])
        if not p.exists():
            missing.append(e["path"])
            continue
        b = p.read_bytes()
        if hashlib.sha256(b).hexdigest() == e["sha256"] and len(b) == e["bytes"]:
            matched.append(e["path"])
        else:
            drifted.append({"path": e["path"], "bytes_on_disk": len(b),
                            "bytes_declared": e["bytes"],
                            "delta": len(b) - e["bytes"]})

    undeclared = [d for d in drifted if d["path"] not in allow]
    undeclared_missing = [m for m in missing if m not in allow]

    print("=" * 78)
    print("KB MANIFEST RECONCILIATION — every entry against the bytes on disk")
    print("=" * 78)
    print(f"declared count : {doc.get('count')}")
    print(f"entries listed : {len(files)}")
    print(f"registers      : {len(doc.get('registers', {}))}")
    print(f"\nMATCHED  : {len(matched)}/{len(files)}")
    print(f"MISSING  : {len(missing)}  (undeclared {len(undeclared_missing)})")
    print(f"DRIFTED  : {len(drifted)}  (undeclared {len(undeclared)})")

    if drifted:
        print("\n-- DRIFT detail " + "-" * 60)
        for d in drifted:
            tag = "DECLARED" if d["path"] in allow else "UNDECLARED"
            print(f"  [{tag}] {d['path']}")
            print(f"      disk={d['bytes_on_disk']} declared={d['bytes_declared']} "
                  f"delta={d['delta']:+d}")

    ok = not undeclared and not undeclared_missing
    print("\n" + "=" * 78)
    print(f"VERDICT: {'RECONCILED' if ok else 'RECONCILIATION_INCOMPLETE'}")
    print("=" * 78)

    out = pathlib.Path("proof/kb-reconcile.json")
    out.parent.mkdir(exist_ok=True)
    receipt = json.dumps({
        "declared_count": doc.get("count"),
        "entries": len(files),
        "registers": len(doc.get("registers", {})),
        "matched": matched, "missing": missing, "drifted": drifted,
        "undeclared_drift": [d["path"] for d in undeclared],
        "undeclared_missing": undeclared_missing,
        "verdict": "RECONCILED" if ok else "RECONCILIATION_INCOMPLETE",
    }, indent=2, sort_keys=True)
    # Write only on change. This runs inside `bash tools/ci.sh`, whose whole contract is that
    # checking a clean tree leaves it clean. Rewriting an identical receipt made every CI run
    # mutate a tracked file, so the revitalization seal chased CI's own output and I9 could
    # never agree with itself.
    if not out.is_file() or out.read_text(encoding="utf-8") != receipt:
        out.write_text(receipt, encoding="utf-8")
    # NEVER #11 permits a basename at two tracked paths only while the copies are
    # byte-identical, and ci.sh fails the moment they drift. The docs/ copy is the mirror the
    # rest of the tree reads, so the producer that owns the bytes must also keep its mirror
    # in step. Leaving that to a human is how the pair diverged in the first place.
    mirror = pathlib.Path("docs/kb-reconcile.json")
    if mirror.parent.is_dir() and (not mirror.is_file()
                                   or mirror.read_text(encoding="utf-8") != receipt):
        mirror.write_text(receipt, encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
