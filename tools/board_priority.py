#!/usr/bin/env python3
"""Board priority: turn an unordered defect list into a sequenced, MUST-bound checklist.

The board used to print tasks in discovery order, each as a bare bullet. Discovery
order is an accident of which probe happened to run first; it says nothing about what
must be fixed before what. A flat list also hides the thing the Operator needs most:
what each unchecked box can destroy if it is skipped.

This module supplies three facts per task, all derived from evidence already in the
cycle receipts, so nothing here is a second opinion about severity:

  severity   from the governing layer (S05/S07). Law and apparatus outrank product.
  rank       severity, then blast radius (how many probes name the same root cause).
  never      the failure modes that make skipping this task destructive or
             substandard, each named as a sacred NEVER with its consequence.

The board renders the result as `- [ ]` checkboxes. An unchecked box is a MUST: it is
open work, and it is unapproved to close until its own probe returns PASS.
"""
import pathlib

# ---------------------------------------------------------------------------
# Severity: derived from layer, not from taste.
#
# The ordering follows blast radius. A defect in law or in a gate does not break one
# feature, it breaks the ability to know whether ANY feature works, so it outranks
# product code. Generated tissue outranks nothing: it is rebuilt from source.
# ---------------------------------------------------------------------------
SEVERITY_BY_LAYER = {
    "L6": ("CRITICAL", 0, "law/board — a wrong law misdirects every later fix"),
    "L1": ("HIGH", 1, "apparatus — a broken gate makes every green line a guess"),
    "L2": ("MEDIUM", 2, "product source — the app's own Kotlin"),
    "L3": ("MEDIUM", 2, "product surface — the offline studio the Operator touches"),
    "L5": ("MEDIUM", 2, "evidence — proof that the other layers hold"),
    "L4": ("LOW", 3, "generated tissue — rebuilt from source, never hand-edited"),
}

# A task whose repair can sign, publish, install, or seal is destructive-capable:
# getting it wrong does not leave a bug, it leaves a wrong artefact in the world.
DESTRUCTIVE_CAPABLE = (
    "delivery", "apksign", "apksigner", "sign", "install", "publish", "push",
    "seal", "release", "fork_integrity", "dex_link",
)

# ---------------------------------------------------------------------------
# The failure-mode taxonomy.
#
# DESTRUCTIVE = corrupting. It does not degrade the tree, it poisons it: the damage is
#   silent, it propagates into artefacts other people consume, and it survives repair
#   because nothing downstream knows it is there.
# DEFICIENCY  = substandard. The tree is weaker than it claims but still honest: the
#   gap is visible to a gate, so it can be seen and closed.
#
# Each entry is (code, NEVER title, consequence). Codes are stable so the board can be
# diffed across cycles.
# ---------------------------------------------------------------------------
TAXONOMY = {
    "green-without-proof": (
        "DESTRUCTIVE",
        "NEVER #13 — NO UNPROVEN CURRENCY",
        "a tree marked current without a clean compile of THAT tree ships code nobody "
        "compiled; the failure surfaces on the Operator's phone, not in CI",
    ),
    "second-copy": (
        "DESTRUCTIVE",
        "NEVER #11 — ONE TREE",
        "two divergent live copies mean the fix lands in the copy that is not shipped, "
        "and the shipped copy keeps the defect; every later patch is a coin flip",
    ),
    "silent-skip": (
        "DESTRUCTIVE",
        "NEVER #13 / SPI-15 — SKIP IS NEVER PASS",
        "a skip reported as a pass turns an unverified path into a claimed-green one, "
        "and the whole suite's meaning collapses",
    ),
    "unpushed": (
        "DESTRUCTIVE",
        "NEVER #21 — NO WAITING FOR APPROVAL THAT ALREADY EXISTS",
        "unpushed work is invisible to CI and to every other worker; a sandbox reset "
        "deletes it, and the loss is total and silent",
    ),
    "phantom-fail": (
        "DESTRUCTIVE",
        "NEVER #19 — NO UNEXAMINED SOURCE",
        "a gate that fails without executing manufactures a defect with no root cause; "
        "the repair is unwritable, so the board can never close",
    ),
    "law-not-gate": (
        "DESTRUCTIVE",
        "NEVER #17 — NO STALLED DEFICIENCY",
        "a law with no gate is a note; the same defect returns on the next cycle and "
        "the previous cycle's evidence becomes a lie by omission",
    ),
    "unexamined-source": (
        "DESTRUCTIVE",
        "NEVER #19 — NO UNEXAMINED SOURCE",
        "shipping a source tree that has not passed its own trial puts an unexamined "
        "artefact in front of a user who cannot examine it either",
    ),
    "scattered-delivery": (
        "DESTRUCTIVE",
        "NEVER #15 — ONE SURFACE",
        "delivery split across links means the Operator cannot tell which one is "
        "current, and a dead link reads as a lost delivery",
    ),
    "two-documents": (
        "DESTRUCTIVE",
        "NEVER #16 — ONE DOCUMENT",
        "two canonical records drift; whichever the reader opens is the one that is "
        "wrong, and there is no way to know which",
    ),
    "stale-seal": (
        "DEFICIENCY",
        "NEVER #17 — NO STALLED DEFICIENCY",
        "a seal that no longer matches its tree attests a state that stopped holding; "
        "the evidence is real but it is evidence of the past",
    ),
    "stale-index": (
        "DEFICIENCY",
        "SPI-2 — READ THE EXACT BYTES",
        "an index describing yesterday's files sends the next reader to a path that "
        "moved; nothing is corrupted, but nothing is findable either",
    ),
    "unregistered-defect": (
        "DEFICIENCY",
        "MUST #32 — HOMEOKINESIS, NOT HOMEOSTASIS",
        "a defect class with no registry entry is debt that cannot ratchet down, so "
        "the same failure recurs and is re-diagnosed from zero",
    ),
    "unindexed-doc": (
        "DEFICIENCY",
        "SPI-2 — READ THE EXACT BYTES",
        "a document outside the index is invisible to every search that trusts the "
        "index, which is all of them",
    ),
    "stale-payload": (
        "DEFICIENCY",
        "NEVER #12 — NO FOREIGN SYMBOL",
        "a stale one-shot payload ships yesterday's tree under today's name; the "
        "Operator installs it and reports a bug that was already fixed",
    ),
}

