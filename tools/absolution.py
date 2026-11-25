#!/usr/bin/env python3
"""absolution.py — the omnivalent unblinded absolution for a self-rewriting producer.

THE DEFECT THIS REPLACES
    A gate that regenerates a tracked file on every invocation is a blind bot. It cannot
    recognize its own rewrite, cannot mark it, and has no way to decide that the rewrite is
    no longer needed and let it through. The first fix attempted for kb_reconcile.py was
    `if changed: write` — which is still blind: it compares bytes but never establishes that
    the bytes it is looking at are the ones git carries. A producer whose output is
    uncommitted rewrites forever, quietly, and every seal downstream chases it.

    That shape is extraction, not retention. NT XI:

        W_in - E = S != 0,   absolution as E/W_in -> 0

    W_in is the rewrite's whole output; E is what leaves the system without returning to the
    source — an unmarked, uncommitted rewrite is pure E. Absolution is E = 0: every byte the
    producer emits is returned to the source of truth (git) and marked as returned.

THE THREE PROPERTIES
    OMNIVALENT — it decides for every producer in a declared registry, not for one hard-coded
        file. A producer not in the registry is not absolved by silence; it is invisible, and
        the coverage check says so.
    UNBLINDED — it does not trust the producer's report or its own comparison. It executes
        each producer twice and hashes the tree before, between, and after. The evidence is
        the bytes, read from disk, not the producer's word.
    ABSOLVING — it answers the question the blind bot could not: is this rewrite still
        needed? Three answers, each with a different verdict:
            FIXED POINT + carried in git   -> ABSOLVED. The rewrite is already returned; it
                                             is a no-op and needs no further write.
            FIXED POINT + not carried      -> CARRIAGE_REQUIRED. The rewrite is correct but
                                             has left the system. It must be committed. This
                                             is not a failure of the producer; it is an
                                             unreturned surplus, and naming it is the point.
            NOT A FIXED POINT              -> UNSTABLE. Two consecutive runs disagree, so the
                                             producer has no answer to give and no rewrite can
                                             be absolved. This is the real defect.

WHAT IT REFUSES
    A producer that exits non-zero is FAIL — a producer that cannot run cannot be absolved.
    A producer that rewrites a path outside its declared outputs is FAIL — unmarked writes are
    extraction by definition. A registry entry whose command does not exist is FAIL.

THE MARK
    proof/absolution.json records, per producer, the two tree hashes, the verdict, and the
    sha256 of every path it owns. It is written only when its content changes, and it is
    written by this tool — the tool marks its own rewrite, which is exactly what the blind
    bot could not do.

Usage:
  python3 tools/absolution.py            # check: witness every producer, print the verdicts
  python3 tools/absolution.py --write    # also refresh proof/absolution.json
  python3 tools/absolution.py --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RECEIPT = ROOT / "proof" / "absolution.json"
LAW = "NT XI: W_in - E = S != 0; absolution as E/W_in -> 0"

# The registry. Each entry names a producer, the command that runs it, and the exact set of
# paths it is allowed to write. A path outside `owns` that changes during the double run is
# an unmarked write and fails the producer.
PRODUCERS = (
    {
        "name": "kb_reconcile",
        "cmd": ("python3", "tools/burden/kb_reconcile.py"),
        "owns": ("proof/kb-reconcile.json", "docs/kb-reconcile.json"),
        "why": "writes the reconciliation receipt on every invocation unless guarded",
    },
    {
        "name": "kb_index",
        "cmd": ("python3", "tools/kb_index.py", "--write"),
        "owns": ("docs/INDEX.md", "docs/kb_manifest.json"),
        "why": "regenerates the published index and its manifest",
    },
    {
        "name": "chat_gatekeeper",
        "cmd": ("python3", "tools/chat_gatekeeper.py", "--check"),
        "owns": ("TASKS.md", "proof/chat_watermark.json", "proof/chat_gatekeeper.json",
                 "proof/chat_pings.json"),
        "skip_exit_codes": (3,),
        "why": "re-ingests the Operator's orders and rewrites the board watermark",
    },
)

EXCLUDED_PARTS = {".git", ".tools", ".gradle", "node_modules", "__pycache__", ".venv"}

# This tool's own receipt records hashes of the tree. If the receipt were inside that tree,
# writing it would change the very evidence it just wrote and the repair could never be a
# fixed point — it would converge only by luck, one pass later, which is what "REPAIR DID NOT
# CONVERGE" twice in a row actually meant. The receipt is the record OF the tree, not part of
# what it records. Same reason proof/revitalization/ is excluded from the seal's snapshot.
SELF_RECEIPT = "proof/absolution.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_stamps(root: pathlib.Path = ROOT) -> dict:
    """mtime+size per path: the only evidence that a producer wrote, not just that it agrees."""
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts) or not path.is_file():
            continue
        if rel.as_posix().startswith("proof/revitalization/"):
            continue
        if rel.as_posix() == SELF_RECEIPT:
            continue
        try:
            st = path.stat()
            out[rel.as_posix()] = f"{st.st_mtime_ns}:{st.st_size}"
        except OSError:
            out[rel.as_posix()] = "UNREADABLE"
    return out


def tree_hashes(root: pathlib.Path = ROOT) -> dict:
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if not path.is_file():
            continue
        if rel.as_posix().startswith("proof/revitalization/"):
            continue  # the cycle's own receipts are written by the run that hashes them
        if rel.as_posix() == SELF_RECEIPT:
            continue  # this run's own receipt cannot be part of the tree it attests
        try:
            out[rel.as_posix()] = sha(path.read_bytes())
        except OSError:
            out[rel.as_posix()] = "UNREADABLE"
    return out


def run(cmd: tuple, root: pathlib.Path = ROOT) -> dict:
    try:
        cp = subprocess.run(list(cmd), cwd=str(root), capture_output=True, text=True)
    except OSError as exc:
        return {"exit": 127, "out": f"{type(exc).__name__}: {exc}"}
    return {"exit": cp.returncode, "out": (cp.stdout + cp.stderr).strip()}


def git_carried(rel: str, digest: str, root: pathlib.Path = ROOT) -> bool:
    """True when HEAD carries exactly these bytes at this path.

    git is the only authority on what has been returned to the source of truth. A file that
    matches on disk but differs from HEAD is a rewrite that has left the system, however
    correct it looks.
    """
    try:
        cp = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=str(root),
                            capture_output=True)
    except OSError:
        return False
    if cp.returncode != 0:
        return False
    return sha(cp.stdout) == digest


def witness(producer: dict, root: pathlib.Path = ROOT) -> dict:
    before = tree_hashes(root)
    stamps_before = tree_stamps(root)
    first = run(producer["cmd"], root)
    after_first = tree_hashes(root)
    stamps = tree_stamps(root)
    second = run(producer["cmd"], root)
    after_second = tree_hashes(root)
    stamps_after_second = tree_stamps(root)

    touched = {p for p in set(before) | set(after_first) | set(after_second)
               if before.get(p) != after_first.get(p) or after_first.get(p) != after_second.get(p)}
    owned = set(producer["owns"])
    foreign = sorted(touched - owned)
    fixed_point = after_first == after_second

    # Content is not the whole question. A producer can rewrite identical bytes, which leaves
    # the content fixed point intact while proving nothing: it cannot recognise its own rewrite
    # and cannot decide the rewrite is no longer needed. git is content-addressed and blind to
    # this, so the mtime is the only witness that a write happened at all.
    rewritten = sorted(p for p in owned
                       if (root / p).is_file() and stamps.get(p) != stamps_after_second.get(p))

    skip_codes = set(producer.get("skip_exit_codes", ()))
    if first["exit"] in skip_codes or second["exit"] in skip_codes:
        no_write = all(stamps_before.get(p) == stamps.get(p) == stamps_after_second.get(p)
                       for p in owned)
        if (first["exit"] == second["exit"]
                and first["exit"] in skip_codes
                and fixed_point and not foreign and no_write):
            verdict, why = "SKIPPED", f"producer not applicable (exit {first['exit']}): {first['out']}"
        else:
            verdict, why = "FAIL", "inconsistent or mutating skip result"
    elif first["exit"] != 0:
        verdict, why = "FAIL", f"producer exited {first['exit']}"
    elif foreign:
        verdict, why = "FAIL", "unmarked write outside declared outputs: " + ", ".join(foreign)
    elif not fixed_point:
        drift = sorted(p for p in set(after_first) | set(after_second)
                       if after_first.get(p) != after_second.get(p))
        verdict, why = "UNSTABLE", "two consecutive runs disagree at: " + ", ".join(drift)
    elif rewritten:
        verdict, why = ("REDUNDANT_REWRITE",
                        "second run rewrote identical bytes at: " + ", ".join(rewritten)
                        + " — the producer cannot decide the rewrite is no longer needed")
    else:
        uncarried = [p for p in sorted(owned)
                     if (root / p).is_file()
                     and not git_carried(p, after_second.get(p, ""), root)]
        if uncarried:
            verdict, why = ("CARRIAGE_REQUIRED",
                            "rewrite is a fixed point but has left the system: "
                            + ", ".join(uncarried))
        else:
            verdict, why = "ABSOLVED", "fixed point, and every byte it owns is carried by git"

    return {
        "producer": producer["name"],
        "verdict": verdict,
        "why": why,
        "fixed_point": fixed_point,
        "wrote": sorted(touched),
        "rewritten_unchanged": rewritten,
        "owns": sorted(owned),
        "exit": first["exit"],
        "exit_again": second["exit"],
        "first_tree_sha256": sha(json.dumps(after_first, sort_keys=True).encode()),
        "second_tree_sha256": sha(json.dumps(after_second, sort_keys=True).encode()),
        "evidence": {p: after_second.get(p) for p in sorted(owned)},
    }


def compute(root: pathlib.Path = ROOT, producers: tuple = PRODUCERS) -> dict:
    results = [witness(p, root) for p in producers]
    absolved = sum(1 for r in results if r["verdict"] == "ABSOLVED")
    skipped = sum(1 for r in results if r["verdict"] == "SKIPPED")
    active = len(results) - skipped
    extraction = active - absolved
    return {
        "law": LAW,
        "producers": len(results),
        "active": active,
        "skipped": skipped,
        "absolved": absolved,
        # E is unreturned work among applicable producers. An explicitly declared
        # environment-dependent skip is neither a defect nor an absolved producer.
        "extraction": extraction,
        "ratio": round(extraction / active, 6) if active else 0.0,
        "results": results,
    }


def render(doc: dict) -> str:
    lines = [f"absolution: {doc['absolved']}/{doc['active']} active producers absolved; "
             f"{doc['skipped']} skipped (E/W_in={doc['ratio']:.3f}, absolution at 0)"]
    for r in doc["results"]:
        lines.append(f"  {r['verdict']:<17} {r['producer']:<16} {r['why']}")
    return "\n".join(lines)


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv[1:])

    doc = compute()
    if args.write:
        payload = json.dumps(doc, indent=2, sort_keys=True) + "\n"
        if not RECEIPT.is_file() or RECEIPT.read_text(encoding="utf-8") != payload:
            RECEIPT.parent.mkdir(parents=True, exist_ok=True)
            RECEIPT.write_text(payload, encoding="utf-8")

    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    else:
        print(render(doc))

    # A fixed point that has not been carried is not this tool's failure to hide; it is a
    # named surplus awaiting the commit that returns it. It fails the gate, because a gate
    # that passes on unreturned work is the blind bot again.
    return 0 if doc["active"] > 0 and doc["absolved"] == doc["active"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
