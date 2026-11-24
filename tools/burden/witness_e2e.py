#!/usr/bin/env python3
"""witness_e2e.py — the independent reproducer for burden KC-BURDEN-2026-1124-E2E.

Any third party, on the landed SHA:

    python3 tools/burden/witness_e2e.py

prints exactly one line and exits 0 only if the whole rehearsal is intact:

    EXPECT:BURDEN_ABSENT_REHEARSAL_OK <merkle-root>

The token is NOT a constant. The suffix is the merkle root of the receipt chain
recomputed from the bytes on disk, so the token differs for every distinct chain.
A witness that prints a fixed string proves nothing; this one cannot be satisfied
by editing the script, because the string it must print is derived from the
evidence it must also validate.

Named failures, exit 1, no false pass:
    BURDEN_PRESENT                 the rehearsal directory is absent
    CHAIN_<CODE>                   the receipt chain does not verify
    MANIFEST_TAMPER <path>         a file does not match its recorded digest
    MANIFEST_MISSING <path>        a recorded file is gone
    BARRIER_OVERCLAIM <field>      the record claims closure it has not earned
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import receipt_chain  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "proof/burden-uplift/E2E-REHEARSAL-2026-11-24"
EXPECT_PREFIX = "EXPECT:BURDEN_ABSENT_REHEARSAL_OK"

DECLARED_STAGES = [
    "S01_BASELINE",
    "S02_REPAIR",
    "S03_REPRODUCTION_CONTRACT",
    "S04_PHANTOM_DUPLICATE_ID",
    "S05_PHANTOM_CONSTANT_WITNESS",
    "S06_BARRIER_STATUS",
    "S07_ENTRAINMENT_CURVE",
]


def merkle_root(hashes: list[str]) -> str:
    """Fold the ordered receipt hashes into one root. Any edit moves the root."""
    level = list(hashes)
    if not level:
        return hashlib.sha256(b"").hexdigest()
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            nxt.append(hashlib.sha256((left + right).encode()).hexdigest())
        level = nxt
    return level[0]


def main() -> int:
    receipt = D / "04_receipts.jsonl"
    manifest = D / "manifest.json"
    if not receipt.is_file() or not manifest.is_file():
        print("BURDEN_PRESENT")
        return 1

    entries = receipt_chain.read(receipt)
    problems = receipt_chain.verify(entries, DECLARED_STAGES)
    if problems:
        for p in problems:
            print(p)
        return 1

    try:
        declared = json.loads(manifest.read_text())["files"]
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"MANIFEST_UNREADABLE {exc}")
        return 1

    for rel, want in sorted(declared.items()):
        path = ROOT / rel
        if not path.is_file():
            print(f"MANIFEST_MISSING {rel}")
            return 1
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != want:
            print(f"MANIFEST_TAMPER {rel}")
            return 1

    record = json.loads((D / "00_burden_record.json").read_text())
    if record.get("barrier_verdict") not in (None, "NOT_CLOSED"):
        print(f"BARRIER_OVERCLAIM barrier_verdict={record.get('barrier_verdict')!r}")
        return 1
    if record.get("mainnet_issuance") not in (None, "FORBIDDEN"):
        print(f"BARRIER_OVERCLAIM mainnet_issuance={record.get('mainnet_issuance')!r}")
        return 1

    root = merkle_root([e["hash"] for e in entries])
    print(f"{EXPECT_PREFIX} {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