# ---------------------------------------------------------------------------
# Binding: which failure modes each probe class can actually cause.
#
# A task inherits only the NEVERs its own repair can violate. Attaching the whole
# taxonomy to every task is how a warning list becomes wallpaper.
# ---------------------------------------------------------------------------
BINDINGS = {
    "delivery gate (source laws)": ["unexamined-source", "green-without-proof", "scattered-delivery"],
    "autophagy (defect-class registry)": ["unregistered-defect", "law-not-gate"],
    "autophagy (defect classes are impossible, not absent)": ["unregistered-defect", "law-not-gate"],
    "one-shot installer": ["stale-payload", "second-copy"],
    "board pulse (real-time push)": ["unpushed", "green-without-proof"],
    "authority gate (NEVER #21)": ["unpushed"],
    "knowledge-base index + dedup": ["stale-index", "unindexed-doc"],
    "revitalization chain gate": ["stale-seal", "law-not-gate", "silent-skip"],
    "kotlin syntax gate": ["green-without-proof", "unexamined-source"],
    "kotlin comment scan": ["green-without-proof"],
    "§19 fork integrity gate (compile proof)": ["green-without-proof", "second-copy"],
    "dex link gate (no unresolved classes)": ["green-without-proof"],
    "doc consolidation check": ["two-documents", "scattered-delivery"],
    "bridge contract audit": ["second-copy", "green-without-proof"],
}

# Applied when a probe has no explicit binding: the two laws any repair can break.
DEFAULT_BINDING = ["green-without-proof", "silent-skip"]

# ---------------------------------------------------------------------------
# The closing row. Every board ends with the staging trial, because a fix that has not
# been stressed has not been shown to hold — detection is not verification (I4).
# ---------------------------------------------------------------------------
STAGING_TRIAL = {
    "id": "STAGING-TRIAL",
    "title": "staging trial: full pre-run stress, then CI",
    "severity": "CRITICAL",
    "rank": 9,
    "always_last": True,
    "acceptance": [
        "every open MUST above is checked, or explicitly descoped in writing",
        "bash tools/tests/run.sh — all suites PASS, no suite skipped",
        "bash tools/ci.sh — exit 0, every gate PASS, no gate SKIP",
        "the stress run is logged to proof/ and the log path is cited here",
    ],
    "never": [
        TAXONOMY["green-without-proof"],
        TAXONOMY["silent-skip"],
        TAXONOMY["unpushed"],
    ],
}


def layer_of(task):
    """The governing layer a task's repair lives in, or None when it is unlocated."""
    for candidate in ("layer", "governing_layer"):
        value = task.get(candidate)
        if isinstance(value, str) and value in SEVERITY_BY_LAYER:
            return value
    gov = (task.get("governing_file") or "").lower()
    if not gov or gov == "unconfirmed":
        return None
    # Generated tissue is checked first: it lives inside build/ and tools/, so a
    # path-prefix test would call it apparatus (HIGH) when it is rebuildable (LOW).
    if any(seg in gov for seg in ("build/gen/", "tools/generated/", "/generated/")):
        return "L4"
    if any(gov.startswith(p) or f"/{p}" in gov
           for p in ("darkith.md", "agents.md", "tasks.md")):
        return "L6"
    if any(t in gov for t in ("tools/", "build/", "kit/")):
        return "L1"
    if "omega-app" in gov:
        return "L3"
    if gov.endswith(".kt"):
        return "L2"
    if gov.startswith("proof/"):
        return "L5"
    return "L1"


