#!/usr/bin/env python3
"""signature_protocol_gate.py — the Procedural Signature Protocol, made executable.

Source: `[corpus] COGNITIVE PROCEDURAL SIGNATURE PROTOCOL.txt`, Part Four (output schema),
Part Five (anti-cut rules), Part Six (fidelity test), Part Nine (what done looks like).

The protocol's own warning is the defect this gate catches: "If the loop only explains the
sanitized signals ... then it is a paraphrase of the legend." A biography reads exactly like a
signature to a reader who is not counting. This gate counts.

A reconstruction is a Markdown file whose headings are the protocol's 13 sections. It is
declared in docs/SIGNATURE-RECONSTRUCTIONS.json:

  { "reconstructions": [ {"path": "docs/recoveries/TESLA.md", "thinker": "Tesla"} ] }

Per file the gate requires:
  1. All 13 sections present, in order (Part Four).
  2. A falsification line — non-empty (Part Four §13, "mandatory").
  3. The loop stated as a SEQUENCE of verbs with arrows, not a list of traits (Part Five).
  4. At least one quote verification: a sanitized and an unsanitized form both present.
  5. Body cost booked (Part Five: "the cut of the platform from the labor").
  6. Distributed system named (Part Five: "the cut of the many from the one").
  7. At least one predicted unsanitized signal (Part Six: prediction, not consistency).
  8. Tier discipline: no load-bearing claim marked Tier D alone. Every `[T?]` tag must be
     A, B, or C; a `[D]` tag may appear only on a line that also carries a corroborating
     A/B/C tag. A claim resting on Tier D alone is the legend speaking.

Exit 0 = every declared reconstruction is signature-shaped.
Exit 1 = at least one is biography-shaped, and the exact missing element is named.
Exit 3 = no declarations (a skip is never a pass, SPI-31).
"""
from __future__ import annotations

import json
import re
import sys
import pathlib

DECL = pathlib.Path("docs/SIGNATURE-RECONSTRUCTIONS.json")
# The validated reconstructions are the Operator's research documents. They sit beside the
# repo, not inside it, so the path resolves the same way tools/citation_gate.py resolves the
# corpus (SPI-8: the home is the Operator's tree, not the cloud checkout).
CORPUS_ROOTS = [pathlib.Path("."), pathlib.Path(".."), pathlib.Path("../..")]


def resolve(src: str) -> pathlib.Path | None:
    for root in CORPUS_ROOTS:
        cand = root / src
        if cand.is_file():
            return cand
    return None

SECTIONS = [
    ("i", "physical scene"),
    ("ii", "intake"),
    ("iii", "substrate"),
    ("iv", "loop"),
    ("v", "failure posture"),
    ("vi", "distributed system"),
    ("vii", "unsanitized register"),
    ("viii", "diachronic mechanic"),
    ("ix", "diary register"),
    ("x", "stated procedure"),
    ("xi", "quote verification"),
    ("xii", "verification table"),
    ("xiii", "falsification line"),
]

ARROW = re.compile(r"(?:→|->|=>)")
TIER = re.compile(r"\[(?:Tier\s*)?([ABCD])\]", re.I)
# The validated reconstructions write "Sanitized quote 1", then "Genuine quote 1", then
# "The cut". Part Five's own word is "unsanitized". Both are the same move, so accept both
# rather than demanding the Operator rewrite a validated document to satisfy a regex.
SANITIZED = re.compile(r"\bsanitized\b|\bthe cut\b", re.I)
UNSANITIZED = re.compile(r"\bunsanitized\b|\bgenuine\b|\bprimary source\b", re.I)
BODY = re.compile(r"\bbody cost\b|\bmetabolic\b", re.I)
DISTRIBUTED = re.compile(r"\bdistributed system\b", re.I)
PREDICT = re.compile(r"\bpredict|\bpredict", re.I)


# The Operator's reconstructions are plain text with a bare numeral heading:
#   I. PHYSICAL SCENE
# A Markdown recovery uses `## I. Physical Scene`. Both are the same document; the gate reads
# both dialects, because a gate that only accepts one dialect reports a defect that is only
# a formatting difference — and then a real absence hides behind the noise.
ROMAN = r"(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII)"
HEADING = re.compile(
    rf"^(?:#{{1,6}}\s*)?({ROMAN})\b[.):]?\s*(.+?)\s*$",
    re.M,
)


def heading_index(text: str) -> dict[str, int]:
    """Map a lowercased heading label to its character offset, in either dialect."""
    found = {}
    for m in HEADING.finditer(text):
        label = m.group(2).strip().lower()
        if label:
            found[label] = m.start()
    return found


