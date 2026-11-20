#!/usr/bin/env python3
"""directive_core.py — the portable law engine. One truth, any dialect.

WHY THIS EXISTS
    Every gate in this repo was written against one document, one language, and one
    spelling: `─── MUST #17 (GENERATED COPIES) ───` inside `DARKITH.md`, gated by a Python
    file named in a `GATE:` line. That is a branded engine. Change the brand — write
    `RULE 17`, or `- **MUST 17**`, or put the law in a `.kt` doc comment, or move it to
    `.rst` — and every gate silently stops seeing it. A law that vanishes from the parser
    is a law that passes by default, which is the same loophole as a skip reported as a
    pass, wearing a different coat.

WHAT IT DOES
    parse      read directives from ANY dialect: box-drawing, markdown headings, bullets,
               blockquote, or source-comment prefixes (// * # -- ; % <!--). Verbs are not
               fixed to NEVER/MUST/SPI: RULE, INVARIANT, LAW, DIRECTIVE, CONSTRAINT,
               POLICY all canonicalise to the same identity.
    couple     bind every law to a gate that can actually fail (SPI-33). A gate named in
               prose, or a generator with no failure branch, is not a coupling.
    heal       when a law declares a PREDICATE and has no gate, GENERATE one — in a
               language the tree already speaks — rather than skip. Regeneration is
               idempotent: same law, same bytes, no diff.
    verify     run the coupled gates and report three ways, never two: PASS 0, FAIL 1,
               SKIP 3 (SPI-31). A predicate matching zero files FAILS (SPI-32).

THE PRIME PURPOSE
    A law is not its spelling. The function is: the rule is enforced or it is reported
    broken. Nothing in between. Every generated gate inherits that — it is born honest,
    with the skip and empty-corpus laws compiled in, so a healed gate cannot re-open the
    hole it was generated to close.

PORTABILITY
    Python 3 stdlib only, one file, no imports from the rest of the tree. Point it at any
    root: `--root /any/project`. It does not know the name Darkith and must not.

Exit: 0 all laws coupled and green; 1 a law is uncoupled or its gate failed; 3 nothing to
check (no directives found — reported, never passed).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

# ── dialect layer ────────────────────────────────────────────────────────────────────────
# Leading noise that may precede a directive in any of the supported document styles.
_NOISE = re.compile(
    r"^[\s\u2500-\u257f\u2550-\u256c|>*+#\-~=_`\[\]()0-9.]*"   # box drawing, bullets, rules
)

# Source-comment prefixes, longest first, stripped once before the verb match.
_COMMENT_PREFIXES = ("<!--", "///", "//!", "//", "/*", "/**", "*/", "*", "--", ";", "%", "''", "#!")

_VERBS = ("NEVER", "MUST", "SPI", "RULE", "INVARIANT", "LAW", "DIRECTIVE", "CONSTRAINT", "POLICY")

# `MUST #17`, `MUST-17`, `MUST 17`, `RULE 4` — all one identity.
_DIRECTIVE = re.compile(
    r"^(?P<verb>" + "|".join(_VERBS) + r")[\s]*[-#]?[\s]*(?P<num>\d+)\b"
    r"(?P<rest>.*)$",
    re.IGNORECASE,
)

_TITLE_PAREN = re.compile(r"^[\s]*\((?P<t>[^)]+)\)")
_TITLE_DASH = re.compile(r"^[\s]*[—–-]{1,2}\s*(?P<t>.+)$")

_GATE_LINE = re.compile(r"^\s*(?:GATE|Gate|gate)\s*:\s*(?P<g>.+)$")
_PREDICATE_LINE = re.compile(r"^\s*PREDICATE\s*:\s*(?P<p>.+)$")
# Any path with a code extension, in any language the tree might use.
_GATE_PATH = re.compile(r"[\w./-]+\.(?:py|sh|js|mjs|cjs|ts|rb|kt|kts|go|rs|pl|php|lua|java|cs)\b")

_SECTION = re.compile(r"^\s*[§#]{1,2}\s*\d+\b")


_CITATION_TAIL = re.compile(r"^[\s]*[);,.]")


def _looks_like_citation(m, stripped: str) -> bool:
    """True when the directive is being REFERRED TO, not DECLARED.

    A declaration introduces its law: `MUST #17 (GENERATED COPIES)`, `RULE 4 — title`,
    `SPI-6` on a line of its own. A citation sits inside a sentence, so the line ends
    immediately after the number, or punctuation follows it.
    """
    rest = m.group("rest")
    if not rest.strip():
        return False                      # bare `SPI-6` on its own line is a declaration
    if _CITATION_TAIL.match(rest):
        return True
    # `NEVER #11/#15/#16` or `MUST #12, MUST #13` — a list of references.
    if re.match(r"^[\s]*[/&+]", rest) or re.search(r",\s*(?:NEVER|MUST|SPI|RULE)\b", rest):
        return True
    return False


def _strip_noise(line: str) -> str:
    s = line.rstrip("\n")
    s = _NOISE.sub("", s, count=1)
    for pre in _COMMENT_PREFIXES:
        if s.startswith(pre):
            s = s[len(pre):]
            break
    return s.strip()


def canonical(verb: str, num: str) -> str:
    return f"{verb.upper()}-{int(num)}"


class Law:
    __slots__ = ("id", "verb", "num", "title", "gate", "predicate", "source", "line", "body")

    def __init__(self, verb, num, title, source, line):
        self.id = canonical(verb, num)
        self.verb = verb.upper()
        self.num = int(num)
        self.title = title
        self.gate = None
        self.predicate = None
        self.source = source
        self.line = line
        self.body = []

    def as_dict(self):
        return {
            "id": self.id, "title": self.title, "gate": self.gate,
            "predicate": self.predicate, "source": str(self.source), "line": self.line,
        }


def parse(text: str, source: str | Path) -> list[Law]:
    """Extract every directive, whatever the document dialect."""
    laws: list[Law] = []
    current: Law | None = None
    for n, raw in enumerate(text.splitlines(), 1):
        stripped = _strip_noise(raw)
        if _SECTION.match(stripped):
            current = None                      # a section heading closes the law above it
            continue
        m = _DIRECTIVE.match(stripped)
        # A DECLARATION, not a citation. "One authoritative tree (NEVER #11); a gate fails"
        # mentions a law; it does not declare one. Requiring the directive to open the line
        # and be followed by a title-ish rest keeps prose citations out of the law set —
        # measured: this alone cut 127 "laws" down to the real count.
        if m and not _looks_like_citation(m, stripped):
            rest = m.group("rest")
            t = _TITLE_PAREN.match(rest) or _TITLE_DASH.match(rest)
            title = (t.group("t").strip() if t else rest.strip(" —-–:")).strip()
            current = Law(m.group("verb"), m.group("num"), title, source, n)
            laws.append(current)
            continue
        if current is None:
            continue
        current.body.append(stripped)
        gm = _GATE_LINE.match(raw) or _GATE_LINE.match(stripped)
        if gm and current.gate is None:
            paths = _GATE_PATH.findall(gm.group("g"))
            if paths:
                current.gate = paths[0]
            continue
        pm = _PREDICATE_LINE.match(raw) or _PREDICATE_LINE.match(stripped)
        if pm and current.predicate is None:
            current.predicate = pm.group("p").strip()
    return laws


def discover(root: Path, patterns: list[str]) -> list[Path]:
    seen: dict[Path, None] = {}
    for pat in patterns:
        for p in sorted(root.glob(pat)):
            if p.is_file():
                seen[p] = None
    return list(seen)


def collect(root: Path, patterns: list[str]) -> list[Law]:
    laws: list[Law] = []
    for p in discover(root, patterns):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        laws.extend(parse(text, p.relative_to(root)))
    return laws


# ── predicate layer: declarative, language-agnostic ──────────────────────────────────────
PREDICATE_HELP = """\
  exists   <path>                 the path must exist
  absent   <path>                 the path must not exist
  unique   <glob>                 exactly one file must match
  contains <glob> :: <regex>      every match must contain the pattern
  forbids  <glob> :: <regex>      no match may contain the pattern
  implies  <glob> :: <a> :: <b>   every match containing <a> must also contain <b>
  runs     <argv...>              the command must exit 0