def severity_of(task) -> tuple:
    """(label, rank, why) for a task. Destructive-capable repairs are never below HIGH."""
    layer = layer_of(task)
    if layer is None:
        # An unlocated defect is not "probably fine": nothing bounds where it lives, so
        # it is held at law level until S07 traces it. The reason says that, rather than
        # borrowing the law layer's reason, which would be a false claim about the file.
        label, rank, why = ("CRITICAL", 0,
                            "root cause unconfirmed — nothing bounds the blast radius "
                            "until S07 traces it, so it is held at law level")
    else:
        label, rank, why = SEVERITY_BY_LAYER[layer]
    haystack = " ".join([
        str(task.get("governing_file") or ""),
        str(task.get("repair_boundary") or ""),
        " ".join(task.get("probes") or []),
        " ".join(task.get("probe_commands") and
                 [c.get("cmd", "") for c in task["probe_commands"]] or []),
    ]).lower()
    if any(word in haystack for word in DESTRUCTIVE_CAPABLE):
        if rank > 1:
            return ("HIGH", 1, "repair is destructive-capable (signs, publishes, "
                               "installs, or seals) — a wrong result leaves the tree")
        return (label, rank, why)
    return (label, rank, why)


def blast_radius(task) -> int:
    """How many probes name the same root cause. Wider blast sorts first."""
    return len(task.get("probes") or [])


def failure_modes(task) -> list:
    """The NEVERs this specific task can violate, deduplicated, destructive first."""
    codes = []
    for probe in task.get("probes") or []:
        codes.extend(BINDINGS.get(probe, []))
    if not codes:
        codes = list(DEFAULT_BINDING)
    # A repair that touches signing or delivery is destructive-capable whatever its
    # probe was called; the taxonomy must reflect that, not the label.
    if severity_of(task)[1] <= 1 and "unpushed" not in codes:
        codes.append("unpushed")
    seen, ordered = set(), []
    for code in codes:
        if code in seen or code not in TAXONOMY:
            continue
        seen.add(code)
        ordered.append(TAXONOMY[code])
    # Destructive before deficiency: the corrupting failure outranks the weaker one.
    ordered.sort(key=lambda entry: 0 if entry[0] == "DESTRUCTIVE" else 1)
    return ordered


def sequence(tasks) -> list:
    """Order tasks for execution: severity, then blast radius, then discovery order.

    Deterministic: equal rank and radius keep their original relative order, so two
    runs over the same defects produce the same board and the diff stays readable.
    """
    decorated = []
    for index, task in enumerate(tasks):
        label, rank, why = severity_of(task)
        decorated.append((rank, -blast_radius(task), index, label, why, task))
    decorated.sort(key=lambda row: (row[0], row[1], row[2]))
    return [{"task": row[5], "severity": row[3], "rank": row[0], "why": row[4],
             "never": failure_modes(row[5])} for row in decorated]


def render(sequenced, closed: bool, skip_note: str = "") -> list:
    """Render the ordered checklist. Unchecked box = MUST = open work."""
    box = "[x]" if closed else "[ ]"
    lines = []
    if not sequenced:
        lines.append(f"- {box} **no open step** — every probe this cycle returned PASS")
    for position, row in enumerate(sequenced, 1):
        task = row["task"]
        lines.append(
            f"- {box} **STEP {position}** — {row['severity']} — "
            f"`{task['id']}` {', '.join(task.get('probes') or [])}")
        lines.append(f"  - why this rank: {row['why']}")
        lines.append(f"  - root cause: `{task.get('root_cause', 'UNCONFIRMED')}`; "
                     f"governing `{task.get('governing_file', 'UNCONFIRMED')}`")
        for criterion in task.get("acceptance_criteria") or []:
            lines.append(f"  - accepts when: {criterion}")
        if row["never"]:
            lines.append("  - sacred NEVERs — what skipping this can do:")
            for kind, title, consequence in row["never"]:
                lines.append(f"    - **{kind}** — {title}: {consequence}")
    lines.append(f"- {box} **STEP {len(sequenced) + 1}** — "
                 f"{STAGING_TRIAL['severity']} — {STAGING_TRIAL['title']}")
    lines.append("  - why this rank: nothing ships before it is stressed; "
                 "detection is not verification (I4)")
    for criterion in STAGING_TRIAL["acceptance"]:
        lines.append(f"  - accepts when: {criterion}")
    lines.append("  - sacred NEVERs — what skipping this can do:")
    for kind, title, consequence in STAGING_TRIAL["never"]:
        lines.append(f"    - **{kind}** — {title}: {consequence}")
    if skip_note:
        lines.append("")
        lines.append(skip_note)
    return lines


if __name__ == "__main__":
    import json
    import sys
    payload = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {"tasks": []}
    for row in sequence(payload.get("tasks", [])):
        print(row["severity"], row["task"]["id"], len(row["never"]))
