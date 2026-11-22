#!/usr/bin/env python3
"""Seed the communal contribution ledger with claims about THIS tree.

Each mint is a claim plus a witness anyone can re-run offline. The phantoms are claims
that look like mints and must fail — they are the trial net's test cases, and the whole
point is that they get caught.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import mint_ledger as m  # noqa: E402

MINTS = [
    ("the NT XII treatise is carried in the tree",
     'python3 -c "import pathlib;print(\'NT12_PRESENT\' if pathlib.Path(\'docs/nt/NT-XII.txt\').is_file() else \'MISSING\')"',
     "NT12_PRESENT"),
    ("the hash-chained ledger implementation exists",
     'python3 -c "import pathlib;print(\'LEDGER_PRESENT\' if pathlib.Path(\'nodal/ledger.py\').is_file() else \'MISSING\')"',
     "LEDGER_PRESENT"),
    ("the raw chain forbids Gradle at the gate level",
     'python3 -c "import pathlib;t=pathlib.Path(\'tools/ci.sh\').read_text();print(\'NO_GRADLE_GATE\' if \'gradle\' in t.lower() else \'UNGATED\')"',
     "NO_GRADLE_GATE"),
    ("the run feed reports severance",
     'python3 -c "import pathlib;print(\'FEED_PRESENT\' if pathlib.Path(\'tools/run_feed.py\').is_file() else \'MISSING\')"',
     "FEED_PRESENT"),
    ("the board states the MUST contract",
     'python3 -c "import pathlib;t=pathlib.Path(\'TASKS.md\').read_text();print(\'MUST_CONTRACT\' if \'An unchecked box is a MUST\' in t else \'ABSENT\')"',
     "MUST_CONTRACT"),
]

PHANTOMS = [
    # Claims a file that is not there. Must be caught.
    ("a non-existent sovereignty manifest",
     'python3 -c "import pathlib;print(\'MANIFEST_OK\' if pathlib.Path(\'docs/SOVEREIGN-MANIFEST.md\').is_file() else \'MISSING\')"',
     "MANIFEST_OK"),
    # Claims a gate exists that does not. Must be caught.
    ("a sybil gate that was never written",
     'python3 -c "import pathlib;print(\'SYBIL_GATED\' if pathlib.Path(\'tools/sybil_gate.py\').is_file() else \'MISSING\')"',
     "SYBIL_GATED"),
]


def main():
    for claim, witness, expect in MINTS:
        record = m.mint(claim, witness, expect)
        print(f"mint     {record['id']}  {claim}")
    for claim, witness, expect in PHANTOMS:
        record = m.mint(claim, witness, expect, kind="phantom")
        print(f"phantom  {record['id']}  {claim}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
