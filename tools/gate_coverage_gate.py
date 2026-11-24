#!/usr/bin/env python3
"""gate_coverage_gate.py — a gate with no caller is not a gate, it is a comment.

THE RECURRENCE THIS CLOSES
    Every session starts with an agent who has never seen this repository. The formulary
    (detect / repair / prevent, tools/autophagy.py) exists, is documented, and works — and
    the agent still rebuilds it in a new silo, because the formulary is written at line 1033
    of AGENTS.md and the agent has already started writing code by the time it gets there.
    Documentation cannot stop this. Only a gate that runs on the next agent's first CI can.

    So the class is not "an agent forgot". The class is "the tree permits an orphan". Four
    gates sat in this repo passing every test and never executing once: circadian_gate,
    convergence_gate, download_gate, synchrony_gate. Each was correct. None was called. That
    is FM-03 in the failure ledger — "a correct table with no caller" — and it is the exact
    shape of the silo an agent builds when it does not know a gate already exists.

THE RULE
    Every tools/*gate*.py must be named in tools/ci.sh. A gate that CI never runs cannot
    fail, and a gate that cannot fail is not evidence. Manual-only tools (make_icon.py,
    serve_hub.py — a build step and a server) are declared in MANUAL with the reason, so
    the exemption is a decision on the record rather than an oversight.

    This gate does not read prose. It reads whether the file is invoked. That is the only
    thing that distinguishes a gate from a comment.

Usage:
  python3 tools/gate_coverage_gate.py            # check
  python3 tools/gate_coverage_gate.py --selftest # prove it fires on an orphan
Exit: 0 = every gate has a caller; 1 = at least one gate is never invoked.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CI = ROOT / "tools" / "ci.sh"

# Tools that end in "gate" but are not gates: they are a build step and a server. Declared
# here with the reason, so "not in CI" is a decision somebody made, not a file somebody lost.
MANUAL = {
    "gate_coverage_gate.py": "this gate; CI calls it, but it also names itself so the "
                             "registry is complete when the file is read alone",
}


def gates() -> list[str]:
    return sorted(p.name for p in (ROOT / "tools").glob("*gate*.py"))


LOOP_HEAD = re.compile(r"^\s*for\s+\w+\s+in\s+(.+?);?\s*do\s*$")


def loop_members(ci_text: str) -> set:
    """Names enumerated by a shell `for g in a b c; do` loop that then invokes tools/$g.py.

    ci.sh runs five gates through one loop variable. A detector that only matches literal
    file names would call all five orphans and be wrong — a detector that cries wolf gets
    switched off, and a switched-off detector is worse than none. The indirection is real
    execution, so it is followed rather than excused.
    """
    lines = ci_text.splitlines()
    found = set()
    for i, line in enumerate(lines):
        m = LOOP_HEAD.match(line)
        if not m:
            continue
        body = "\n".join(lines[i + 1:i + 8])
        var = re.search(r"for\s+(\w+)\s+in", line).group(1)
        if f"tools/${var}.py" not in body and f"tools/${{{var}}}.py" not in body:
            continue
        found.update(tok for tok in m.group(1).split() if re.fullmatch(r"[\w-]+", tok))
    return found


def invoked(name: str, ci_text: str, looped: set = frozenset()) -> bool:
    """True when ci.sh actually runs this file, not merely mentions it in a comment."""
    stem = name[:-3] if name.endswith(".py") else name
    if stem in looped:
        return True
    for line in ci_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", stripped):
            return True
    return False


def orphans(ci_text: str) -> list[str]:
    looped = loop_members(ci_text)
    return [g for g in gates() if g not in MANUAL and not invoked(g, ci_text, looped)]


def declared_gates() -> list[tuple[str, str]]:
    """(law id, gate path) for every law that names a gate that exists.

    The glob above only sees files whose NAME contains "gate". A law may declare any file as
    its gate — SPI-10 names tools/kt_comment_scan.py — so a name-based scan reports full
    coverage over a law whose gate has no caller. Same defect class as FM-03, one level up:
    the registry cannot see the orphans it was built to find.
    """
    try:
        import policy_block
    except ImportError:
        sys.path.insert(0, str(ROOT / "tools"))
        import policy_block
    out = []
    for law in policy_block.derive_laws(policy_block.read_doc()):
        gate = (law.get("gate") or "").strip()
        if not gate:
            continue
        path = ROOT / gate
        if path.is_file():
            out.append((law["id"], gate))
    return out


def uncalled_declared(ci_text: str) -> list[tuple[str, str]]:
    """Laws whose declared gate file exists but which ci.sh never runs.

    `tools/ci.sh` is exempt: a law naming the suite itself is enforced by every gate in it,
    so asking whether ci.sh calls ci.sh is a category error.
    """
    looped = loop_members(ci_text)
    bad = []
    for law_id, gate in declared_gates():
        name = gate.rsplit("/", 1)[-1]
        if name == "ci.sh":
            continue
        if not invoked(name, ci_text, looped) and name not in MANUAL:
            bad.append((law_id, gate))
    return bad


def main(argv: list) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv[1:])

    ci_text = CI.read_text(encoding="utf-8") if CI.is_file() else ""

    if args.selftest:
        # A gate that only ever prints PASS is the defect it polices. Prove it can say NO:
        # a synthetic ci.sh that calls nothing must orphan every gate, and a synthetic one
        # that calls the orphans must clear them.
        full_text = "".join(f"run x python3 tools/{g}\n" for g in gates())
        empty = orphans("# nothing is called here\n")
        full = orphans(full_text)
        ok = bool(empty) and not full and invoked("foo_gate.py", "run 'x' python3 tools/foo_gate.py")
        # The declared-gate check must also be able to say NO. Calling every *gate*.py is the
        # blind spot in one line: that text still leaves SPI-10 unrun, because its gate has
        # no "gate" in the filename. Clearing it requires naming every declared gate.
        declared = declared_gates()
        all_declared_text = "".join(f"run x python3 {g}\n" for _, g in declared)
        blind_spot = uncalled_declared(full_text)
        declared_ok = (
            bool(declared)
            and bool(blind_spot)
            and any(gate == "tools/kt_comment_scan.py" for _, gate in blind_spot)
            and not uncalled_declared(all_declared_text)
            and len(uncalled_declared("# nothing is called here\n")) >= len(blind_spot)
        )
        print(f"gate_coverage_gate selftest: {'ok' if ok and declared_ok else 'FAIL'} — "
              f"empty ci orphans {len(empty)}, full ci orphans {len(full)}, "
              f"declared gates {len(declared)}, "
              f"declared-and-uncalled under empty ci {len(uncalled_declared('# nothing is called here\n'))}")
        return 0 if (ok and declared_ok) else 1

    bad = orphans(ci_text)
    if bad:
        print(f"gate_coverage_gate: FAIL — {len(bad)} gate(s) are never invoked by CI, "
              f"so they cannot fail and are not evidence:")
        for name in bad:
            print(f"  - tools/{name}  (no caller in tools/ci.sh)")
        print("  A gate that never runs is a comment. Wire it into ci.sh, or declare it in "
              "MANUAL with the reason it is not a gate.")
        return 1

    uncalled = uncalled_declared(ci_text)
    if uncalled:
        print(f"gate_coverage_gate: FAIL — {len(uncalled)} law(s) name a gate that CI never "
              f"calls, so the law is enforced by nothing:")
        for law_id, gate in uncalled:
            print(f"  - {law_id} -> {gate}  (no caller in tools/ci.sh)")
        print("  Either wire the gate into ci.sh, or point the law at the gate that does "
              "run. A law whose gate is never invoked is a comment with a filename.")
        return 1

    print(f"gate_coverage_gate: PASS — all {len(gates())} gate(s) have a CI caller, and "
          f"every law's declared gate is invoked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
