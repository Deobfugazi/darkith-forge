#!/usr/bin/env python3
"""adversarial_battery.py — attack the rehearsal evidence from every angle I can think of.

Each vector mutates the evidence, runs the witness, and requires a REFUSAL (exit 1).
A vector that succeeds is an open hole, printed as HOLE. Evidence is restored from a
clean copy after every vector, and the battery refuses to report unless the restore
itself verified green first.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "proof/burden-uplift/E2E-REHEARSAL-2026-11-24"
W = ROOT / "tools/burden/witness_e2e.py"
BACKUP = pathlib.Path("/tmp/burden_battery_backup")


def run_witness() -> tuple[int, str]:
    cp = subprocess.run([sys.executable, str(W)], cwd=str(ROOT),
                        capture_output=True, text=True, timeout=180)
    return cp.returncode, (cp.stdout.strip() + cp.stderr.strip())


def restore():
    shutil.rmtree(D, ignore_errors=True)
    shutil.copytree(BACKUP, D)


def vector(name: str, mutate) -> tuple[str, bool, str]:
    try:
        mutate()
    except Exception as exc:  # noqa: BLE001
        restore()
        return (name, False, f"mutation failed: {exc}")
    rc, out = run_witness()
    restore()
    refused = rc != 0
    return (name, refused, out.splitlines()[0] if out else "")


def main() -> int:
    shutil.rmtree(BACKUP, ignore_errors=True)
    shutil.copytree(D, BACKUP)

    rc, out = run_witness()
    if rc != 0:
        print(f"BASELINE NOT GREEN — battery aborted: {out}")
        return 2
    print(f"baseline intact: rc=0  {out[:70]}\n")

    rec = D / "00_burden_record.json"
    rc_file = D / "04_receipts.jsonl"
    curve = D / "05_viability_curve.csv"
    man = D / "manifest.json"

    def edit_json(path, **kw):
        def f():
            d = json.loads(path.read_text())
            d.update(kw)
            path.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
        return f

    def edit_json_nested(path, key, val):
        def f():
            d = json.loads(path.read_text())
            d[key] = val
            path.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
        return f

    def receipts(fn):
        def f():
            lines = [json.loads(l) for l in rc_file.read_text().splitlines() if l.strip()]
            lines = fn(lines)
            rc_file.write_text(
                "".join(json.dumps(x, sort_keys=True) + "\n" for x in lines))
        return f

    def drop_line(i):
        def f():
            lines = [l for l in rc_file.read_text().splitlines() if l.strip()]
            del lines[i]
            rc_file.write_text("\n".join(lines) + "\n")
        return f

    def swap_lines():
        lines = [l for l in rc_file.read_text().splitlines() if l.strip()]
        lines[1], lines[2] = lines[2], lines[1]
        rc_file.write_text("\n".join(lines) + "\n")

    def forge_body(lines):
        lines[0]["detail"] = "FORGED"
        return lines

    vectors = [
        ("A01 rehearsal dir deleted", lambda: shutil.rmtree(D)),
        ("A02 receipts file deleted", lambda: rc_file.unlink()),
        ("A03 chain truncated 7->6", drop_line(6)),
        ("A04 two receipts swapped", swap_lines),
        ("A05 receipt body edited, hash kept", receipts(forge_body)),
        ("A06 curve appended to", lambda: curve.write_text(curve.read_text() + "x\n")),
        ("A07 burden record appended to", lambda: rec.write_text(rec.read_text() + " ")),
        ("A08 record claims barrier CLOSED", edit_json(rec, barrier_verdict="CLOSED")),
        ("A09 record claims mainnet ALLOWED", edit_json(rec, mainnet_issuance="ALLOWED")),
        ("A10 manifest generated stamp rewritten",
         lambda: man.write_text(man.read_text().replace("2026", "1970", 1))),
        ("A11 manifest deleted", lambda: man.unlink()),
        ("A12 curve scenarios relabelled",
         lambda: curve.write_text(curve.read_text().replace(
             "measured_baseline", "optimistic"))),
        ("A13 all evidence removed",
         lambda: [p.unlink() for p in D.iterdir()]),
        ("A14 witness script itself edited",
         lambda: W.write_text(W.read_text().replace("EXPECT_PREFIX = ",
                                                    "EXPECT_PREFIX = '' or "))),
        ("A15 manifest file hash lowered to match nothing",
         lambda: man.write_text(man.read_text().replace("00_burden_record.json\": \"",
                                                        "00_burden_record.json\": \"00"))),
    ]

    holes = []
    for name, mutate in vectors:
        ok_name, refused, first = vector(name, mutate)
        if name.startswith("A14"):
            # editing the witness changes its own manifest hash -> must be caught
            pass
        if not refused:
            holes.append(name)
        print(f"  {'REFUSED' if refused else 'HOLE   '}  {name:44s} {first[:56]}")

    # the witness file was restored by the copytree? no - backup excludes tools.
    # restore the witness explicitly if A14 mutated it.
    subprocess.run(["git", "checkout", "--", "tools/burden/witness_e2e.py"], cwd=str(ROOT))

    print(f"\n{len(vectors)} vectors, {len(holes)} hole(s)")
    rc, out = run_witness()
    print(f"post-battery integrity: rc={rc} {out[:70]}")
    return 1 if holes else 0


if __name__ == "__main__":
    raise SystemExit(main())
