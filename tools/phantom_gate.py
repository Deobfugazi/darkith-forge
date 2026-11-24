#!/usr/bin/env python3
"""phantom_gate.py — a closed briefing must not be re-seeded into the next session.

THE RECURRENCE. A briefing arrives by chat: "19 Kotlin files lost the opening `/*`; inject
the markers at these lines." It was measured false once (18 of 19 cited lines already open a
valid `/**`; the 19th is a code line) and recorded CLOSED in tools/closed_briefings.py. It
still came back. Every session, an agent re-derived the same proof, spent the same tokens,
and delivered the same refusal.

WHY THE EXISTING GATE DID NOT STOP IT. closed_briefings.py scans TASKS.md and RESUME.md —
the task boards. It cannot see a brief that arrives in the chat. So the brief stayed out of
the gate's field of view while its PAYLOAD stayed in the repository, where any agent that
greps for the symptom finds it and reads it as live.

THE PAYLOAD IS THE VECTOR. docs/KOTLIN-STRIP-TABLE.json ships the 19 filenames and line
numbers verbatim, and its own `_why` admits it is bound to ../tree.orig — a pre-damage copy
where all 19 openers exist. An agent greps "unclosed comment", finds a table of files and
lines, and has no way to tell it is a fossil. A record of a defect reads exactly like a
report of one.

WHAT THIS GATE ENFORCES. Every tracked payload named below must:
  1. declare itself CLOSED, in the bytes an agent actually greps (a status key, first);
  2. carry the measurement that closed it — not an assertion, a number; and
  3. have that number still be TRUE against the live tree.

Rule 3 is what makes this a gate and not a comment. If the live tree ever really does lose
those openers, the recorded measurement stops matching, this gate fails, and the brief is
re-armed for a human to judge. Suppression that cannot notice a genuine regression is the
vacuous green this repository exists to refuse.

Usage:
  python3 tools/phantom_gate.py --check
  python3 tools/phantom_gate.py --selftest
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIVE_TREE = ROOT / "app/src/main/java"

# A payload is "seeding" when it names files and line numbers and asks for a marker.
SEEDING_KEY = re.compile(r"^_status$", re.I)
CLOSED_WORDS = re.compile(r"\bCLOSED\b|\bHISTORICAL\b|\bFOSSIL\b", re.I)
DO_NOT_ACT = re.compile(r"do[_ ]?not[_ ]?act|do not act", re.I)

PAYLOADS = [
    {
        "id": "comment-19files",
        "path": "docs/KOTLIN-STRIP-TABLE.json",
        "why": "ships the 19 filenames and line numbers; bound to ../tree.orig, not app/",
        "measure": "openers_present_at_cited_lines",
        "live": "app/src/main/java",
        "min_agree": 15,
    },
]


def _cited(files: dict) -> dict[str, int]:
    return {str(k): int(v) for k, v in files.items()}


def _resolve_live(stem: str, live_root: pathlib.Path) -> pathlib.Path | None:
    hits = sorted(live_root.rglob(stem))
    return hits[0] if hits else None


def measure(payload: dict) -> tuple[int, int, list[str]]:
    """Count cited lines that ALREADY open a block comment in the LIVE tree.

    Returns (already_open, considered, names_of_files_that_are_actually_defective).
    """
    data = json.loads((ROOT / payload["path"]).read_text(encoding="utf-8"))
    live_root = ROOT / payload["live"]
    cited = _cited(data.get("files", {}))
    already = 0
    defective: list[str] = []
    for stem, line in sorted(cited.items()):
        p = _resolve_live(stem, live_root)
        if p is None:
            defective.append(f"{stem} (absent from live tree)")
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) >= line and lines[line - 1].lstrip().startswith("/*"):
            already += 1
        else:
            defective.append(f"{stem}:{line}")
    return already, len(cited), defective


def check_payload(payload: dict) -> list[str]:
    """Return the problems that make this payload unsafe to leave in the tree."""
    problems: list[str] = []
    path = ROOT / payload["path"]
    if not path.is_file():
        return [f"MISSING: {payload['path']} (registry names a payload that is gone)"]

    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(text)
    except ValueError as exc:
        return [f"UNPARSEABLE: {payload['path']}: {exc}"]

    # 1. the first key an agent sees must say CLOSED
    first_key = next(iter(data), "")
    status = data.get("_status", "")
    if not SEEDING_KEY.match(first_key) or not CLOSED_WORDS.search(str(status)):
        problems.append(
            f"NOT MARKED CLOSED: {payload['path']} must open with a `_status` key whose value "
            f"says CLOSED/HISTORICAL (first key is {first_key!r}, status={status!r}); an agent "
            "greps this file and cannot tell a fossil from a live defect")
    if not DO_NOT_ACT.search(text):
        problems.append(
            f"NO INSTRUCTION BAR: {payload['path']} must contain 'do not act' so a reader who "
            "finds it is told to stop rather than to inject markers")

    # 2. the closing measurement must be recorded as a number
    recorded = data.get("_measurement", {}).get(payload["measure"])
    if not isinstance(recorded, int):
        problems.append(
            f"NO MEASUREMENT: {payload['path']} must record "
            f"_measurement.{payload['measure']} as an integer (found {recorded!r})")

    # 3. and that number must still be true — this is what re-arms the brief
    already, considered, defective = measure(payload)
    if isinstance(recorded, int) and recorded != already:
        problems.append(
            f"STALE MEASUREMENT: {payload['path']} claims {recorded}/{considered} cited lines "
            f"already open a comment, live tree says {already}/{considered} — the bytes moved; "
            "re-measure and re-judge, do not trust the fossil")
    if already < payload["min_agree"]:
        problems.append(
            f"PREMISE MAY BE LIVE: only {already}/{considered} cited lines open a comment in "
            f"{payload['live']} (threshold {payload['min_agree']}); real defects: "
            + ", ".join(defective[:6])
            + " — this briefing is NOT closed any more, escalate it to the Operator")
    return problems


def check() -> int:
    all_problems: list[str] = []
    for payload in PAYLOADS:
        all_problems += check_payload(payload)

    if all_problems:
        print(f"phantom_gate: FAIL — {len(all_problems)} problem(s); a closed brief can "
              "re-seed itself from these bytes:")
        for p in all_problems:
            print(f"  - {p}")
        return 1

    for payload in PAYLOADS:
        already, considered, _ = measure(payload)
        print(f"  [{payload['id']}] CLOSED and measured: {already}/{considered} cited lines "
              f"already open a comment in {payload['live']}")
        print(f"     payload: {payload['path']} — {payload['why']}")
        print(f"     do not act on it. Proof: python3 tools/comment_audit.py")
    print(f"phantom_gate: PASS — {len(PAYLOADS)} closed brief(s) marked, measured, and "
          "still false")
    return 0


def selftest() -> int:
    """Prove the gate fires on a live-looking payload AND stays silent on a marked one."""
    import shutil
    import tempfile

    global ROOT
    real_root = ROOT
    work = pathlib.Path(tempfile.mkdtemp(prefix="phantom-selftest-"))
    checks: list[tuple[str, bool, str]] = []
    try:
        ROOT = work
        live = work / "app/src/main/java"
        live.mkdir(parents=True)
        # a live tree where 18/19 cited lines already open a comment
        files = {}
        for i in range(19):
            name = f"F{i}.kt"
            files[name] = 3
            body = "package x\n\n/** doc */\nclass F\n" if i < 18 else "package x\n\nclass F\n"
            (live / name).write_text(body)
        (work / "docs").mkdir()
        payload = {
            "id": "t", "path": "docs/T.json", "why": "test",
            "measure": "openers_present_at_cited_lines",
            "live": "app/src/main/java", "min_agree": 15,
        }
        pj = work / payload["path"]

        # 1. a bare fossil — reads exactly like a live report — MUST be refused
        pj.write_text(json.dumps({"files": files}, indent=1))
        p1 = check_payload(payload)
        checks.append(("bare fossil is refused", bool(p1), f"{len(p1)} problem(s)"))

        # 2. marked CLOSED with the WRONG measurement MUST be refused
        pj.write_text(json.dumps({"_status": "CLOSED", "_do_not_act": "do not act",
                                  "_measurement": {"openers_present_at_cited_lines": 3},
                                  "files": files}, indent=1))
        p2 = check_payload(payload)
        checks.append(("stale measurement is refused",
                       any("STALE MEASUREMENT" in x for x in p2), f"{len(p2)} problem(s)"))

        # 3. honestly marked and correctly measured MUST pass — the control
        pj.write_text(json.dumps({"_status": "CLOSED — HISTORICAL FOSSIL",
                                  "_do_not_act": "do not act on this table",
                                  "_measurement": {"openers_present_at_cited_lines": 18},
                                  "files": files}, indent=1))
        p3 = check_payload(payload)
        checks.append(("honest control passes", not p3, "; ".join(p3)[:80]))

        # 4. a REAL regression MUST re-arm the brief
        (live / "F0.kt").write_text("package x\n\nclass F\n")
        for i in range(19):
            (live / f"F{i}.kt").write_text("package x\n\nclass F\n")
        pj.write_text(json.dumps({"_status": "CLOSED", "_do_not_act": "do not act",
                                  "_measurement": {"openers_present_at_cited_lines": 0},
                                  "files": files}, indent=1))
        p4 = check_payload(payload)
        checks.append(("genuine regression re-arms", any("PREMISE MAY BE LIVE" in x for x in p4),
                       f"{len(p4)} problem(s)"))
    finally:
        ROOT = real_root
        shutil.rmtree(work, ignore_errors=True)

    print("=" * 78)
    print("PHANTOM GATE — SELFTEST")
    print("=" * 78)
    holes = 0
    for name, ok, detail in checks:
        holes += not ok
        print(f"  [{'PASS' if ok else 'HOLE'}] {name}  {detail}")
    print(f"\nSELFTEST: {'PASS' if holes == 0 else 'FAIL'} ({holes} hole(s))")
    return 0 if holes == 0 else 1


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    return check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
