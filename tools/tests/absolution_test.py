#!/usr/bin/env python3
"""Witness the absolution gate: every verdict must fire, and the blind bot must fail.

The point of this file is not that the gate passes on a clean tree. It is that the gate can
tell the three cases apart that `if changed: write` could not:

    a no-op producer                    -> ABSOLVED
    a fixed point git already carries   -> ABSOLVED
    a fixed point git does NOT carry    -> CARRIAGE_REQUIRED   (named surplus, not silence)
    two runs that disagree              -> UNSTABLE            (no answer to give)
    a producer that writes elsewhere    -> FAIL                (unmarked write is extraction)
    a producer that exits non-zero      -> FAIL

A gate that only ever says ABSOLVED is the blind bot again, so the refusal checks are the
substance here.
"""
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import absolution as a  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" - {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def fixture(script_body: str, skip_exit_codes: tuple = ()) -> tuple:
    """A throwaway repo with one producer, committed so HEAD is a real authority."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="absolution-test-"))
    (tmp / "proof").mkdir(parents=True)
    (tmp / "proof" / "out.json").write_text('{"v": 1}\n', encoding="utf-8")
    (tmp / "producer.py").write_text(script_body, encoding="utf-8")
    env = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q"], cwd=str(tmp), check=True)
    subprocess.run(env + ["add", "-A"], cwd=str(tmp), check=True)
    subprocess.run(env + ["commit", "-qm", "fixture"], cwd=str(tmp), check=True)
    return tmp, {"name": "fixture", "cmd": ("python3", "producer.py"),
                 "owns": ("proof/out.json",), "skip_exit_codes": skip_exit_codes,
                 "why": "fixture"}


def run_case(body: str, skip_exit_codes: tuple = ()) -> dict:
    tmp, producer = fixture(body, skip_exit_codes)
    return a.witness(producer, tmp)


def main() -> int:
    print("ABSOLUTION GATE TEST")

    # 1. A producer that writes identical bytes every time, already carried by git.
    r = run_case(
        "import pathlib\n"
        "p = pathlib.Path('proof/out.json')\n"
        "want = '{\"v\": 1}\\n'\n"
        "if not p.is_file() or p.read_text() != want:\n"
        "    p.write_text(want)\n")
    check("identical rewrite of carried bytes is ABSOLVED", r["verdict"] == "ABSOLVED", r["why"])
    check("identical rewrite is recognised as a fixed point", r["fixed_point"] is True)

    # 2. The blind bot's blind spot: correct bytes, but not in git. It must be NAMED, not
    #    silently rewritten and not silently accepted.
    r = run_case(
        "import pathlib\n"
        "p = pathlib.Path('proof/out.json')\n"
        "want = '{\"v\": 2}\\n'\n"
        "if not p.is_file() or p.read_text() != want:\n"
        "    p.write_text(want)\n")
    check("uncommitted fixed point is CARRIAGE_REQUIRED", r["verdict"] == "CARRIAGE_REQUIRED",
          r["why"])
    check("carriage names the exact unreturned path", "proof/out.json" in r["why"])

    # 3. Two runs disagree: the producer has no answer, so no rewrite can be absolved.
    r = run_case(
        "import pathlib, random\n"
        "p = pathlib.Path('proof/out.json')\n"
        "p.write_text('{\"v\": %d}\\n' % random.randrange(10**9))\n")
    check("oscillating producer is UNSTABLE", r["verdict"] == "UNSTABLE", r["why"])
    check("oscillation is NOT a fixed point", r["fixed_point"] is False)

    # 4. The failure the blind bot could not see at all: correct bytes, written again anyway.
    #    Content is unchanged, git is content-addressed and blind, so only the write itself
    #    distinguishes this from an honest no-op.
    r = run_case(
        "import pathlib, time\n"
        "p = pathlib.Path('proof/out.json')\n"
        "p.write_text('{\"v\": 1}\\n')\n"
        "time.sleep(0.01)\n"
        "p.write_text('{\"v\": 1}\\n')\n")
    check("rewriting identical bytes is REDUNDANT_REWRITE",
          r["verdict"] == "REDUNDANT_REWRITE", r["why"])
    check("redundant rewrite is named", "proof/out.json" in r["why"])

    # 5. A write outside the declared outputs is extraction, whatever the bytes say.
    r = run_case(
        "import pathlib\n"
        "pathlib.Path('proof/out.json').write_text('{\"v\": 1}\\n')\n"
        "pathlib.Path('proof/smuggled.json').write_text('{}')\n")
    check("unmarked write outside declared outputs is FAIL", r["verdict"] == "FAIL", r["why"])
    check("the smuggled path is named", "proof/smuggled.json" in r["why"])

    # 6. A producer that cannot run cannot be absolved.
    r = run_case("import sys\nsys.exit(3)\n")
    check("non-zero producer is FAIL", r["verdict"] == "FAIL", r["why"])

    # 7. Exit 3 is an explicit, non-mutating environment skip only when declared.
    r = run_case("import sys\nsys.exit(3)\n", skip_exit_codes=(3,))
    check("declared unavailable producer is SKIPPED", r["verdict"] == "SKIPPED", r["why"])

    # 8. The gate must pass only when every applicable producer is absolved.
    doc = a.compute()
    check("live registry's active producers are absolved",
          doc["active"] > 0 and doc["absolved"] == doc["active"],
          f"{doc['absolved']}/{doc['active']} active; {doc['skipped']} skipped")
    check("live E/W_in is 0", doc["ratio"] == 0.0, str(doc["ratio"]))
    check("gate exit reflects active producer verdicts",
          a.main(["absolution.py"]) == (0 if doc["active"] > 0
                                      and doc["absolved"] == doc["active"] else 1))

    print()
    if FAILS:
        print(f"ABSOLUTION GATE TEST: FAIL — {len(FAILS)} check(s): {', '.join(FAILS)}")
        return 1
    print("ABSOLUTION GATE TEST: PASS — every refusal fires")
    return 0


if __name__ == "__main__":
    sys.exit(main())
