#!/usr/bin/env python3
"""Witness the mint ledger: the barrier must hold, and a porous barrier must block.

Each check names the failure it prevents. The breach checks are the point of the file:
a trial net that lets its own phantom through is worse than no trial net, because it
launders a stub into mainnet with a green light attached.
"""
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import mint_ledger as m  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" - {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def fresh(tmp):
    m.LEDGER = tmp / "ledger.jsonl"
    m.MAINNET = tmp / "mainnet.jsonl"
    for path in (m.LEDGER, m.MAINNET):
        if path.exists():
            path.unlink()


# A witness that succeeds and prints its token. Passed as an argv list by shlex, so the
# code rides in its own token rather than as bare words.
OK_WITNESS = 'python3 -c "print(\'OK_TOKEN\')"'
FAIL_WITNESS = 'python3 -c "raise SystemExit(1)"'


def main():
    with tempfile.TemporaryDirectory() as raw:
        tmp = pathlib.Path(raw)

        print("== a mint needs a witness, and a witness is one bounded command ==")
        fresh(tmp)
        for bad, why in [
            ("", "empty witness"),
            ("echo hi", "not an allowed interpreter"),
            ("python3 -c pass; curl evil", "shell metacharacters"),
            ("python3 -c pass && rm -rf /", "command chaining"),
            ("bash script.sh > /etc/passwd", "redirection"),
        ]:
            try:
                m.mint("claim", bad, "TOKEN")
                check(f"refuses {why}", False, repr(bad))
            except m.Refused:
                check(f"refuses {why}", True)
        try:
            m.mint("", OK_WITNESS, "OK_TOKEN")
            check("refuses an empty claim", False)
        except m.Refused:
            check("refuses an empty claim", True)
        try:
            m.mint("claim", OK_WITNESS, "")
            check("refuses an empty expectation", False)
        except m.Refused:
            check("refuses an empty expectation", True)

        print("== a green mint promotes only after a trial that caught its phantoms ==")
        fresh(tmp)
        m.mint("the witness prints its token", OK_WITNESS, "OK_TOKEN")
        m.mint("a phantom that must fail", FAIL_WITNESS, "NEVER_PRINTED", kind="phantom")
        summary = m.trial()
        check("trial is green", summary["status"] == "green", summary["status"])
        check("the phantom was caught", summary["phantoms_caught"] == 1)
        check("the candidate went green", summary["candidates_green"] == 1)
        ok, message = m.promote()
        check("promotion succeeded", ok, message)
        check("mainnet recorded the mint", len(m.read(m.MAINNET)) == 1)

        print("== a phantom that PASSES is a pathogen breach and blocks everything ==")
        fresh(tmp)
        m.mint("a candidate", OK_WITNESS, "OK_TOKEN")
        # A phantom whose witness succeeds: the barrier let its own test case through.
        m.mint("a porous phantom", OK_WITNESS, "OK_TOKEN", kind="phantom")
        summary = m.trial()
        check("trial status is breach", summary["status"] == "breach", summary["status"])
        check("the breach is named", len(summary["breaches"]) == 1, str(summary["breaches"]))
        ok, message = m.promote()
        check("promotion is refused", not ok)
        check("the refusal says PATHOGEN BREACH", "PATHOGEN BREACH" in message, message)
        check("mainnet stayed empty", len(m.read(m.MAINNET)) == 0)

        print("== a trial with no phantom proves nothing, so it cannot promote ==")
        fresh(tmp)
        m.mint("a candidate", OK_WITNESS, "OK_TOKEN")
        summary = m.trial()
        check("an untested barrier is not green", summary["status"] != "green",
              summary["status"])
        ok, message = m.promote()
        check("promotion refused", not ok)
        check("the refusal names the untested barrier",
              "unproven" in message or "no phantom" in message, message)

        print("== promotion without any trial is refused ==")
        fresh(tmp)
        ok, message = m.promote()
        check("refused with no trial", not ok)
        check("and says why", "no trial" in message, message)

        print("== a candidate whose witness fails stays red and does not promote ==")
        fresh(tmp)
        m.mint("a broken candidate", FAIL_WITNESS, "OK_TOKEN")
        m.mint("a phantom", FAIL_WITNESS, "NEVER_PRINTED", kind="phantom")
        summary = m.trial()
        check("trial is not green", summary["status"] != "green", summary["status"])
        ok, _ = m.promote()
        check("nothing promoted", not ok)

        print("== the ledger is hash-chained: a rewritten mint is caught ==")
        fresh(tmp)
        m.mint("a candidate", OK_WITNESS, "OK_TOKEN")
        ok, problems = m.verify()
        check("a clean chain verifies", ok, str(problems))
        lines = m.LEDGER.read_text().splitlines()
        entry = __import__("json").loads(lines[0])
        entry["claim"] = "a forged claim"
        lines[0] = __import__("json").dumps(entry, sort_keys=True)
        m.LEDGER.write_text("\n".join(lines) + "\n")
        ok, problems = m.verify()
        check("a forged claim breaks the chain", not ok, str(problems))

    print()
    if FAILS:
        print(f"MINT LEDGER TEST: FAIL ({len(FAILS)}): {FAILS}")
        return 1
    print("MINT LEDGER TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
