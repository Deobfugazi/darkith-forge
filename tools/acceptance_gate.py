#!/usr/bin/env python3
"""The frozen acceptance set: what "done" means, fixed before the work, hashed.

The directive's §6 requires that the acceptance predicates be frozen and carried as a
single hash, because a criterion that can be re-read after the fact can always be made
to fit whatever the tree happens to contain. The laws already carry a PREDICATE line
each; `policy_block.derive_laws` projects it into an `acceptance` field. This gate takes
that derivation, freezes it in `proof/acceptance.json`, and pins it with a sha256 over
the canonically ordered rows.

Freezing is not the same as passing. This gate answers one question: do the acceptance
criteria on disk today still describe the laws on disk today? Whether each criterion
holds is the job of the gate each law names, and that is measured elsewhere.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import policy_block  # noqa: E402

SET_PATH = ROOT / "proof" / "acceptance.json"
SCHEMA = "darkith-acceptance-set"


def _sha(rows: list[dict]) -> str:
    canon = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def rows() -> list[dict]:
    """One row per law, in document order: the criterion and the gate that measures it."""
    laws = policy_block.derive_laws(policy_block.read_doc())
    return [
        {
            "id": law["id"],
            "acceptance": law["acceptance"],
            "gate": law["gate"],
        }
        for law in laws
    ]


def build() -> dict:
    rws = rows()
    return {
        "schema": SCHEMA,
        "count": len(rws),
        "sha256": _sha(rws),
        "criteria": rws,
    }


def cmd_write() -> int:
    doc = build()
    SET_PATH.parent.mkdir(parents=True, exist_ok=True)
    SET_PATH.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        shown = SET_PATH.relative_to(ROOT)
    except ValueError:
        shown = SET_PATH
    print(
        f"acceptance_gate: froze {doc['count']} criteria "
        f"(sha256 {doc['sha256'][:16]}…) -> {shown}"
    )
    return 0


def cmd_check() -> int:
    if not SET_PATH.is_file():
        print(
            "acceptance_gate: FAIL — no frozen acceptance set; the criteria are not fixed, "
            "so nothing can be accepted against them (run --write, then commit it)"
        )
        return 2
    try:
        frozen = json.loads(SET_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"acceptance_gate: FAIL — acceptance set is not valid JSON: {e}")
        return 1

    problems = []
    if frozen.get("schema") != SCHEMA:
        problems.append(f"schema is {frozen.get('schema')!r}, expected {SCHEMA!r}")

    current = build()
    if frozen.get("count") != current["count"]:
        problems.append(
            f"frozen count {frozen.get('count')} != derived count {current['count']} "
            "— laws were added or removed since the set was frozen"
        )
    if frozen.get("sha256") != current["sha256"]:
        problems.append(
            f"frozen sha256 {str(frozen.get('sha256'))[:16]}… != derived "
            f"{current['sha256'][:16]}… — a criterion or gate changed under the freeze"
        )
    if frozen.get("criteria") != current["criteria"]:
        problems.append("frozen criteria differ from the derived criteria")

    if problems:
        print("acceptance_gate: FAIL")
        for p in problems:
            print(f"  - {p}")
        print("  the freeze is stale: re-derive, review the diff, then --write")
        return 1

    print(
        f"acceptance_gate: PASS — {current['count']} criteria frozen, hash matches "
        f"({current['sha256'][:16]}…), every law names a gate"
    )
    return 0


def selftest() -> int:
    """Prove the freeze detects a changed criterion and a missing set."""
    import tempfile

    ok = True
    real = SET_PATH
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "acceptance.json"
        globals()["SET_PATH"] = tmp

        if cmd_check() != 2:
            print("acceptance_gate selftest: FAIL — absent set was not refused")
            ok = False

        if cmd_write() != 0:
            print("acceptance_gate selftest: FAIL — could not write a set")
            ok = False
        if cmd_check() != 0:
            print("acceptance_gate selftest: FAIL — a freshly written set did not verify")
            ok = False

        doc = json.loads(tmp.read_text(encoding="utf-8"))
        doc["criteria"][0]["acceptance"] = "gate exits zero"
        doc["criteria"][0]["gate"] = "tools/law_gate.py"
        tmp.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if cmd_check() == 0:
            print("acceptance_gate selftest: FAIL — a tampered criterion still passed")
            ok = False

    globals()["SET_PATH"] = real
    if ok:
        print("acceptance_gate selftest: ok — absent refused, fresh verifies, tampered refused")
        return 0
    return 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="freeze the derived criteria")
    ap.add_argument("--check", action="store_true", help="verify the freeze is current")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.write:
        return cmd_write()
    return cmd_check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
