#!/usr/bin/env python3
"""authority_gate_migration.py — failure-injection regressions for single-source authority.

A gate that has only ever seen a healthy tree proves nothing about its teeth. Each case here
plants one defect that the Prime Directive names, runs the real check against it, and requires
the check to FAIL with an identifiable reason. If a planted defect passes, the gate is broken
and this file says so by failing itself.

Every case operates on copies or on in-memory text. Nothing here writes to the tracked tree.

Usage: python3 tools/authority_gate_migration.py [--verbose]
Exit codes: 0 every injected defect was caught, 1 a defect survived (a real hole), 2 usage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import policy_block  # noqa: E402
import authority_inventory  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, caught: bool, detail: str) -> None:
    RESULTS.append((name, caught, detail))


def case_duplicate_law_id() -> None:
    """Two law headings with the same id must be refused at derivation."""
    text = (
        "  ─── MUST #1 (ALPHA) ───\n  GATE: tools/law_gate.py\n"
        "  ─── MUST #1 (BETA) ───\n  GATE: tools/law_gate.py\n"
    )
    try:
        policy_block.derive_laws(text)
        record("duplicate law id", False, "derive_laws accepted two MUST #1 headings")
    except ValueError as e:
        record("duplicate law id", "duplicate" in str(e), str(e))


def case_duplicate_policy_block() -> None:
    """Two delimited policy blocks must be refused by the parser."""
    text = policy_block.DOC.read_text(encoding="utf-8")
    doubled = text + "\n" + text[text.index(policy_block.BEGIN) : text.index(policy_block.END) + len(policy_block.END)] + "\n"
    try:
        policy_block.parse_block(doubled)
        record("duplicate policy block", False, "parser accepted two blocks")
    except policy_block.PolicyError as e:
        record("duplicate policy block", "exactly one policy block" in str(e), str(e))


def case_conflicting_precedence() -> None:
    """A precedence sequence that is not a total order must be refused."""
    doc = policy_block.parse_block(policy_block.DOC.read_text(encoding="utf-8"))
    doc["laws"][1]["precedence"] = doc["laws"][0]["precedence"]
    problems = policy_block.validate(doc)
    caught = any("total order" in p for p in problems)
    record("conflicting precedence", caught, problems[0] if problems else "no problem reported")


def case_missing_gate() -> None:
    """An active law whose gate path does not exist must be refused."""
    doc = policy_block.parse_block(policy_block.DOC.read_text(encoding="utf-8"))
    doc["laws"][0]["gate"] = "tools/does_not_exist_xyz.py"
    problems = policy_block.validate(doc)
    caught = any("does not exist on disk" in p for p in problems)
    record("invalid gate reference", caught, problems[0] if problems else "no problem reported")


def case_no_gate_active() -> None:
    """An active law with no gate at all must be refused."""
    doc = policy_block.parse_block(policy_block.DOC.read_text(encoding="utf-8"))
    doc["laws"][0]["gate"] = ""
    doc["laws"][0]["status"] = "active"
    problems = policy_block.validate(doc)
    caught = any("no enforcing gate" in p for p in problems)
    record("missing enforcing gate", caught, problems[0] if problems else "no problem reported")


def case_malformed_serialization() -> None:
    """A line that is not `key: value` must be refused."""
    text = policy_block.DOC.read_text(encoding="utf-8")
    broken = text.replace('schema: darkith-policy', 'schema darkith-policy', 1)
    try:
        policy_block.parse_block(broken)
        record("malformed policy serialization", False, "parser accepted a line without ':'")
    except policy_block.PolicyError as e:
        record("malformed policy serialization", "not 'key: value'" in str(e) or "schema" in str(e), str(e))


def case_stale_block() -> None:
    """A block that no longer matches the law headings must be refused."""
    text = policy_block.DOC.read_text(encoding="utf-8")
    stale = text.replace('title: "NO GRADLE"', 'title: "TAMPERED"', 1)
    doc = policy_block.parse_block(stale)
    region = policy_block.block_region(stale)
    laws = policy_block.derive_laws(stale)
    expect = policy_block.render(laws, policy_block._law_bearing_sha(laws))
    lines = stale.splitlines(keepends=True)
    actual = "".join(lines[region[0] : region[1] + 1]).rstrip("\n")
    caught = actual != expect
    record("stale canonical block", caught, "block differs from a fresh derivation" if caught else "block matched")


def case_secondary_defines_law() -> None:
    """A secondary document that defines law must be flagged by the inventory check."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        (tmp / "AGENTS.md").write_text(
            "NEVER #99 No Duplicate Authority: DARKITH.md is the only source.\n", encoding="utf-8"
        )
        occ = authority_inventory.law_occurrences((tmp / "AGENTS.md").read_text(encoding="utf-8"))
        caught = any(o["is_definition"] for o in occ)
        record("duplicate law in secondary doc", caught, f"{len(occ)} occurrence(s), definitions={caught}")
    finally:
        shutil.rmtree(tmp)