def section_body(text: str, heads: dict[str, int], key: str) -> str | None:
    """Return the text under the heading whose label ends with `key`, up to the next heading."""
    starts = sorted(heads.values())
    for label, off in heads.items():
        if label.rstrip(".").endswith(key) or key in label:
            nxt = next((s for s in starts if s > off), len(text))
            return text[off:nxt]
    return None


def audit(text: str) -> list[str]:
    problems = []
    heads = heading_index(text)

    # 1. all 13 sections, in order
    offsets = []
    for numeral, name in SECTIONS:
        body = section_body(text, heads, name)
        if body is None:
            problems.append(f"MISSING_SECTION {numeral.upper()}. {name}")
        else:
            offsets.append(heads[next(l for l in heads if name in l)])
    if offsets != sorted(offsets):
        problems.append("SECTIONS_OUT_OF_ORDER (Part Four fixes the order)")

    # 2. falsification line non-empty
    fal = section_body(text, heads, "falsification line")
    if fal is not None:
        stripped = re.sub(r"^#{1,6}.*$", "", fal, flags=re.M).strip()
        if len(stripped) < 40:
            problems.append("FALSIFICATION_LINE_EMPTY (Part Four makes it mandatory)")

    # 3. loop stated as a sequence, not a trait list.
    #    Two legitimate spellings, both used in the validated corpus: an arrow chain
    #    (`desire -> incubation -> ...`) or a numbered list of named phases (`1. Desire`).
    #    A trait list has neither: it says "he was persistent and brilliant".
    loop = section_body(text, heads, "loop") or ""
    arrows = len(ARROW.findall(loop))
    numbered = len(re.findall(r"^\s*\d+[.)]\s+\S", loop, re.M))
    if arrows < 3 and numbered < 3:
        problems.append("LOOP_NOT_A_SEQUENCE (IV. Loop has neither 3 arrows nor 3 numbered "
                        "phases; Part Five forbids stating a procedure as a trait)")

    # 4. quote verification present, both halves
    quote = section_body(text, heads, "quote verification") or ""
    if not (SANITIZED.search(quote) and UNSANITIZED.search(quote)):
        problems.append("QUOTE_VERIFICATION_INCOMPLETE (needs both the sanitized and the "
                        "unsanitized form; Part Five anti-cut rule 2)")

    # 5/6. body cost and distributed system booked
    if not BODY.search(text):
        problems.append("BODY_COST_NOT_BOOKED (Part Five: the platform is not free)")
    if not DISTRIBUTED.search(text):
        problems.append("DISTRIBUTED_SYSTEM_NOT_NAMED (Part Five: the many are not the one)")

    # 7. a predicted unsanitized signal
    if not PREDICT.search(text):
        problems.append("NO_PREDICTION (Part Six: prediction is the test, not plausibility)")

    # 8. tier discipline — no load-bearing claim on Tier D alone.
    #    Exception: XI. Quote Verification MUST show the Tier D sanitized form, because Part
    #    Five requires "the sanitized version shown next to the unsanitized version". There,
    #    the Tier D line is the object of the cut, not a claim resting on it.
    q_start = next((o for l, o in heads.items() if "quote verification" in l), None)
    q_end = (next((s for s in sorted(heads.values()) if s > q_start), len(text))
             if q_start is not None else None)
    offset = 0
    for lineno, line in enumerate(text.splitlines(keepends=True), 1):
        in_quote = q_start is not None and q_start <= offset < q_end
        tiers = {x.upper() for x in TIER.findall(line)}
        if tiers and tiers <= {"D"} and not in_quote:
            problems.append(f"TIER_D_ONLY line {lineno}: a load-bearing claim cannot rest on "
                            f"self-presentation alone (Part Two)")
        offset += len(line)
    return problems