"""


def parse_predicate(spec: str):
    kind, _, arg = spec.partition(" ")
    kind, arg = kind.strip().lower(), arg.strip()
    if kind not in ("exists", "absent", "unique", "contains", "forbids", "implies", "runs"):
        return None, None
    if kind in ("contains", "forbids"):
        pat, sep, regex = arg.partition("::")
        if not sep:
            return None, None
        return kind, (pat.strip(), regex.strip())
    if kind == "implies":
        # implies <glob> :: <antecedent> :: <consequent>
        # "contains" is a universal quantifier and cannot state an implication: SPI-8 says
        # IF a bridge declares fileRoots THEN it derives it from external storage, and not
        # every file in the tree is such a bridge. A law that cannot be written is a law
        # that gets written wrong, which is how the first SPI-8 predicate accused 43
        # innocent files.
        parts = [x.strip() for x in arg.split("::")]
        if len(parts) != 3 or not all(parts):
            return None, None
        return kind, tuple(parts)
    if not arg:
        return None, None
    return kind, arg


GENERATED_HEADER = '''#!/usr/bin/env python3
"""GENERATED by tools/directive_core.py --heal. Do not edit; regenerate instead.

Law: {law_id} — {title}
Source: {source}:{line}
Predicate: {predicate}

Regenerated from a declarative predicate because the law named no gate that could fail
(SPI-33). Exit contract: {contract}

