#!/usr/bin/env python3
"""witness_e2e.py - the independent reproducer for burden KC-BURDEN-2026-1124-E2E.
Any third party, on the exact landed SHA:  python3 tools/burden/witness_e2e.py
prints EXPECT:BURDEN_ABSENT_REHEARSAL_OK (exit 0) iff the rehearsal receipt chain is
intact and every manifest hash matches the bytes on disk. Anything else is a named
failure: BURDEN_PRESENT / CHAIN_BROKEN_AT n / MANIFEST_TAMPER path. Exit code 1."""
import hashlib, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPECT = "BURDEN_ABSENT_REHEARSAL_OK"
def main():
    d = ROOT / "proof/burden-uplift/E2E-REHEARSAL-2026-11-24"
    receipt = d / "04_receipts.jsonl"
    manifest = d / "manifest.json"
    if not receipt.is_file() or not manifest.is_file():
        print("BURDEN_PRESENT"); return 1
    prev = "GENESIS"
    for line in receipt.read_text().splitlines():
        if not line.strip(): continue
        rec = json.loads(line)
        payload = dict(rec); payload.pop("receipt_sha256", None); payload.pop("prev", None)
        want = hashlib.sha256((prev + json.dumps(payload, sort_keys=True)).encode()).hexdigest()
        if rec.get("prev") != prev or rec.get("receipt_sha256") != want:
            print("CHAIN_BROKEN_AT", rec.get("seq")); return 1
        prev = rec["receipt_sha256"]
    for p, h in json.loads(manifest.read_text())["files"].items():
        real = hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        if real != h:
            print("MANIFEST_TAMPER", p); return 1
    print("EXPECT:" + EXPECT)
    return 0
sys.exit(main())