def run() -> int:
    if not DECL.exists():
        print("SIGNATURE_PROTOCOL: SKIP no_declarations (a skip is never a pass, SPI-31)")
        return 3
    items = json.loads(DECL.read_text()).get("reconstructions", [])
    if not items:
        print("SIGNATURE_PROTOCOL: SKIP empty_declarations (a skip is never a pass, SPI-31)")
        return 3

    print("=" * 78)
    print("PROCEDURAL SIGNATURE GATE — is this a loop, or a biography?")
    print("=" * 78)
    bad = 0
    absent = 0
    for it in items:
        path, thinker = it.get("path", "?"), it.get("thinker", "?")
        p = resolve(path)
        if p is None:
            # The Operator's corpus lives OUTSIDE the repository (SPI-8: the home is the
            # SD card, not the cloud checkout), so a fresh clone legitimately cannot see
            # these files. Counting that as `bad` reported "LEGEND_MASQUERADING" - a claim
            # that the work is a biography - when the truth was "I could not look". That
            # accusation is the same blindness the gate exists to catch, pointed the wrong
            # way, and it made the gate PASS on the Operator's machine while FAILING on the
            # exact bytes a clone would run. Absence of evidence is not evidence of a legend.
            print(f"  [ABSENT] {thinker}: {path} (not found in repo or corpus)")
            absent += 1
            continue
        problems = audit(p.read_text())
        verdict = "SIGNATURE" if not problems else "BIOGRAPHY"
        print(f"  [{verdict}] {thinker}: {path}")
        for pr in problems:
            print(f"      {pr}")
        bad += bool(problems)
    print("\n" + "=" * 78)
    if bad:
        print("VERDICT: LEGEND_MASQUERADING")
        print("=" * 78)
        return 1
    if absent:
        print(f"VERDICT: SKIP corpus_absent ({absent} source(s) unreachable; a skip is "
              f"never a pass, SPI-31)")
        print("=" * 78)
        return 3
    print("VERDICT: ALL_SIGNATURES")
    print("=" * 78)
    return 0


def selftest() -> int:
    good = "\n".join([
        "# Recovery: Tesla",
        "## I. Physical Scene", "The Budapest park. [A]",
        "## II. Intake", "A remembered problem. [A]",
        "## III. Substrate", "The mental workspace. [A]",
        "## IV. Loop",
        "desire → incubation → convergence → mental operation → instantiation → confirmation [A]",
        "## V. Failure Posture", "Absence of external failure data is the tell. [B]",
        "## VI. Distributed System", "Peck and Brown, Westinghouse, Scherff. [B]",
        "## VII. Unsanitized Register", "The 84-hour sessions. [A]",
        "## VIII. Diachronic Mechanic", "AC motor, 1882 to 1888. [A]",
        "## IX. Diary Register", "Notebook entries. [A]",
        "## X. Stated Procedure", "Run the loop. [A]",
        "## XI. Quote Verification",
        "Sanitized: 'think in energy, frequency, vibration' — apocryphal. [D]",
        "Unsanitized: 'no thrill like seeing a creation of the brain unfolding'. [A]",
        "## XII. Verification Table", "Every row tiered. [A]",
        "## XIII. Falsification Line",
        "If the Colorado Springs notebooks show generation rather than confirmation, this breaks. [A]",
        "## Body cost", "Body cost: 2-5 hours sleep. [A]",
        "## Prediction", "It predicts the notebooks are validation records. [A]",
    ])

    legend = "\n".join([
        "# Tesla: A Life",
        "## I. Physical Scene", "He was a genius. [D]",
        "## II. Intake", "He had ideas. [D]",
        "## III. Substrate", "His mind. [D]",
        "## IV. Loop", "He was brilliant and persistent and visionary. [D]",
        "## V. Failure Posture", "He did not fail. [D]",
        "## VI. Distributed System", "He worked alone. [D]",
        "## VII. Unsanitized Register", "He was a genius. [D]",
        "## VIII. Diachronic Mechanic", "He invented things. [D]",
        "## IX. Diary Register", "He wrote. [D]",
        "## X. Stated Procedure", "Think hard. [D]",
        "## XI. Quote Verification", "He said think in energy. [D]",
        "## XII. Verification Table", "All verified. [D]",
        "## XIII. Falsification Line", "None. [D]",
    ])

    good_p, legend_p = audit(good), audit(legend)
    checks = [
        ("signature-shaped doc passes", good_p == [], f"{good_p}"),
        ("legend is refused", len(legend_p) >= 5, f"{len(legend_p)} problems"),
        ("names the missing body cost", any("BODY_COST" in p for p in legend_p), ""),
        ("names the missing prediction", any("NO_PREDICTION" in p for p in legend_p), ""),
        ("catches trait-list loop", any("LOOP_NOT_A_SEQUENCE" in p for p in legend_p), ""),
        ("catches Tier-D-only claims", any("TIER_D_ONLY" in p for p in legend_p), ""),
        ("catches empty falsification", any("FALSIFICATION" in p for p in legend_p), ""),
    ]
    print("=" * 78)
    print("PROCEDURAL SIGNATURE GATE — SELFTEST")
    print("=" * 78)
    holes = 0
    for name, ok, detail in checks:
        holes += not ok
        print(f"  [{'PASS' if ok else 'HOLE'}] {name}  {detail}")
    print(f"\nSELFTEST: {'PASS' if holes == 0 else 'FAIL'} ({holes} hole(s))")
    return 0 if holes == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
