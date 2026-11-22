#!/usr/bin/env python3
"""Witness the run feed and the derived governance. Each check names the failure it prevents."""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import run_feed as rf  # noqa: E402
import revitalization as rv  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" - {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def main():
    print("== the feed is hash-chained: a rewritten line is caught ==")
    original = rf.FEED
    with tempfile.TemporaryDirectory() as tmp:
        rf.FEED = pathlib.Path(tmp) / "feed.jsonl"
        rf.append("start", "R1", stage="S01", detail="baseline")
        rf.append("terminal", "R1", verdict="PASS")
        ok, problems = rf.verify()
        check("a clean chain verifies", ok, str(problems))
        check("two entries landed", len(rf.read_entries()) == 2)

        lines = rf.FEED.read_text().splitlines()
        entry = json.loads(lines[1])
        entry["verdict"] = "FORGED"
        lines[1] = json.dumps(entry, sort_keys=True)
        rf.FEED.write_text("\n".join(lines) + "\n")
        ok, problems = rf.verify()
        check("a forged verdict breaks the chain", not ok, str(problems))
        check("and the problem names the hash", any("hash mismatch" in p for p in problems))

        print("== the severance detector: a run that dies without a terminal is named ==")
        rf.FEED.write_text("")
        rf.append("start", "R-ALIVE", stage="S01")
        rf.append("terminal", "R-ALIVE", verdict="PASS")
        rf.append("start", "R-DEAD", stage="S04")
        dead = rf.severed(timeout=0)
        ids = [d["run_id"] for d in dead]
        check("the dead run is reported", ids == ["R-DEAD"], str(ids))
        check("the live run is not", "R-ALIVE" not in ids)
        check("the reason names a severed run", "severed" in dead[0]["reason"])

        print("== a torn final line is the signature of a kill, and is reported ==")
        with rf.FEED.open("a", encoding="utf-8") as handle:
            handle.write('{"seq":99,"kind":"sta')
        ok, problems = rf.verify()
        check("a torn write fails verification", not ok)
        check("and is named as torn", any("torn" in p for p in problems), str(problems))

        print("== identity is recorded, and unknown is never invented ==")
        rf.FEED.write_text("")
        entry = rf.append("start", "R-ID", stage="S01")
        for field in ("agent", "model", "vendor", "session", "tab"):
            check(f"entry carries {field}", field in entry, str(entry.get(field)))
        check("model defaults to UNKNOWN, not a guess", entry["model"] == "UNKNOWN",
              entry["model"])
    rf.FEED = original

    print("== derived governance reads the law a gate cites, from its own bytes ==")
    class Fake:
        tool_of = staticmethod(rv.Pipeline.tool_of)
        derive_governance = rv.Pipeline.derive_governance
        defined_laws = classmethod(lambda cls: rv.Pipeline.defined_laws())

    fake = Fake()
    sensor = fake.derive_governance("python3 tools/nt_sensor.py")
    check("nt_sensor derives a clause", bool(sensor.get("governing_clause")), str(sensor))
    check("nt_sensor derives a root cause",
          sensor.get("root_cause") == "GATE_FAILURE::NT_SENSOR", str(sensor.get("root_cause")))
    check("build/ gates are located too",
          rv.Pipeline.tool_of("python3 build/verify.py --fast") == "build/verify.py")

    print("== a citation the law does not define is never derived ==")
    # board_law_gate.py mentions NEVER #10 only to say it does not exist. Reading that as
    # governance would put a fabricated law on the board.
    check("a fabricated citation yields no clause",
          fake.derive_governance("python3 tools/board_law_gate.py") == {},
          str(fake.derive_governance("python3 tools/board_law_gate.py")))
    check("NEVER-10 is not in the law inventory",
          "NEVER-10" not in rv.Pipeline.defined_laws())

    print("== a gate that cites no law stays honestly UNCONFIRMED ==")
    check("no clause invented for a silent gate",
          fake.derive_governance("python3 tools/savf_parity_gate.py") == {})

    print()
    if FAILS:
        print(f"RUN FEED TEST: FAIL ({len(FAILS)}): {FAILS}")
        return 1
    print("RUN FEED TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