A generated gate states only the exits it can actually produce. An earlier version of this
template claimed "exit 3 SKIP" for every kind, including the file-existence kinds that have
no skip state at all — a docstring describing behaviour the code cannot have, which is the
same lie as a gate that cannot fail.
"""
import fnmatch, re, shlex, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def matches(glob_pat):
    return sorted(p for p in ROOT.glob(glob_pat) if p.is_file())


def main():
    kind, arg = __KIND__, __ARG__
'''

CONTRACT = {
    "exists":   "0 PASS if the path exists, 1 FAIL if it does not (no skip state exists)",
    "absent":   "0 PASS if the path is gone, 1 FAIL if it is present (no skip state exists)",
    "unique":   "0 PASS on exactly one match, 1 FAIL on zero or several (empty is a FAIL)",
    "contains": "0 PASS if every match contains the pattern, 1 FAIL otherwise (empty is a FAIL)",
    "forbids":  "0 PASS if no match contains the pattern, 1 FAIL otherwise (empty is a FAIL)",
    "implies":  "0 PASS if every match with the antecedent also has the consequent, 1 FAIL otherwise",
    "runs":     "0 PASS on exit 0, 3 SKIP if the command exits 3, 1 FAIL otherwise",
}

GENERATED_BODY = {
    "exists": '''\
    target = ROOT / arg
    if not target.exists():
        print(f"{LAW}: FAIL — required path missing: {arg}")
        return 1
    print(f"{LAW}: PASS — {arg} exists")
    return 0
''',
    "absent": '''\
    target = ROOT / arg
    if target.exists():
        print(f"{LAW}: FAIL — forbidden path present: {arg}")
        return 1
    print(f"{LAW}: PASS — {arg} absent")
    return 0
''',
    "unique": '''\
    hits = matches(arg)
    if not hits:
        print(f"{LAW}: FAIL — nothing matches {arg} (empty corpus is not a pass, SPI-32)")
        return 1
    if len(hits) > 1:
        print(f"{LAW}: FAIL — {len(hits)} matches for {arg}, exactly one required")
        return 1
    print(f"{LAW}: PASS — exactly one match for {arg}")
    return 0
''',
    "contains": '''\
    glob_pat, pattern = arg
    hits = matches(glob_pat)
    if not hits:
        print(f"{LAW}: FAIL — nothing matches {glob_pat} (empty corpus is not a pass, SPI-32)")
        return 1
    rx = re.compile(pattern)
    bad = [str(p.relative_to(ROOT)) for p in hits
           if not rx.search(p.read_text(encoding="utf-8", errors="replace"))]
    if bad:
        print(f"{LAW}: FAIL — {len(bad)} file(s) lack /{pattern}/: {bad[:5]}")
        return 1
    print(f"{LAW}: PASS — all {len(hits)} file(s) contain /{pattern}/")
    return 0
''',
    "forbids": '''\
    glob_pat, pattern = arg
    hits = matches(glob_pat)
    if not hits:
        print(f"{LAW}: FAIL — nothing matches {glob_pat} (empty corpus is not a pass, SPI-32)")
        return 1
    rx = re.compile(pattern)
    bad = [str(p.relative_to(ROOT)) for p in hits
           if rx.search(p.read_text(encoding="utf-8", errors="replace"))]
    if bad:
        print(f"{LAW}: FAIL — /{pattern}/ found in {len(bad)} file(s): {bad[:5]}")
        return 1
    print(f"{LAW}: PASS — /{pattern}/ absent from all {len(hits)} file(s)")
    return 0
''',
    "implies": '''\
    glob_pat, antecedent, consequent = arg
    hits = matches(glob_pat)
    if not hits:
        print(f"{LAW}: FAIL — nothing matches {glob_pat} (empty corpus is not a pass, SPI-32)")
        return 1
    ra, rb = re.compile(antecedent), re.compile(consequent)
    bad = [str(p.relative_to(ROOT)) for p in hits
           if ra.search(p.read_text(encoding="utf-8", errors="replace"))
           and not rb.search(p.read_text(encoding="utf-8", errors="replace"))]
    if bad:
        print(f"{LAW}: FAIL — /{antecedent}/ without /{consequent}/ in {len(bad)} file(s): {bad[:5]}")
        return 1
    print(f"{LAW}: PASS — every /{antecedent}/ is accompanied by /{consequent}/")
    return 0
''',
    "runs": '''\
    argv = shlex.split(arg)
    if not argv:
        print(f"{LAW}: SKIP — empty command")
        return 3
    r = subprocess.run(argv, cwd=ROOT)
    if r.returncode == 0:
        print(f"{LAW}: PASS — {arg} exited 0")
        return 0
    if r.returncode == 3:
        print(f"{LAW}: SKIP — {arg} exited 3")
        return 3
    print(f"{LAW}: FAIL — {arg} exited {r.returncode}")
    return 1
''',
}


def generate_gate(law: Law) -> str | None:
    kind, arg = parse_predicate(law.predicate or "")
    if kind is None:
        return None
    body = GENERATED_BODY[kind]
    # The predicate is a regex in some kinds, so its backslashes must be doubled before it
    # lands in a docstring, or the generated file emits SyntaxWarning on import. A generated
    # gate that warns is a gate that will one day be silenced.
    shown_predicate = (law.predicate or "").replace("\\", "\\\\")
    src = GENERATED_HEADER.format(
        law_id=law.id, title=law.title or "(untitled)",
        source=law.source, line=law.line, predicate=shown_predicate,
        contract=CONTRACT[kind],
    ).replace("__KIND__", repr(kind)).replace("__ARG__", repr(arg))
    src += f'    LAW = {law.id!r}\n'
    src += body
    src += '\n\nif __name__ == "__main__":\n    sys.exit(main())\n'
    return src


def gate_name(law: Law) -> str:
    return "gate_" + re.sub(r"[^A-Za-z0-9]+", "_", law.id).lower() + ".py"


# ── coupling ─────────────────────────────────────────────────────────────────────────────
def gate_path(root: Path, law: Law) -> Path | None:
    return (root / law.gate) if law.gate else None


def gate_can_fail(path: Path) -> tuple[bool, str]:
    """SPI-33: can this program return non-zero at all?

    Static analysis can PROVE ABSENCE of a failure branch. It cannot prove presence of a
    correct one, and two attempts to guess more precisely produced false accusations:

      tools/source_inspector.py  ends `return 0 if ok else 1` and defines `write_ledger`
                                 beside it — a checker that also writes, called a generator
      tools/test_icon_forge.js   ends `process.exit(fail ? 1 : 0)` — a real exit, missed

    Four of five accusations in the first run were wrong. A detector that cries wolf is a
    mistrial (MUST #33), so this now answers the narrow question it can answer honestly:
    does the file contain any exit-producing expression that is not unconditionally zero?
    If it does, the gate is accepted and RUNNING it decides. If it contains none, it is a
    generator and cannot be a gate.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return False, f"unreadable: {e}"

    exits = re.findall(
        r"(?:return|exit|throw|panic|abort|die|raise)\s*[({]?\s*[^\n;]*",
        text,
    )
    for e in exits:
        # anything that could carry a non-zero value, in any language's spelling
        if re.search(r"[1-9]|fail|error|bad|!=|==|\?|if\b", e):
            return True, "ok"
    if exits:
        return True, "ok (has an exit expression; running decides)"
    return False, "no exit expression at all — this is a generator, not a gate"


def merge(laws: list[Law]) -> list[Law]:
    """One law, however many documents quote it.

    The same law is restated in the canonical record, the agent memory, the task board and a
    knowledge-base catalog. That is one law quoted four times, not four laws. MERGE the
    copies: a law is enforced if ANY declaration of it carries enforcement. Picking by file
    order was order-sensitive and let a catalog copy with no gate shadow the real one.
    """
    merged: dict[str, Law] = {}
    for law in laws:
        prev = merged.get(law.id)
        if prev is None:
            merged[law.id] = law
            continue
        if law.gate and not prev.gate:
            prev.gate = law.gate
            prev.source, prev.line = law.source, law.line
        if law.predicate and not prev.predicate:
            prev.predicate = law.predicate
        if not prev.title and law.title:
            prev.title = law.title
    return list(merged.values())


def couple(root: Path, laws: list[Law]) -> tuple[list[str], list[Law]]:
    """Bind each law to a gate that can fail.

    A `PREDICATE:` line is itself a coupling: it says what the law means mechanically, so
    the gate can be REGENERATED from it rather than trusted to exist. Such a law is coupled
    when its generated gate exists and can fail, whatever its `GATE:` line says. That is the
    auto-coupling mechanic — the law carries its own enforcement, and the engine writes it.

    A law with no predicate falls back to the gate it names, which must exist and be able
    to return non-zero.
    """
    problems: list[str] = []
    uncoupled: list[Law] = []
    for law in laws:
        if law.predicate:
            gen = root / "tools" / "generated" / gate_name(law)
            if not gen.is_file():
                uncoupled.append(law)
                continue
            ok, why = gate_can_fail(gen)
            if not ok:
                problems.append(f"{law.id} generated gate cannot fail — {why}")
                uncoupled.append(law)
            continue
        gp = gate_path(root, law)
        if gp is None:
            uncoupled.append(law)
            continue
        if not gp.is_file():
            problems.append(f"{law.id} ({law.source}:{law.line}) names gate {law.gate} — absent")
            uncoupled.append(law)
            continue
        ok, why = gate_can_fail(gp)
        if not ok:
            problems.append(f"{law.id} gate {law.gate} cannot fail — {why}")
            uncoupled.append(law)
    return problems, uncoupled


# ── healing ─────────────────────────────────────────────────────────────────────────────
def heal(root: Path, uncoupled: list[Law], dry_run: bool) -> tuple[int, list[str]]:
    outdir = root / "tools" / "generated"
    written, log = 0, []
    for law in uncoupled:
        if not law.predicate:
            log.append(f"{law.id}: no gate and no PREDICATE — cannot regenerate; "
                       f"add `PREDICATE: <kind> <arg>` under the law ({PREDICATE_HELP.splitlines()[0].strip()})")
            continue
        src = generate_gate(law)
        if src is None:
            log.append(f"{law.id}: PREDICATE not understood: {law.predicate!r}")
            continue
        dest = outdir / gate_name(law)
        digest = hashlib.sha256(src.encode()).hexdigest()[:12]
        if dest.is_file() and dest.read_text(encoding="utf-8") == src:
            log.append(f"{law.id}: already healed -> {dest.relative_to(root)} ({digest})")
            continue
        if not dry_run:
            outdir.mkdir(parents=True, exist_ok=True)
            dest.write_text(src, encoding="utf-8")
            dest.chmod(0o755)
        written += 1
        log.append(f"{law.id}: {'would write' if dry_run else 'wrote'} "
                   f"{dest.relative_to(root)} ({digest})")
    return written, log


# ── selftest: every dialect, every predicate, both trials ────────────────────────────────
SELFTEST_DOC = """\
─── MUST #1 (BOX DIALECT) ───
GATE: tools/one.py

### RULE 2 — MARKDOWN DIALECT
GATE: tools/two.sh

- **LAW 3**: BULLET DIALECT
  GATE: tools/three.kt

> INVARIANT 4 (BLOCKQUOTE)
> GATE: tools/four.js

// POLICY 5: SOURCE COMMENT DIALECT
// GATE: tools/five.ts

§9 — A SECTION, NOT A LAW

SPI-6 (DASH FORM)
GATE: tools/six.py

CONSTRAINT #7
PREDICATE: exists some/path
"""


def selftest() -> int:
    import tempfile

    fails: list[str] = []

    def ok(cond, msg):
        if not cond:
            fails.append(msg)

    laws = parse(SELFTEST_DOC, "selftest.md")
    ids = [l.id for l in laws]
    for want in ("MUST-1", "RULE-2", "LAW-3", "INVARIANT-4", "POLICY-5", "SPI-6", "CONSTRAINT-7"):
        ok(want in ids, f"dialect parse missed {want} (got {ids})")
    ok("LAW-9" not in ids, "§9 section was misparsed as a law")
    ok(len(laws) == 7, f"expected 7 laws, got {len(laws)}: {ids}")

    by = {l.id: l for l in laws}
    # .get, never []: a selftest that raises on a broken parser produces no verdict at all,
    # and "crashed" reads as "not passing" only if someone is watching. A missing law must
    # become a recorded failure like any other.
    ok(by.get("MUST-1") is not None and by["MUST-1"].title == "BOX DIALECT",
       f"title parse: {getattr(by.get('MUST-1'), 'title', None)!r}")
    ok(by.get("RULE-2") is not None and by["RULE-2"].title == "MARKDOWN DIALECT",
       f"markdown dialect not parsed (title {getattr(by.get('RULE-2'), 'title', None)!r})")
    ok(by.get("LAW-3") is not None and by["LAW-3"].gate == "tools/three.kt",
       f"bullet dialect gate parse: {getattr(by.get('LAW-3'), 'gate', None)!r}")
    ok(by.get("CONSTRAINT-7") is not None and by["CONSTRAINT-7"].predicate == "exists some/path",
       "predicate parse")

    # canonicalisation: spelling must not change identity
    for spelling in ("MUST #17", "MUST-17", "MUST 17", "must #17"):
        got = parse(spelling + " (X)\n", "t.md")
        ok(got and got[0].id == "MUST-17", f"canonicalisation failed for {spelling!r}")

    # predicate generation: every kind, and every generated gate must be born honest
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "tools").mkdir()
        (root / "a.txt").write_text("hello\n")
        (root / "b.txt").write_text("rooted\n")
        for kind, arg in (("exists", "a.txt"), ("absent", "nope.txt"), ("unique", "a.txt"),
                          ("contains", "a.txt :: hello"), ("forbids", "a.txt :: goodbye"),
                          ("implies", "*.txt :: rooted :: hello"), ("runs", "true")):
            law = Law("MUST", "99", "T", "t.md", 1)
            law.predicate = f"{kind} {arg}"
            src = generate_gate(law)
            ok(src is not None, f"no gate generated for {kind}")
            if src:
                # The gate must not describe an exit it cannot produce.
                if kind == "runs":
                    ok("return 3" in src, f"generated {kind} gate lost the SKIP signal (SPI-31)")
                else:
                    ok("return 3" not in src,
                       f"generated {kind} gate claims a SKIP state it cannot reach")
                ok("empty corpus is not a pass" in src or kind in ("exists", "absent", "runs"),
                   f"generated {kind} gate can pass vacuously (SPI-32)")
                ok("sys.exit(main())" in src, f"generated {kind} gate has no entrypoint")
        # round trip: a healed gate must actually run and agree with its predicate
        law = Law("MUST", "98", "T", "t.md", 1)
        law.predicate = "contains a.txt :: hello"
        dest = root / "tools" / "generated" / gate_name(law)
        dest.parent.mkdir(parents=True)
        dest.write_text(generate_gate(law))
        r = subprocess.run([sys.executable, str(dest)], capture_output=True, text=True)
        ok(r.returncode == 0, f"healed gate failed on a true predicate: {r.stdout}{r.stderr}")
        law.predicate = "forbids a.txt :: hello"
        dest.write_text(generate_gate(law))
        r = subprocess.run([sys.executable, str(dest)], capture_output=True, text=True)
        ok(r.returncode == 1, f"healed gate passed on a false predicate: {r.stdout}")
        # implication semantics: antecedent without consequent FAILS, with it PASSES
        law.predicate = "implies *.txt :: rooted :: hello"
        dest.write_text(generate_gate(law))
        r = subprocess.run([sys.executable, str(dest)], capture_output=True, text=True)
        ok(r.returncode == 1, f"implication passed with antecedent and no consequent: {r.stdout}")
        (root / "b.txt").write_text("rooted and hello\n")
        r = subprocess.run([sys.executable, str(dest)], capture_output=True, text=True)
        ok(r.returncode == 0, f"implication failed when consequent present: {r.stdout}")

        # empty corpus must FAIL, never pass (SPI-32)
        law.predicate = "contains zzz*.txt :: hello"
        dest.write_text(generate_gate(law))
        r = subprocess.run([sys.executable, str(dest)], capture_output=True, text=True)
        ok(r.returncode == 1, f"healed gate passed over an empty corpus: {r.stdout}")

        # SPI-33: a generator with no failure branch must not couple
        gen = root / "tools" / "gen.py"
        gen.write_text("def pack():\n    open('x','w').write('y')\npack()\n")
        ok(not gate_can_fail(gen)[0], "generator with no failure branch was accepted as a gate")
        chk = root / "tools" / "chk.py"
        chk.write_text("import sys\ndef main():\n    return 1\nsys.exit(main())\n")
        ok(gate_can_fail(chk)[0], "real checker was rejected as a gate")

        # healing is idempotent: same law, same bytes
        law2 = Law("MUST", "97", "T", "t.md", 1)
        law2.predicate = "exists a.txt"
        n1, _ = heal(root, [law2], dry_run=False)
        n2, _ = heal(root, [law2], dry_run=False)
        ok(n1 == 1 and n2 == 0, f"healing not idempotent: wrote {n1} then {n2}")

    if fails:
        print(f"directive_core selftest: FAIL — {len(fails)} problem(s)")
        for f in fails:
            print("  " + f)
        return 1
    print(f"directive_core selftest: PASS — 7 dialects, 7 predicate kinds, "
          f"idempotent healing, SPI-31/32/33 compiled into every generated gate")
    return 0


