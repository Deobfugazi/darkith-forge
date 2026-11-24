#!/usr/bin/env python3
"""receipt_chain.py — the canonical, reproducible receipt chain.

The previous rehearsal wrote receipt hashes that NO convention reproduces: the chain
failed on its own landed bytes (CHAIN_BROKEN_AT 1). That is worse than no chain, because
it looks like evidence. This module is the single writer/verifier, and it uses the same
canonical form as tools/mint_ledger.py so the repo has ONE chain convention, not two.

Canonical form (identical to mint_ledger._canonical):
    sha256( json.dumps(body_without_hash, sort_keys=True, separators=(",", ":")) )

The link rule:
    entry["prev"]   = previous entry's "hash", or "GENESIS" for the first
    entry["hash"]   = sha256(canonical(entry with prev, without hash))

Note the ordering: `prev` is INSIDE the hashed body. A chain that hashes the body and
then attaches prev outside it can be re-linked freely, which is the defect this closes.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

GENESIS = "GENESIS"


def canonical(entry: dict) -> bytes:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def digest(entry: dict) -> str:
    return hashlib.sha256(canonical(entry)).hexdigest()


def seal(entry: dict, prev: str) -> dict:
    """Return the entry with prev and hash filled in, hash covering prev."""
    out = dict(entry)
    out.pop("hash", None)
    out["prev"] = prev
    out["hash"] = digest(out)
    return out


def write(path: pathlib.Path, entries: list[dict]) -> list[dict]:
    """Write a fresh chain, sealing each entry against the one before it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sealed, prev = [], GENESIS
    for index, entry in enumerate(entries, 1):
        row = dict(entry)
        row["seq"] = index
        row = seal(row, prev)
        sealed.append(row)
        prev = row["hash"]
    path.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in sealed), encoding="utf-8")
    return sealed


def read(path: pathlib.Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"__torn__": line})
    return out


def verify(entries: list[dict], expected_stages: list[str] | None = None) -> list[str]:
    """Return a list of problems. Empty list means the chain is intact."""
    problems: list[str] = []
    if not entries:
        return ["CHAIN_EMPTY: no receipts"]

    prev = GENESIS
    for index, entry in enumerate(entries, 1):
        if "__torn__" in entry:
            problems.append(f"CHAIN_TORN: line {index} is not valid JSON (killed mid-write)")
            continue
        if entry.get("seq") != index:
            problems.append(
                f"CHAIN_SEQ: line {index} has seq={entry.get('seq')}, expected {index}")
        if entry.get("prev") != prev:
            problems.append(
                f"CHAIN_RELINK: line {index} prev={entry.get('prev')!r} != expected {prev!r}")
        want = digest(entry)
        if entry.get("hash") != want:
            problems.append(
                f"CHAIN_HASH: line {index} hash={entry.get('hash')} != recomputed {want}")
        prev = entry.get("hash", "")

    if expected_stages:
        got = [e.get("stage") for e in entries if "__torn__" not in e]
        if got != expected_stages:
            problems.append(
                f"CHAIN_STAGES: stage sequence {got} != declared {expected_stages}"
                " (a missing or reordered stage is a truncation, not a pass)")
    return problems