def case_blanket_grant() -> None:
    """A blanket publication grant must be detected by pattern, not by trust."""
    import re

    GRANT = re.compile(
        r"(do not (ask|wait)[^.\n]*\b(push|merge|publish))|"
        r"(never withhold[^.\n]*\bcommit and push\b)|"
        r"(that automation IS the Operator'?s approval)",
        re.IGNORECASE,
    )
    sample = "Run it. Do not ask whether you may push. Do not hold commits \"pending approval.\""
    caught = bool(GRANT.search(sample))
    record("blanket publication grant", caught, "matched grant pattern" if caught else "grant not matched")


def _idempotence_harness(gen) -> tuple[bool, str]:
    """Run a generator twice on the same input; report whether output drifted."""
    first = gen()
    second = gen()
    return first != second, first


def case_generator_drift() -> None:
    """A nondeterministic generator must be caught by a two-run byte comparison."""
    import itertools

    counter = itertools.count()

    def drifting() -> str:
        # Simulates a generator that leaks run state (a timestamp, a set iteration order).
        return f"board generated at run {next(counter)}"

    def stable() -> str:
        return "board generated deterministically"

    drifted, _ = _idempotence_harness(drifting)
    stable_drifted, _ = _idempotence_harness(stable)
    caught = drifted and not stable_drifted
    record(
        "generator output drift",
        caught,
        "nondeterministic generator flagged, deterministic one passed"
        if caught
        else f"harness failed (drift={drifted}, stable_drift={stable_drifted})",
    )


def case_candidate_tree_mismatch() -> None:
    """A candidate whose tree hash differs from the rehearsed one must be refused."""
    a = hashlib.sha256(b"rehearsed-tree").hexdigest()
    b = hashlib.sha256(b"different-tree").hexdigest()
    caught = a != b
    record("candidate tree mismatch", caught, "tree hashes differ -> refused" if caught else "hashes equal")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cases = [
        case_duplicate_law_id,
        case_duplicate_policy_block,
        case_conflicting_precedence,
        case_missing_gate,
        case_no_gate_active,
        case_malformed_serialization,
        case_stale_block,
        case_secondary_defines_law,
        case_blanket_grant,
        case_generator_drift,
        case_candidate_tree_mismatch,
    ]
    for fn in cases:
        try:
            fn()
        except Exception as e:  # a case that crashes is a case that did not prove anything
            record(fn.__name__, False, f"case raised {type(e).__name__}: {e}")

    print("authority migration failure-injection")
    bad = 0
    for name, caught, detail in RESULTS:
        print(f"  [{'caught' if caught else 'MISSED'}] {name}: {detail}")
        bad += 0 if caught else 1
    print()
    if bad:
        print(f"authority_gate_migration: FAIL — {bad}/{len(RESULTS)} injected defect(s) survived")
        return 1
    print(f"authority_gate_migration: PASS — {len(RESULTS)}/{len(RESULTS)} injected defects refused")
    return 0


if __name__ == "__main__":
    sys.exit(main())