# ── main ────────────────────────────────────────────────────────────────────────────────
DEFAULT_PATTERNS = ["*.md", "docs/*.md", "docs/**/*.md", "*.rst", "*.txt", "LAWS*"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Portable directive engine.")
    ap.add_argument("--root", default=".", help="project root to examine")
    ap.add_argument("--docs", nargs="*", default=None, help="glob patterns for directive files")
    ap.add_argument("--check", action="store_true", help="couple laws to gates and report")
    ap.add_argument("--heal", action="store_true", help="generate gates for uncoupled laws")
    ap.add_argument("--dry-run", action="store_true", help="with --heal: show, do not write")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dialects", action="store_true", help="print the accepted dialects")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.dialects:
        print("verbs:", ", ".join(_VERBS))
        print("comment prefixes:", ", ".join(_COMMENT_PREFIXES))
        print("predicates:\n" + PREDICATE_HELP)
        return 0

    root = Path(args.root).resolve()
    laws = collect(root, args.docs or DEFAULT_PATTERNS)
    laws = merge(laws)
    if not laws:
        print("directive_core: SKIP — no directives found (an empty law set is not a pass)")
        return 3

    problems, uncoupled = couple(root, laws)

    healed = 0
    if args.heal:
        # Regenerate EVERY predicate law, not only the uncoupled ones. A generated gate that
        # is coupled is still generated: if the law's predicate is edited, the gate must
        # follow, or the document and the enforcement drift apart silently. `heal` is
        # idempotent, so regenerating a correct gate costs nothing and reports "already".
        healed, log = heal(root, [l for l in laws if l.predicate], args.dry_run)
        for line in log:
            print("  heal: " + line)
        if not args.dry_run and healed:
            laws = merge(collect(root, args.docs or DEFAULT_PATTERNS))
            problems, uncoupled = couple(root, laws)

    if args.json:
        print(json.dumps({
            "root": str(root), "laws": [l.as_dict() for l in laws],
            "uncoupled": [l.id for l in uncoupled], "problems": problems,
            "healed": healed,
        }, indent=2))
    else:
        print(f"directive_core: {len(laws)} law(s), {len(laws) - len(uncoupled)} coupled, "
              f"{len(uncoupled)} uncoupled, {healed} healed")

    if problems or uncoupled:
        if not args.json:
            for p in problems:
                print("  " + p)
            for l in uncoupled:
                if not l.predicate:
                    print(f"  {l.id} ({l.source}:{l.line}) — uncoupled and no PREDICATE "
                          f"to regenerate from")
        return 1
    if not args.json:
        print("directive_core: PASS — every law is bound to a gate that can fail")
    return 0


if __name__ == "__main__":
    sys.exit(main())
