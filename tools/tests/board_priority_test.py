#!/usr/bin/env python3
"""Witness the board priority engine. Each check names the failure it prevents."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import board_priority as bp  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" - {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def task(**kw):
    base = {"id": "REV-x", "probes": ["p"], "root_cause": "UNCONFIRMED",
            "governing_file": "UNCONFIRMED", "acceptance_criteria": []}
    base.update(kw)
    return base


def main():
    print("== severity is derived from the governing layer, not from taste ==")
    law = task(governing_file="DARKITH.md")
    apparatus = task(governing_file="tools/autophagy.py")
    product = task(governing_file="app/src/main/java/Foo.kt")
    generated = task(governing_file="build/gen/Emitted.kt")
    check("law outranks apparatus", bp.severity_of(law)[1] < bp.severity_of(apparatus)[1])
    check("apparatus outranks product",
          bp.severity_of(apparatus)[1] < bp.severity_of(product)[1])
    check("product outranks generated",
          bp.severity_of(product)[1] < bp.severity_of(generated)[1])
    check("an unlocated defect is held at law level",
          bp.severity_of(task())[1] == 0,
          "nothing bounds its blast radius")

    print("== an unlocated defect says WHY, and does not claim a layer it lacks ==")
    why = bp.severity_of(task())[2]
    check("reason names the real cause, not a borrowed one",
          "unconfirmed" in why and "wrong law" not in why, why)

    print("== a destructive-capable repair is never below HIGH ==")
    signing = task(governing_file="proof/convergence.json", probes=["apksigner test"])
    check("a signing repair on a generated file is still HIGH",
          bp.severity_of(signing)[1] <= 1, bp.severity_of(signing)[0])
    check("its reason names destructive capability",
          "destructive" in bp.severity_of(signing)[2])

    print("== sequencing: severity, then blast radius, then discovery order ==")
    tasks = [
        task(id="LOW-WIDE", governing_file="build/gen/x.py", probes=["a", "b", "c", "d"]),
        task(id="CRIT", governing_file="DARKITH.md", probes=["z"]),
        task(id="MID", governing_file="app/Foo.kt", probes=["m"]),
        task(id="MID2", governing_file="app/Bar.kt", probes=["n"]),
    ]
    order = [row["task"]["id"] for row in bp.sequence(tasks)]
    check("law first", order[0] == "CRIT", str(order))
    check("generated last", order[-1] == "LOW-WIDE", str(order))
    check("equal severity keeps discovery order",
          order[1:3] == ["MID", "MID2"], str(order))

    wide = task(id="WIDE", governing_file="app/A.kt", probes=["a", "b", "c"])
    narrow = task(id="NARROW", governing_file="app/B.kt", probes=["a"])
    wide_first = [r["task"]["id"] for r in bp.sequence([narrow, wide])]
    check("wider blast radius sorts first at equal severity",
          wide_first == ["WIDE", "NARROW"], str(wide_first))

    print("== sequencing is deterministic (a board that churns is unreadable) ==")
    first = [r["task"]["id"] for r in bp.sequence(tasks)]
    second = [r["task"]["id"] for r in bp.sequence(list(tasks))]
    check("same input, same order", first == second, str(first))

    print("== failure modes: only the ones this task can actually cause ==")
    deliver = task(probes=["delivery gate (source laws)"])
    codes = [title for _, title, _ in bp.failure_modes(deliver)]
    check("delivery names unexamined source", any("UNEXAMINED SOURCE" in c for c in codes))
    check("delivery does not name stale index",
          not any("exact bytes" in c.lower() for c in codes),
          "an unrelated law on every task is wallpaper")

    unknown = task(probes=["a probe nobody registered"])
    check("an unbound probe still gets the two universal laws",
          len(bp.failure_modes(unknown)) >= 2)

    print("== destructive failure modes are listed before deficiencies ==")
    payload = task(probes=["one-shot installer"])
    kinds = [k for k, _, _ in bp.failure_modes(payload)]
    if "DESTRUCTIVE" in kinds and "DEFICIENCY" in kinds:
        check("corrupting precedes substandard",
              kinds.index("DESTRUCTIVE") < kinds.index("DEFICIENCY"), str(kinds))
    else:
        check("payload carries both kinds", False, str(kinds))

    print("== deduplication: one law appears once, even when two probes name it ==")
    both = task(probes=["delivery gate (source laws)", "§19 fork integrity gate (compile proof)"])
    titles = [t for _, t, _ in bp.failure_modes(both)]
    check("no duplicate NEVER titles", len(titles) == len(set(titles)), str(titles))

    print("== the staging trial is always last, and always CRITICAL ==")
    rendered = bp.render(bp.sequence(tasks), False)
    tail = [line for line in rendered if "STAGING" in line or "staging trial" in line]
    check("staging trial is present", bool(tail))
    check("staging trial is the final step",
          any("STEP 5" in line for line in tail),
          f"{len(tasks)} tasks then trial = STEP 5")
    check("staging trial is CRITICAL", any("CRITICAL" in line for line in tail))
    check("staging trial demands the stress run",
          any("tools/tests/run.sh" in line for line in rendered))
    check("staging trial demands full CI",
          any("tools/ci.sh" in line for line in rendered))

    print("== an open board shows unchecked boxes; a closed board checks them ==")
    open_lines = bp.render(bp.sequence(tasks), False)
    closed_lines = bp.render(bp.sequence(tasks), True)
    check("open board: unchecked box is open work",
          all("[ ]" in line for line in open_lines if line.startswith("- [")
              ), "an unchecked box must mean open work")
    check("closed board: every box checked",
          all("[x]" in line for line in closed_lines if line.startswith("- [")
              ))

    print("== an empty backlog is stated, not silently blank ==")
    empty = bp.render(bp.sequence([]), True)
    check("empty board says so", any("no open step" in line for line in empty), str(empty))

    print("== the board must not mint tokens that parse as law ==")
    # `directive_core` reads `- **MUST 17**` as a law declaration, so a numbered board
    # step labelled MUST is enrolled as an uncoupled law and fails CI. STEP is inert.
    import re as _re
    law_shaped = _re.compile(r"^\s*[-*]\s*\*\*(?:NEVER|MUST|SPI|RULE|INVARIANT|LAW)"
                             r"[\s]*[-#]?[\s]*\d+", _re.IGNORECASE)
    offenders = [line for line in open_lines if law_shaped.match(line)]
    check("no board line parses as a law declaration", not offenders, str(offenders))

    print("== every taxonomy entry is well formed ==")
    bad = [code for code, entry in bp.TAXONOMY.items()
           if len(entry) != 3 or entry[0] not in ("DESTRUCTIVE", "DEFICIENCY")
           or not entry[1] or not entry[2]]
    check("no malformed taxonomy entry", not bad, str(bad))
    check("every binding points at a real entry",
          all(code in bp.TAXONOMY
              for codes in bp.BINDINGS.values() for code in codes))

    print()
    if FAILS:
        print(f"BOARD PRIORITY TEST: FAIL ({len(FAILS)}): {FAILS}")
        return 1
    print("BOARD PRIORITY TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
