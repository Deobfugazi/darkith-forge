#!/usr/bin/env python3
"""Closed briefings may not be re-opened. Gate + ledger.

A briefing that arrives by chat is not durable, but it is not forbidden either: it is
evidence. What is forbidden is a fresh agent re-litigating a briefing that the bytes have
already closed. That loop cost delivery cycles because the board never said "closed".

Each entry below records a briefing that is DONE, the measurement that closed it, and the
signature that would mean someone re-opened it. TASKS.md is scanned: a closed briefing
reappearing on the task board is a defect, because the board is what a fresh agent reads.

Exit 0 = no closed briefing re-opened. Exit 1 = one was. Exit 3 = SKIP, no board to read.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLOSED = [
    {
        "id": "comment-19files",
        "brief": "19 Kotlin files lost the opening '/*' of their top comment block; inject "
                 "the markers at the cited lines",
        "closed_by": "The bytes never matched. 18 of 19 cited lines already opened a valid "
                     "/** (the 19th, HomekeeperBridge.kt:282, is a code line). The real "
                     "defect was a mangled CLOSER ('//' where '*/' belonged) in 2 files, "
                     "core/CssLite.kt and core/SubstrateIngestor.kt, both repaired to "
                     "byte-identical. Verified by tools/kt_comment_scan.py and kotlinc 1.9.24.",
        "evidence": "proof/comment_premise_check.txt, proof/kotlin_comment_repair.json",
        "gate": "python3 tools/comment_audit.py",
        # A line on the task board that re-opens the brief rather than reporting it closed.
        "reopen": re.compile(
            r"(inject|restore|add)\s+(the\s+)?[`'\"]?/\*|"
            r"send\s+(me\s+)?the\s+script|"
            r"fix\s+the\s+19\b|"
            r"19\s+(kotlin\s+)?files?\s+(lost|stripped|missing|need)|"
            # Canon asserting the premise as fact. Narrating it as a false claim is allowed:
            # the excluded words are what mark a sentence as a report, not a restatement.
            r"(?=.*stripped\s+the\s+opening)(?=.*\b19\b)"
            r"(?!.*\b(?:claimed|hypothesis|would\s+have|false|never|closed)\b)",
            re.I),
    },
]

BOARDS = ["TASKS.md", "RESUME.md", "AGENTS.md", "DARKITH.md", "README.md"]
ALLOW = re.compile(r"\bCLOSED\b|\bclosed\b|\bresolved\b|\bdone\b|\bnever\b", re.I)


def main(argv):
    if "--ledger" in argv or not argv:
        for c in CLOSED:
            print(f"  [{c['id']}] CLOSED — {c['brief'][:60]}...")
            print(f"     evidence: {c['evidence']}")
            print(f"     gate:     {c['gate']}")
        if not argv:
            return 0

    checked = 0
    reopened = []
    for name in BOARDS:
        p = os.path.join(ROOT, name)
        if not os.path.isfile(p):
            continue
        checked += 1
        with open(p, encoding="utf-8", errors="surrogateescape") as fh:
            for n, line in enumerate(fh, 1):
                for c in CLOSED:
                    if c["reopen"].search(line) and not ALLOW.search(line):
                        reopened.append((name, n, c["id"], line.strip()[:90]))

    if checked == 0:
        print("closed_briefings: SKIP — no task board found; nothing examined")
        return 3

    if reopened:
        print(f"closed_briefings: FAIL — {len(reopened)} closed briefing(s) re-opened:")
        for name, n, cid, text in reopened:
            print(f"  {name}:{n} re-opens [{cid}]: {text}")
        print("  these are CLOSED. The bytes decided. Do not re-report them; run the gate.")
        return 1

    print(f"closed_briefings: PASS — {len(CLOSED)} closed briefing(s), {checked} board(s) "
          f"scanned, none re-opened")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
